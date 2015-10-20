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

from driver.base import DriverMeta, MoveEventMeta, find_key, map_coordinates

from itertools import starmap
from contextlib import contextmanager
from os import popen
from ctypes import *
from ctypes.util import find_library

def lib( l ):
	path = find_library( l )
	if not path: quit( "Can't find %s!" % l )
	return CDLL( path )

Q = lib( "quartz" )

"""
Typedefs, Functions, Structures:
"""
# Primitives:
is64bit = sizeof( c_void_p ) != 4
class CFTypeRef( c_void_p ): pass
CFTypeRefPtr = POINTER( CFTypeRef )
CGFloat = c_double if is64bit else c_float
CFIndex = c_long
CFStringEncoding = c_uint32
CFBooleanRef = CFStringRef =\
CFArrayRef = CFDictionaryRef = CFAllocatorRef = CFTypeRef
# Window info:
CGWindowID = CGWindowListOption = c_uint32
# Event tap:
CFRunLoopRef = CFRunLoopSourceRef =\
CGEventTapProxy = CFMachPortRef = CGEventSourceRef = CGEventRef = CFTypeRef
CGEventTapLocation = CGEventTapPlacement =\
CGEventTapOptions = CGEventType = c_uint32
CGEventMask = c_uint64
CGEventTapCallBack = CFUNCTYPE( CGEventRef,
	CGEventTapProxy, CGEventType, CGEventRef, CFTypeRef )

class CGPoint( Structure ):
	_fields_ = [('_x', CGFloat), ('_y', CGFloat)]
	def x( self ): return int( self._x )
	def y( self ): return int( self._y )
	def tuple( self ): return (self.x(), self.y())

class CGRect( Structure ):
	_fields_ = [('origin', CGPoint), ('size', CGPoint)]
	def tuple( self ): return self.origin.tuple() + self.size.tuple()

# Fixes the return and argument types of FFI function:
def fix_cfn( fn, res, args ):
	fn.restype = res
	fn.argtypes = args

# This fixes ALL FFI functions used in Quartz (ApplicationServices.h):
list( starmap( fix_cfn, [
	# Primitives:
	(Q.CFRelease, None, [CFTypeRef]),
	(Q.CFStringGetLength, CFIndex, [CFStringRef]),
	(Q.CFStringGetCString, c_bool,
		[CFStringRef, c_char_p, CFIndex, CFStringEncoding]),
	(Q.CFArrayCreate, CFArrayRef,
		[CFAllocatorRef, CFTypeRefPtr, CFIndex, CFTypeRef]),
	(Q.CFArrayGetCount, CFIndex, [CFArrayRef]),
	(Q.CFArrayGetValueAtIndex, CFTypeRef, [CFArrayRef, CFIndex]),
	(Q.CFDictionaryGetValue, CFTypeRef, [CFDictionaryRef, CFTypeRef]),
	(Q.CFDictionaryContainsKey, c_bool, [CFDictionaryRef, CFTypeRef]),
	(Q.CGRectMakeWithDictionaryRepresentation, c_bool,
		[CFDictionaryRef, POINTER( CGRect )]),
	# Window information:
	(Q.CGWindowListCreate, CFArrayRef, [CGWindowListOption, CGWindowID]),
	(Q.CGWindowListCopyWindowInfo, CFArrayRef, [CGWindowListOption, CGWindowID]),
	(Q.CGWindowListCreateDescriptionFromArray, CFArrayRef, [CFArrayRef]),
	# Pointer, Events & taps:
	(Q.CGEventCreate, CGEventRef, [CGEventSourceRef]),
	(Q.CGEventGetLocation, CGPoint, [CGEventRef]),
	(Q.CGEventTapCreate, CFMachPortRef, [CGEventTapLocation,
		CGEventTapPlacement, CGEventTapOptions, CGEventMask,
		CGEventTapCallBack, CFTypeRef]),
	(Q.CGEventTapEnable, None, [CFMachPortRef, c_bool]),
	(Q.CFMachPortCreateRunLoopSource, CFRunLoopSourceRef,
		[CFAllocatorRef, CFMachPortRef, CFIndex]),
	(Q.CFMachPortIsValid, c_bool, [CFMachPortRef]),
	(Q.CFMachPortInvalidate, None, [CFMachPortRef]),
	(Q.CFRunLoopGetCurrent, CFRunLoopRef, []),
	(Q.CFRunLoopAddSource, None,
		[CFRunLoopRef, CFRunLoopSourceRef, CFStringRef]),
	(Q.CFRunLoopRun, None, []),
	(Q.CFRunLoopStop, None, [CFRunLoopRef]),
	(Q.CFRunLoopSourceInvalidate, None, [CFRunLoopSourceRef])
] ) )

