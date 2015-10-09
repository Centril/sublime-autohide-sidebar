from ctypes import *
from ctypes.util import find_library

r = byref

xlib_path = find_library( 'X11' )
if not xlib_path:
	print( "PANIC!" )
	quit()
xlib = CDLL( xlib_path )

Bool = c_bool
Time = c_ulong
Atom = c_ulong
Display = c_void_p
Window = c_ulong
WindowPtr = POINTER( Window )
XPointer = c_char_p

MotionNotify = 6
PointerMotionMask = (1 << 6)

class Event( Structure ):
	_fields_ = [('type', c_int)]

class MotionEvent( Structure ):
	_fields_ = [
		('type', c_int),
		('serial', c_ulong),
		('send_event', Bool),
		('display', Display),
		('window', Window),
		('root', Window),
		('subwindow', Window),
		('time', Time),
		('x', c_int), ('y', c_int),
		('x_root', c_int), ('y_root', c_int),
		('state', c_uint),
		('is_hint', c_char),
		('same_screen', Bool)
	]

# display is ignored, as is arg!
EventPredicate = CFUNCTYPE( Bool, Display, POINTER( Event ), XPointer )

print( xlib )

display = xlib.XOpenDisplay( None )
if not display: sys.exit()
root_window = xlib.XRootWindow( display, 0 )

print( display, root_window )



def is_sublime( window ):
	nameAtom = xlib.XInternAtom( display, "_NET_WM_NAME", 0 )
	utf8Atom = xlib.XInternAtom( display, "UTF8_STRING", 0 )

	_type = Atom()
	_format = c_int()
	nitems = c_ulong()
	after = c_ulong()
	data = POINTER( c_ubyte )()

	s = xlib.XGetWindowProperty( display, window, nameAtom, 0, 65536, 0,\
		utf8Atom, byref( _type ), byref( _format ), byref( nitems ),\
		byref( after ), byref( data ) )
	print( s )
	print( data )

#print( is_sublime( root_window ) )



def get_client_list2( display, root ):
	children = WindowPtr()
	num = c_uint()
	s = xlib.XQueryTree( display, root, byref( Window() ), byref( Window() ), byref( children ), byref( num ) )
	print( s )
	arr = (Window * num.value ).from_address( addressof( children ) )
	xlib.XFree( children )
	for win in arr:
		print( "window:", win )
		print( is_sublime( win ) )
	return arr

MAX_PROPERTY_VALUE_LEN = 4096
def get_property( d, w, xa_prop_type, prop_name ):
	xa_prop_name = Atom( xlib.XInternAtom( d, prop_name, False ) )
	xa_ret_type = Atom()
	ret_format = c_int()
	ret_nitems = c_ulong()
	ret_bytes_after = c_ulong()
	tmp_size = c_ulong()
	ret_prop = POINTER( c_ubyte )()
	l = int( MAX_PROPERTY_VALUE_LEN / 4 )

	s = xlib.XGetWindowProperty( d, w, xa_prop_name, 0, l, False,\
		xa_prop_type, r( xa_ret_type ), r( ret_format ), r( ret_nitems ),\
		r( ret_bytes_after ), r( ret_prop ) )

	print( s )
	if s:	
		print( "can't get property")
		return

	if xa_ret_type != xa_prop_type:
		print( "invalid type", xa_ret_type, xa_prop_type )
		xlib.XFree( ret_prop )
		#return

	print( 1337 )

	tmp_size = int(ret_format.value / int(32 / sizeof( c_long ) ) ) * ret_nitems.value
	ret = (c_char * (tmp_size + 1)).from_buffer_copy( ret_prop )
	#ret.raw[tmp_size] = '\0'

	xlib.XFree( ret_prop )
	return (ret, tmp_size)


XA_WINDOW = Atom( 33 )
def get_client_list( display, root ):
	r = get_property( display, root, Atom( xlib.XInternAtom( display, "UTF8_STRING", 0 ) ), "_NET_WM_NAME" )
	r = get_property( display, root, XA_WINDOW, "_NET_CLIENT_LIST" )
	print( r )

	arr = 1
	return arr

print( get_client_list( display, root_window ) )


quit()


xlib.XSelectInput( display, root_window, PointerMotionMask );

while True:
	def motion_predicate( d, event, a ):
		print( 1340 )
		return event.contents.type == MotionNotify

	pred = EventPredicate( motion_predicate )

	event = MotionEvent()

	xlib.XPeekIfEvent( display, byref( event ), pred, None )
	print( event )


xlib.XCloseDisplay( display )



