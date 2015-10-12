"""
Autohide Sidebar
or: sublime-autohide-sidebar

A Sublime Text plugin that autohides the sidebar and shows
it when the mouse hovers the edge of the editors window.

Copyright (C) 2015, Mazdak Farrokhzad

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from base import MoveEventMeta, find_key, map_coordinates

# Imports:
from contextlib import contextmanager
from os import popen
from ctypes import *
from ctypes.util import find_library

def lib( l ):
	path = find_library( l )
	if not path: quit( "Can't find %s!" % l )
	return CDLL( path )

# Get Xlib:
X11 = lib( "X11" )

# Typedefs:
class Display( Structure): pass

Bool = c_int
Time = c_ulong
Atom = c_ulong
DisplayPtr = POINTER( Display )
Window = c_ulong
WindowPtr = POINTER( Window )
XPointer = c_char_p

class XAnyEvent( Structure ):
	_fields_ = [
		('type', c_int),
		('serial', c_ulong),
		('send_event', Bool),
		('display', DisplayPtr ),
		('window', Window)
	]

XEventCommon = [
	('root', Window),
	('subwindow', Window),
	('time', Time),
	('x', c_int), ('y', c_int),
	('x_root', c_int), ('y_root', c_int)]

class XMotionEvent( XAnyEvent ):
	_fields_ = XEventCommon + [
		('state', c_uint),
		('is_hint', c_char),
		('same_screen', Bool)
	]

class XCrossingEvent( XAnyEvent ):
	_fields_ = XEventCommon + [
		('mode', c_int),
		('detail', c_int),
		('same_screen', Bool),
		('focus', Bool),
		('state', c_uint),
	]

class XEvent( Union ):
	_fields_ = [
		('type', c_int),
		('xany', XAnyEvent),
		('xmotion', XMotionEvent),
		('xcross', XCrossingEvent),
		('pad', c_long * 24),
	]

EventPredicate = CFUNCTYPE( Bool, DisplayPtr, POINTER( XEvent ), XPointer )
X11.XOpenDisplay.restype = DisplayPtr

# Constants: XWindow._property:
MAX_PROPERTY_VALUE_LEN = int( 4096 / 4 )
BYTE_LONG = int( 32 / sizeof( c_long ) )
XA_CARDINAL = 6
XA_WINDOW = 33
XA_STRING = 31
Success = 0

# Constants: Motion & Leave:
MotionNotify = 6
LeaveNotify	= 8
NotifyList = [MotionNotify, LeaveNotify]
PointerMotionMask = (1 << 6)
LeaveWindowMask	= (1 << 5)
EventMask = PointerMotionMask | LeaveWindowMask

# Returns atom identifier associated with specified prop string:
def intern_atom( disp, prop ):
	return X11.XInternAtom( disp, c_char_p( prop.encode() ), 0 )

@contextmanager
def x_lock( disp ):
	try:
		X11.XLockDisplay( disp )
		yield 
	finally:
		X11.XUnlockDisplay( disp )

# XWindow: a wrapper around X11 Windows:
class XWindow( object ):
	def __init__( self, disp, win ):
		self.disp = disp
		self.win = win

	def __eq__( self, rhs ):
		return isinstance( rhs, self.__class__) and self.win == rhs.win
	def __ne__( self, rhs ):
		return not self.__eq__( rhs )
	def __hash__( self ):
		return hash( self.win )

	# Returns root window:
	def root( disp ):
		with x_lock( disp ): 
			return XWindow( disp, X11.XRootWindow( disp, 0 ) )

	# Retrieves a property of X11 window of prop_name:
	def _property( self, xa_prop_type, prop_name, mbuf = None ):
		xa_prop_name = Atom()
		xa_ret_type = Atom()
		ret_format = c_int()
		ret_nitems = c_ulong()
		ret_prop = POINTER( c_ubyte )()
		xa_prop_name = intern_atom( self.disp, prop_name )

		# MAX_PROPERTY_VALUE_LEN / 4 explanation (XGetWindowProperty manpage):
		# long_length = Length in 32-bit multiples of the data to be retrieved.
		s = X11.XGetWindowProperty( self.disp, self.win, xa_prop_name, 0,
				MAX_PROPERTY_VALUE_LEN, 0, xa_prop_type,
				byref( xa_ret_type ), byref( ret_format ),
				byref( ret_nitems ), byref( c_ulong() ), byref( ret_prop ) )

		# Fail if not Success or non-matching types:
		if s != Success: return print( "Can't get property: " + prop_name )
		if xa_ret_type.value != xa_prop_type:
			print( "Invalid type of property: " + prop_name )
			X11.XFree( ret_prop )
			return

		if mbuf:
			(buf, byte_size) = mbuf( ret_format.value, ret_nitems.value )
		else:
			byte_size = ret_nitems.value * int( ret_format.value / 8 )
			buf = create_string_buffer( byte_size )

		memmove( buf, ret_prop, byte_size )
		X11.XFree( ret_prop )
		return buf

	# Get top level X11 windows:
	def client_list( self ):
		with x_lock( self.disp ):
			mbuf = lambda f, n: ((Window * n)(), int( f / BYTE_LONG ) * n)
			r = self._property( XA_WINDOW, "_NET_CLIENT_LIST", mbuf )
			if not r:
				r = self._property( XA_CARDINAL, "_WIN_CLIENT_LIST", mbuf )
				if not r:
					return print( "Cannot get client list properties.\n"\
								  "(_NET_CLIENT_LIST or _WIN_CLIENT_LIST)" )
			return [XWindow( self.disp, w ) for w in r]

	# Retrieves PID of a X11 window if possible:
	def pid( self ):
		with x_lock( self.disp ):
			mbuf = lambda f, n: (pointer( c_ulong() ), int( f / BYTE_LONG ) * n)
			r = self._property( XA_CARDINAL, "_NET_WM_PID", mbuf )
			if not r: return print( "Can't get PID of window: ", self.win )
			return r.contents.value

	# Retrieves title of X11 window if possible:
	def title( self ):
		with x_lock( self.disp ): 
			r = self._property( XA_STRING, "WM_NAME" )
			if not r:
				r = self._property( XA_CARDINAL, "_NET_WM_NAME" )
				if not r: return print( "Can't get title of window: ", win )
			return r[:].decode()

	# Allows events specified by mask to happen for window:
	def select_input( self, mask ):
		with x_lock( self.disp ):
			X11.XSelectInput( self.disp, self.win, mask )

	# Returns a tuple ((x-pos, y-pos, width, height), root_window) of window:
	def geom( self ):
		root = Window()
		rect = [c_int(), c_int(), c_uint(), c_uint()]
		refs = [byref( e ) for e in rect]

		# Get geometry and roof of window, ignore rest:
		with x_lock( self.disp ):
			X11.XGetGeometry( self.disp, self.win, byref( root ),
				refs[0], refs[1], refs[2], refs[3],
				byref( c_uint() ), byref( c_uint() ) )

		# Translate if needed (not same window as root) to root coordinates:
		if self.win != root:
			with x_lock( self.disp ):
				X11.XTranslateCoordinates( self.disp, self.win, root,
					rect[0], rect[1], refs[0], refs[1], byref( Window() ) )

		# Return values & make a new window wrapper:
		return (tuple( e.value for e in rect ), XWindow( self.disp, root ))

	# Returns the position of pointer relative to window:
	def pointer( self ):
		w1, w2 = [byref( Window() ) for _ in range( 2 )]
		xys = [c_int() for _ in range( 4 )]
		refs = [byref( e ) for e in xys]

		with x_lock( self.disp ):
			X11.XQueryPointer( self.disp, self.win, w1, w2,
				refs[0], refs[1], refs[2], refs[3], byref( c_ulong() ) )

		return tuple( e.value for e in xys )

# Checks if window is a sublime text window:
def is_sublime( win ):
	pid = win.pid()
	if not pid: return False
	r = popen( "ps -p %s -c -o command" % pid ).read().split()
	if len( r ) and "sublime_text" in r[-1]: return True
	# Fallback approach:
	title = win.title()
	return title.endswith( ' - Sublime Text' ) if title else False

def enable_events( win ):
	win.select_input( EventMask )

def event_id( event ):
	return win_map[XWindow( disp, event.window )]

"""
Public API
"""

def window_coordinates( _id ):
	# Fetch window or quit if not available:
	global win_map
	win = find_key( win_map, _id )
	if not win: return

	# Get geometrics & pointer:
	(wx, wy, ww, wh), root = win.geom()
	(rx, ry, _, _), _ = root.geom()
	cx, cy, _, _ = root.pointer()

	# Quit if not within bounds:
	if not ((wx <= cx <= (wx + ww)) and (wy <= cy <= (wy + wh))): return

	# Map (cx, cy) to space( win ):
	return map_coordinates( rx, ry, wx, wy, cx, cy )

def window_width( _id ):
	global win_map
	win = find_key( win_map, _id )
	return win.geom()[0][2] if win else None

def register_new_window( _id ):
	global win_map
	if find_key( win_map, _id ): return

	# Get top level windows:
	top_windows = root_window.client_list()
	if not top_windows: return print( "Can't find top level windows" )

	# Bind first non-registered window => _id.
	for w in filter( is_sublime, top_windows ):
		if w not in win_map:
			print( "found", "window", w.win,
					"pid", w.pid(), "title", w.title() )
			# Register callbacks & bind:
			enable_events( w )
			win_map[w] = _id
			return

class MoveEvent( MoveEventMeta ):
	def __init__( self ):
		# For some reason X11 can't work with daemon threads:
		super().__init__( False )

	def run( self ):
		# Using predicate to avoid copying events of no interest:
		def event_predicate( d, event, a ):
			e = event.contents
			return e.type in NotifyList and not e.xany.send_event
		pred = EventPredicate( event_predicate )

		# Event pump:
		while self.alive:
			# Block, waiting for an event:
			e = XEvent()
			ref = byref( e )
			X11.XIfEvent( disp, ref, pred, None )

			# Route event &
			# Put event back, we are just passively snooping:
			mask, fn = ((PointerMotionMask, self._move)
						if e.type == MotionNotify
						else (LeaveWindowMask, self._leave))
			fn( e )
			X11.XSendEvent( disp, e.xany.window, 0, mask, ref )

	def _move( self, event ):
		e = event.xmotion
		self.move( event_id( e ), e.x, e.y )

	def _leave( self, event ):
		self.leave( event_id( event.xcross ) )

	def _stop( self ):
		X11.XCloseDisplay( disp )

class Tracker( MoveEvent ):
	def move( self, _id, x, y ): print( "move", _id, x, y )
	def leave( self, _id ): print( "leave", _id )

# Let's get things started in here:
# Initialize X11: Threading, get Display & Root Window:
if not X11.XInitThreads(): quit( "X11 doesn't support multithreading." )
disp = X11.XOpenDisplay( None )
if not disp: quit( "Can't open default display!" )
root_window = XWindow.root( disp )
win_map = {}


register_new_window( 1 )
print( window_width( 1 ) )
print( window_coordinates( 1 ) )

#quit()

m = Tracker()
m.start()