"""
ctypes helpers:
"""
# Yields from fn(x) and releases x after:
def do_release( x, fn ):
	try: yield from fn( x )
	finally: Q.CFRelease( x )

# Manages a CFArray like a generator and cleans up after usage:
def cfarray( arr, map_fn = lambda x, i: x ):
	yield from do_release( arr, lambda arr:
		(map_fn( Q.CFArrayGetValueAtIndex( arr, i ), i )
		 for i in range( Q.CFArrayGetCount( arr ) )) )

# Returns object of _restype using CFNumberRef _from interpreting as _type:
def cfnumber_get( _type, _restype, _from ):
	_to = _restype()
	return Q.CFNumberGetValue( _from, _type, byref( _to ) ) and _to

# Returns contents of cfstring as a byte slice:
def cfstring_get( ref ):
	_len = Q.CFStringGetLength( ref ) + 1
	_buf = create_string_buffer( _len )
	return (Q.CFStringGetCString( ref, _buf, _len, 0 ) and
		_buf.value.decode( errors = 'ignore' ))

# View of CFDictionaryRef as a python dict (partial implementation):
class CFDict( object ):
	def __init__( self, data ): self.d = data
	def __getitem__( self, k ): return Q.CFDictionaryGetValue( self.d, k )
	def __contains__( self, k ): return Q.CFDictionaryContainsKey( self.d, k )

"""
Constants:
"""
# Window info:
kCGWindowListOptionOnScreenOnly = (1 << 0)
kCGWindowListExcludeDesktopElements = CGWindowListOption( 1 << 4 )
kCGNullWindowID = CGWindowID( 0 )
kCFNumberSInt32Type = 3
kCFNumberIntType = 9
kCGWindowIDCFNumberType = kCFNumberSInt32Type
# Event taps:
kCGSessionEventTap = CGEventTapLocation( 1 )
kCGHeadInsertEventTap = CGEventTapPlacement( 0 )
kCGEventTapOptionListenOnly = CGEventTapOptions( 1 )
# Using kCGEventMouseMoved
EventTapMask = CGEventMask( 1 << 5 )
# Convert these constants from _FunPtr to c_void_p
[WNumber, WName, WOwnerPID, WLayer, WBounds, RunLoopDefaultMode] = map(
	lambda fn: CFTypeRefPtr.from_buffer( fn ).contents,
	[Q.kCGWindowNumber, Q.kCGWindowName, Q.kCGWindowOwnerPID,
	 Q.kCGWindowLayer, Q.kCGWindowBounds, Q.kCFRunLoopDefaultMode] )

"""
Helpers:
"""
# Wrapper around CFDict from Q.CGWindowListCopyWindowInfo:
class WinDict( object ):
	def __init__( self, _dict, _id = None ):
		self.dict = CFDict( _dict )
		self._id = _id

	@contextmanager
	def from_ids( w_ids ):
		arr = cast( (CGWindowID * len( w_ids ))( *w_ids ), CFTypeRefPtr )
		yield from do_release( Q.CFArrayCreate( None, arr, len( w_ids ), None ),
			lambda a: cfarray( Q.CGWindowListCreateDescriptionFromArray( a ),
								 lambda w, i: WinDict( w, w_ids[i] ) ) )

	def noid( _dict, i ): return WinDict( _dict )

	def _get( self, key, type_id, to_type ):
		return cfnumber_get( type_id, to_type, self.dict[key] ).value

	def id( self ):
		if not self._id:
			self._id = self._get( WNumber, kCGWindowIDCFNumberType, CGWindowID )
		return self._id

	def pid( self ): return self._get( WOwnerPID, kCFNumberIntType, c_int )

	def level( self ): return self._get( WLayer, kCFNumberIntType, c_int )

	def title( self ):
		return WName in self.dict and cfstring_get( self.dict[WName] )

	def bounds( self ):
		rect = CGRect()
		return Q.CGRectMakeWithDictionaryRepresentation( self.dict[WBounds],
			byref( rect ) ) and rect.tuple()

	def is_onscreen( self ):
		return self.id() in list( cfarray( Q.CGWindowListCreate(
			kCGWindowListOptionOnScreenOnly, kCGNullWindowID ),
			lambda x, i: x.value ) )