"""
static gchar *get_property (Display *disp, Window win, /*{{{*/
        Atom xa_prop_type, gchar *prop_name, unsigned long *size) {
    Atom xa_prop_name;
    Atom xa_ret_type;
    int ret_format;
    unsigned long ret_nitems;
    unsigned long ret_bytes_after;
    unsigned long tmp_size;
    unsigned char *ret_prop;
    gchar *ret;
    
    xa_prop_name = XInternAtom(disp, prop_name, False);
    
    /* MAX_PROPERTY_VALUE_LEN / 4 explanation (XGetWindowProperty manpage):
     *
     * long_length = Specifies the length in 32-bit multiples of the
     *               data to be retrieved.
     */
    if (XGetWindowProperty(disp, win, xa_prop_name, 0, MAX_PROPERTY_VALUE_LEN / 4, False,
            xa_prop_type, &xa_ret_type, &ret_format,     
            &ret_nitems, &ret_bytes_after, &ret_prop) != Success) {
        p_verbose("Cannot get %s property.\n", prop_name);
        return NULL;
    }
  
    if (xa_ret_type != xa_prop_type) {
        p_verbose("Invalid type of %s property.\n", prop_name);
        XFree(ret_prop);
        return NULL;
    }

    /* null terminate the result to make string handling easier */
    tmp_size = (ret_format / (32 / sizeof(long))) * ret_nitems;
    ret = g_malloc(tmp_size + 1);
    memcpy(ret, ret_prop, tmp_size);
    ret[tmp_size] = '\0';

    if (size) {
        *size = tmp_size;
    }
    
    XFree(ret_prop);
    return ret;
}/*}}}*/
"""

"""
static Window *get_client_list (Display *disp, unsigned long *size) {/*{{{*/
    Window *client_list;

    if ((client_list = (Window *)get_property(disp, DefaultRootWindow(disp), 
                    XA_WINDOW, "_NET_CLIENT_LIST", size)) == NULL) {
        if ((client_list = (Window *)get_property(disp, DefaultRootWindow(disp), 
                        XA_CARDINAL, "_WIN_CLIENT_LIST", size)) == NULL) {
            fputs("Cannot get client list properties. \n"
                  "(_NET_CLIENT_LIST or _WIN_CLIENT_LIST)"
                  "\n", stderr);
            return NULL;
        }
    }

    return client_list;
}/*}}}*/
"""

"""
  Atom nameAtom = XInternAtom(dpy,"_NET_WM_NAME",false);
  Atom utf8Atom = XInternAtom(dpy,"UTF8_STRING",false);
  Atom type;
  int format;
  unsigned long nitems, after;
  unsigned char *data = 0;

  if (Success == XGetWindowProperty(dpy, window, nameAtom, 0, 65536,
                                    false, utf8Atom, &type, &format,
                                    &nitems, &after, &data)) {
    if (data) {
      log.debug("Name: %s", data);
      XFree(data);
    }
  }
"""

"""
int XGetWindowProperty(display, w, property, long_offset, long_length, delete, req_type, 
                        actual_type_return, actual_format_return, nitems_return, bytes_after_return, 
                        prop_return)
      Display *display;
      Window w;
      Atom property;
      long long_offset, long_length;
      Bool delete;
      Atom req_type; 
      Atom *actual_type_return;
      int *actual_format_return;
      unsigned long *nitems_return;
      unsigned long *bytes_after_return;
      unsigned char **prop_return;
"""

"""
Status XQueryTree(display, w, root_return, parent_return, children_return, nchildren_return)
      Display *display;
      Window w;
      Window *root_return;
      Window *parent_return;
      Window **children_return;
      unsigned int *nchildren_return;
"""

"""
typedef struct {
	int type;		/* MotionNotify */
	unsigned long serial;	/* # of last request processed by server */
	Bool send_event;	/* true if this came from a SendEvent request */
	Display *display;	/* Display the event was read from */
	Window window;		/* ``event'' window reported relative to */
	Window root;		/* root window that the event occurred on */
	Window subwindow;	/* child window */
	Time time;		/* milliseconds */
	int x, y;		/* pointer x, y coordinates in event window */
	int x_root, y_root;	/* coordinates relative to root */
	unsigned int state;	/* key or button mask */
	char is_hint;		/* detail */
	Bool same_screen;	/* same screen flag */
} XMotionEvent;
typedef XMotionEvent XPointerMovedEvent;
"""

"""
Bool (*predicate)(display, event, arg)
     Display *display;
     XEvent *event;
     XPointer arg;
"""

"""
XPeekIfEvent(display, event_return, predicate, arg)
      Display *display;
      XEvent *event_return;
      Bool (*predicate)();
      XPointer arg;
"""

"""
#include <stdio.h>
#include <X11/Xlib.h>

char *key_name[] = {
    "first",
    "second (or middle)",
    "third",
    "fourth",  // :D
    "fivth"    // :|
};

int main(int argc, char **argv)
{
    Display *display;
    XEvent xevent;
    Window window;

    if( (display = XOpenDisplay(NULL)) == NULL )
        return -1;


    window = DefaultRootWindow(display);
    XAllowEvents(display, AsyncBoth, CurrentTime);

    XGrabPointer(display, 
                 window,
                 1, 
                 PointerMotionMask | ButtonPressMask | ButtonReleaseMask , 
                 GrabModeAsync,
                 GrabModeAsync, 
                 None,
                 None,
                 CurrentTime);

    while(1) {
        XNextEvent(display, &xevent);

        switch (xevent.type) {
            case MotionNotify:
                printf("Mouse move      : [%d, %d]\n", xevent.xmotion.x_root, xevent.xmotion.y_root);
                break;
            case ButtonPress:
                printf("Button pressed  : %s\n", key_name[xevent.xbutton.button - 1]);
                break;
            case ButtonRelease:
                printf("Button released : %s\n", key_name[xevent.xbutton.button - 1]);
                break;
        }
    }

    return 0;
}
"""