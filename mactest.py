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
is64bit = sizeof( c_void_p ) != 4
class CFTypeRef( c_void_p ): pass
CFTypeRefPtr = POINTER( CFTypeRef )
CGFloat = c_double if is64bit else c_float
CFIndex = c_long
CFStringRef = CFTypeRef
CFStringEncoding = c_uint32
CFArrayRef = CFTypeRef
CFDictionaryRef = CFTypeRef
CFAllocatorRef = CFTypeRef
CGWindowID = c_uint32
CGWindowListOption = c_uint32

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

list( starmap( fix_cfn, [
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
	(Q.CFRelease, None, [CFTypeRef]),
	(Q.CGWindowListCopyWindowInfo, CFArrayRef, [CGWindowListOption]),
	(Q.CGWindowListCreateDescriptionFromArray, CFArrayRef, [CFArrayRef])
] ) )

"""
ctypes helpers:
"""
# Converts a _FunPtr to c_void_p
def fn_to_voidp( fn ): return CFTypeRefPtr.from_buffer( fn ).contents

# Handles a CFArray like a generator,
# all operations with it are only valid until Q.CFRelease
def cfarray( arr ):
	n = Q.CFArrayGetCount( arr )
	for i in range( n ):
		yield Q.CFArrayGetValueAtIndex( arr, i )

# Returns object of _restype using CFNumberRef _from interpreting as _type:
def cfnumber_get( _type, _restype, _from ):
	_to = _restype()
	r = Q.CFNumberGetValue( _from, _type, byref( _to ) )
	return _to

# Returns contents of cfstring as a byte slice:
def cfstring_get( ref ):
	str_length = Q.CFStringGetLength( ref ) + 1
	str_buf = create_string_buffer( str_length )
	result = Q.CFStringGetCString( ref, str_buf, str_length, 0 )
	return str_buf.value.decode( errors = 'ignore' )

# View of CFDictionaryRef as a python dict (partial implementation):
class CFDict( object ):
	def __init__( self, data ):
		self.data = data

	def __getitem__( self, key ):
		return Q.CFDictionaryGetValue( self.data, key )

	def __contains__( self, key ):
		return Q.CFDictionaryContainsKey( self.data, key )

"""
Constants:
"""
kCGWindowListExcludeDesktopElements = CGWindowListOption( 1 << 4 )
kCGNullWindowID = CGWindowID( 0 )
kCGWindowNumber = fn_to_voidp( Q.kCGWindowNumber )
kCGWindowName = fn_to_voidp( Q.kCGWindowName )
kCGWindowOwnerPID = fn_to_voidp( Q.kCGWindowOwnerPID )
kCGWindowLayer = fn_to_voidp( Q.kCGWindowLayer )
kCGWindowBounds = fn_to_voidp( Q.kCGWindowBounds )

kCFNumberSInt32Type = 3
kCFNumberIntType = 9
kCGWindowIDCFNumberType = kCFNumberSInt32Type

"""
sublime_windows:
"""
# Wrapper around CFDict from Q.CGWindowListCopyWindowInfo:
class WinDict( object ):
	def __init__( self, _dict ):
		self.dict = CFDict( _dict )

	def _get( self, key, type_id, to_type ):
		return cfnumber_get( type_id, to_type, self.dict[key] ).value

	def id( self ):
		return self._get( kCGWindowNumber, kCGWindowIDCFNumberType, CGWindowID )

	def pid( self ):
		return self._get( kCGWindowOwnerPID, kCFNumberIntType, c_int )

	def level( self ):
		return self._get( kCGWindowLayer, kCFNumberIntType, c_int )

	def title( self ):
		return (cfstring_get( self.dict[kCGWindowName] )
				if kCGWindowName in self.dict else None)

	def bounds( self ):
		rect = CGRect()
		return (rect.tuple() if Q.CGRectMakeWithDictionaryRepresentation(
			self.dict[kCGWindowBounds], byref( rect ) ) else None)

# Checks if window is a sublime text window:
def is_sublime( win ):
	pid = win.pid()
	if not pid: return False
	r = popen( "ps -p %s -c -o command" % pid ).read().strip().split( '\n' )
	return r and "Sublime Text" in r[-1] and win.level() == 0 and win.title()

def sublime_windows():
	windows = Q.CGWindowListCopyWindowInfo(
		kCGWindowListExcludeDesktopElements, kCGNullWindowID )

	if not windows: quit( "Can't access CGWindows! ")

	try:
		for _win in cfarray( windows ):
			w = WinDict( _win )
			if is_sublime( w ): yield w
	finally:
		Q.CFRelease( windows )

@contextmanager
def single_window_dict( w_id ):
	w_arr = Q.CFArrayCreate( None,
		CFTypeRefPtr.from_buffer( pointer( CGWindowID( w_id ) ) ), 1, None )
	try:
		w_desc = Q.CGWindowListCreateDescriptionFromArray( w_arr )
		try: yield WinDict( next( cfarray( w_desc ) ) )
		finally: Q.CFRelease( w_desc )
	finally: Q.CFRelease( w_arr )

"""
Move event logic:
"""
class MoveEvent( MoveEventMeta ):
	def run( self ):
		while self.alive: pass

	def _stopx( self ):
		pass

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
		win = find_key( self.win_map, _id )
		if not win: return
		return None

	def window_width( self, _id ):
		win = find_key( self.win_map, _id )
		if not win: return
		with single_window_dict( win ) as ww: return ww.bounds()[2]

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

for _id in range( 1, 3 ): print( D.window_width( _id ) )