# Imports:
from ctypes import *
from ctypes.util import find_library

def q( msg ): print( msg ) and quit()

# Get Xlib:
xlib_path = find_library( 'X11' )
if not xlib_path: q( "Can't find X11!" )
x = CDLL( xlib_path )

#Bool = c_bool
#Time = c_ulong
Atom = c_ulong
#Display = c_void_p
Window = c_ulong
WindowPtr = POINTER( Window )
#XPointer = c_char_p

disp = x.XOpenDisplay( None )
if not disp: q( "Can't open default display!" )

def intern_atom( disp, prop ):
	return x.XInternAtom( disp, c_char_p( prop.encode() ), 0 )

MAX_PROPERTY_VALUE_LEN = int( 4096 / 4 )
XA_WINDOW = 33
XA_CARDINAL = 6
XA_STRING = 31
Success = 0
UTF8_STRING = intern_atom( disp, "UTF8_STRING" )
BYTE_LONG = int( 32 / sizeof( c_long ) )

class XWindow( object ):
	def __init__( self, disp, win ):
		self.disp = disp
		self.win = win

	# Retrieves a property of X11 window of prop_name:
	def _property( self, xa_prop_type, prop_name, mbuf = None ):
		xa_prop_name = Atom()
		xa_ret_type = Atom()
		ret_format = c_int()
		ret_nitems = c_ulong()
		ret_prop = POINTER( c_ubyte )()
		xa_prop_name = intern_atom( self.disp, prop_name )

		# MAX_PROPERTY_VALUE_LEN / 4 explanation (XGetWindowProperty manpage):
		# long_length = The length in 32-bit multiples of the data to be retrieved.
		s = x.XGetWindowProperty( self.disp, self.win, xa_prop_name, 0,
				MAX_PROPERTY_VALUE_LEN, 0, xa_prop_type,
				byref( xa_ret_type ), byref( ret_format ),
				byref( ret_nitems ), byref( c_ulong() ), byref( ret_prop ) )

		# Fail if not Success or non-matching types:
		if s != Success: return print( "Can't get property: " + prop_name )
		if xa_ret_type.value != xa_prop_type:
			print( "Invalid type of property: " + prop_name )
			x.XFree( ret_prop )
			return

		if mbuf:
			(buf, byte_size) = mbuf( ret_format.value, ret_nitems.value )
		else:
			byte_size = ret_nitems.value * int( ret_format.value / 8 )
			buf = create_string_buffer( byte_size + 1 )
			buf[byte_size] = b'\0'

		memmove( buf, ret_prop, byte_size )
		x.XFree( ret_prop )
		return buf

	# Get top level X11 windows:
	def client_list( self ):
		mbuf = lambda f, n: ((Window * n)(), int( f / BYTE_LONG ) * n)
		r = self._property( XA_WINDOW, "_NET_CLIENT_LIST", mbuf )
		if not r:
			r = self._property( XA_CARDINAL, "_WIN_CLIENT_LIST", mbuf )
			if not r: return print( "Cannot get client list properties.\n"\
									"(_NET_CLIENT_LIST or _WIN_CLIENT_LIST)" )
		return [XWindow( self.disp, w ) for w in r]

	# Retrieves PID of a X11 window if possible:
	def pid( self ):
		mbuf = lambda f, n: (pointer( c_ulong() ), int( f / BYTE_LONG ) * n)
		r = self._property( XA_CARDINAL, "_NET_WM_PID", mbuf )
		if not r: return print( "Can't get PID of window: ", win )
		return r.contents.value

	# Retrieves title of X11 window if possible:
	def title( self ):
		r = self._property( XA_STRING, "WM_NAME" )
		if not r:
			r = self._property( XA_CARDINAL, "_NET_WM_NAME" )
			if not r: return print( "Can't get title of window: ", win )
		return r[:].decode()

# Gets root window:
def get_root_window( disp ):
	return XWindow( disp, x.XRootWindow( disp, 0 ) )

root_window = get_root_window( disp )
cls = root_window.client_list()
if not cls: q( "Can't find top level windows")

for w in cls:
	title = w.title()
	pid = w.pid()
	print( "window: ", w.win, "pid: ", pid, "title: ", title )