# Checks if window is a sublime text window:
def is_sublime( win ):
	pid = win.pid()
	if not pid: return False
	r = popen( "ps -p %s -c -o command" % pid ).read().strip().split( '\n' )
	return r and "Sublime Text" in r[-1] and win.level() == 0 and win.title()

def sublime_windows():
	return filter( is_sublime, cfarray( Q.CGWindowListCopyWindowInfo(
		kCGWindowListExcludeDesktopElements, kCGNullWindowID ), WinDict.noid ) )

# Returns the cursor position as (x, y):
def get_cursor_location():
	return tuple( do_release( Q.CGEventCreate( None ),
				lambda e: Q.CGEventGetLocation( e ).tuple() ) )

# Checks if point (x, y) is within bounds (l, t, w, h):
def point_within_bounds( p, b ): 
	return (b[0] <= p[0] <= (b[0] + b[2])) and (b[1] <= p[1] <= (b[1] + b[3]))

# Maps c from space(r) -> space(w), all input are given in (x, y):
def _map_coordinates( r, w, c ):
	return map_coordinates( r[0], r[1], w[0], w[1], c[0], c[1] )

"""
Move event logic:
"""

class MoveEvent( MoveEventMeta ):
	def run( self ):
		# Create tap or quit if failure:
		cb = CGEventTapCallBack( self.handler )
		port = Q.CGEventTapCreate( kCGSessionEventTap, kCGHeadInsertEventTap,
			kCGEventTapOptionListenOnly, EventTapMask, cb, None )
		if not port: quit( "FATAL ERROR: Could not create Quartz Events Tap!" )

		# Create source, attach source to run loop, enable tap:
		source = Q.CFMachPortCreateRunLoopSource( None, port, 0 )
		self.loop = Q.CFRunLoopGetCurrent()
		Q.CFRunLoopAddSource( self.loop, source, RunLoopDefaultMode )
		Q.CGEventTapEnable( port, True )

		# Run event pump while we can, then cleanup:
		try:
			while self.alive: Q.CFRunLoopRun()
		finally:
			if Q.CFMachPortIsValid( port ):
				Q.CFMachPortInvalidate( port )
				Q.CFRunLoopSourceInvalidate( source )
				Q.CFRelease( port )
				Q.CFRelease( source )

	def handler( self, proxy, _type, event, d ):
		x, y = Q.CGEventGetLocation( event ).tuple()
		print( "move", x, y )

	def _stopx( self ):
		# Stop the run loop, this will unblock Q.CFRunLoopRun():
		# Cleanup is done in .run().
		Q.CFRunLoopStop( self.loop )

"""
Public API:
"""
class Driver( DriverMeta ):
	def __init__( self ):
		# Let's get things started in here:
		# Create win_map:
		self.win_map = {}

	def window_coordinates( self, _id ):
		# Fetch window or quit if not available:
		w_id = find_key( self.win_map, _id )
		if not w_id: return

		# Get geometrics & pointer:
		with WinDict.from_ids( [w_id] ) as w:
			if not w.is_onscreen(): return
			bounds = w.bounds()
			print( bounds )

		c = get_cursor_location()

		# Map c to space(win) if within space:
		if point_within_bounds( c, bounds ):
			return _map_coordinates( (0, 0), bounds, c )

	def window_width( self, _id ):
		w_id = find_key( self.win_map, _id )
		if not w_id: return
		with WinDict.from_ids( [w_id] ) as w: return w.bounds()[2]

	def register_new_window( self, _id ):
		if find_key( self.win_map, _id ): return

		for w in sublime_windows():
			w_id = w.id()
			if w_id not in self.win_map:
				print( "window", w_id, "pid", w.pid(), "title", w.title() )
				self.win_map[w_id] = _id
				return

		return None

	def tracker( self, move, leave ):
		return MoveEvent( self, move, leave )

D = Driver()
for _id in range( 1, 3 ): D.register_new_window( _id )
print( D.win_map )

for _id in range( 1, 3 ):
	print( D.window_width( _id ) )
	print( D.window_coordinates( _id ) )

T = D.tracker(	lambda _id, x, y: print( "move", _id, x, y ),
				lambda _id: print( "leave", _id ) )
T.start()
def stop():
	T.stopx()