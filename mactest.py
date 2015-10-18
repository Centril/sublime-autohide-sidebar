from os import popen
from ctypes import *
from ctypes.util import find_library

def lib( l ):
	path = find_library( l )
	if not path: quit( "Can't find %s!" % l )
	return CDLL( path )

Q = lib( "quartz" )

"""
Typedefs & Functions:
"""
c_void_pp = POINTER( c_void_p )

CGWindowID = c_uint32
CGWindowListOption = c_uint32

CFIndex = c_long
CFStringRef = c_void_p
CFStringEncoding = c_uint32
CFArrayRef = c_void_p
CFDictionaryRef = c_void_p

# Fixes the return and argument types of FFI function:
def fix_cfn( fn, res, args ):
	fn.restype = res
	fn.argtypes = args

fix_cfn( Q.CFStringGetLength, CFIndex, [CFStringRef] )
fix_cfn( Q.CFStringGetCString, c_bool,
	[CFStringRef, c_char_p, CFIndex, CFStringEncoding] )
fix_cfn( Q.CFArrayGetCount, CFIndex, [CFArrayRef] )
fix_cfn( Q.CFArrayGetValueAtIndex, c_void_p, [CFArrayRef, CFIndex] )
fix_cfn( Q.CFDictionaryGetValue, c_void_p, [CFDictionaryRef, c_void_p] )
fix_cfn( Q.CFDictionaryContainsKey, c_bool, [CFDictionaryRef, c_void_p] ) 
fix_cfn( Q.CFRelease, None, [c_void_p] )
fix_cfn( Q.CGWindowListCopyWindowInfo, CFArrayRef, [CGWindowListOption] )

# Converts a _FunPtr to c_void_p
def fn_to_voidp( fn ): return c_void_pp.from_buffer( fn ).contents

# Handles a CFArray like a generator:
def cfarray( arr ):
	n = Q.CFArrayGetCount( arr )
	for i in range( n ):
		yield Q.CFArrayGetValueAtIndex( arr, i )

# Returns object of _restype using CFNumberRef _from interpreting as _type:
def cfnumber_get( _type, _restype, _from ):
	_to = _restype()
	r = Q.CFNumberGetValue( _from, _type, byref( _to ) )
	return _to

def cfstring_get( ref ):
	str_length = Q.CFStringGetLength( ref ) + 1
	str_buf = create_string_buffer( str_length )
	result = Q.CFStringGetCString( ref, str_buf, str_length, 0 )
	return str_buf.value.decode( errors = 'ignore' )

#class __CFString( Structure ): pass
#class __CFArray( Structure ): pass
#CFStringRef = POINTER( __CFString )
#CFArrayRef = POINTER( __CFArray )

"""
Constants:
"""
kCGWindowListOptionAll = CGWindowListOption( 0 )
kCGWindowListExcludeDesktopElements = CGWindowListOption( 1 << 4 )
kCGNullWindowID = CGWindowID( 0 )
kCGWindowNumber = fn_to_voidp( Q.kCGWindowNumber )
kCGWindowName = fn_to_voidp( Q.kCGWindowName )
kCGWindowOwnerName = fn_to_voidp( Q.kCGWindowOwnerName )
kCGWindowOwnerPID = fn_to_voidp( Q.kCGWindowOwnerPID )
kCGWindowLayer = fn_to_voidp( Q.kCGWindowLayer )

kCFNumberSInt32Type = 3
kCFNumberIntType = 9
kCGWindowIDCFNumberType = kCFNumberSInt32Type

"""
Stuff:
"""

# View of CFDictionaryRef as a python dict (partial implementation):
class CFDict( object ):
	def __init__( self, data ):
		self.data = data

	def __getitem__( self, key ):
		return Q.CFDictionaryGetValue( self.data, key )

	def __contains__( self, key ):
		return Q.CFDictionaryContainsKey( self.data, key )

class WinDict( object ):
	def __init__( self, _dict ):
		self.dict = CFDict( _dict )

	def _get( self, key, type_id, to_type ):
		return cfnumber_get( type_id, to_type, self.dict[key] )

	def id( self ):
		return self._get( kCGWindowNumber, kCGWindowIDCFNumberType, CGWindowID )

	def pid( self ):
		return self._get( kCGWindowOwnerPID, kCFNumberIntType, c_int ).value

	def title( self ):
		return (cfstring_get( self.dict[kCGWindowName] )
				if kCGWindowName in self.dict else None)

# Checks if window is a sublime text window:
def is_sublime( win ):
	pid = win.pid()
	if not pid: return False
	r = popen( "ps -p %s -c -o command" % pid ).read().strip().split( '\n' )
	if not (r and "Sublime Text" in r[-1]): return False
	if win.title(): return True
	# Fallback approach:
#	title = win.title()
#	return title.endswith( ' - Sublime Text' ) if title else False

def top_level():
	windows = Q.CGWindowListCopyWindowInfo(
		0, kCGNullWindowID )

	try:
		for _win in cfarray( windows ):
			w = WinDict( _win )
			if not is_sublime( w ): continue
			print( _win, w.id(), w.pid(), w.title() )
	finally:
		Q.CFRelease( windows )

top_level()