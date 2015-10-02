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

from .base import MoveEventMeta

import atexit
from ctypes import *
from ctypes.wintypes import BOOL, HWND, LONG, INT, WPARAM, LPARAM, DWORD
[user32, kernel32, version, psapi, dwmapi] = [windll.user32, windll.kernel32, windll.version, windll.psapi, windll.dwmapi]

"""
Win32 types:
"""

class POINT( Structure ):
	_fields_ = [('x', LONG), ('y', LONG)]

class RECT( Structure ):
	_fields_ = [('l', LONG), ('t', LONG), ('r', LONG), ('b', LONG)]

class MSLLHOOKSTRUCT( Structure ):
	_fields_ = [("pt", POINT)]

"""
Win32 constants:
"""

WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
GA_ROOT = 2
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
#DWMWA_EXTENDED_FRAME_BOUNDS = 9

HookProc = WINFUNCTYPE( LONG, INT, WPARAM, POINTER( MSLLHOOKSTRUCT ) )
EnumWindowsProc = WINFUNCTYPE( BOOL, HWND, LPARAM )
MODULE_HANDLE = windll.kernel32.GetModuleHandleW( None )

# Get the window where point resides:
def get_hwnd( x, y ):
	hwnd = user32.WindowFromPhysicalPoint( POINT( x, y ) )
	return user32.GetAncestor( hwnd, GA_ROOT ) if hwnd else None

"""
is_sublime:
"""

# Returns PID of process:
def get_pid( hwnd ):
	pid = DWORD()
	user32.GetWindowThreadProcessId( hwnd, byref( pid ) )
	return pid

# Strips null terminated bytes and whitespace:
import re
def strip_win32_string( s ):
	return re.sub('[ \n\t\0]+', '', s[:].strip() )

# Executes a lambda with a buffer with the buffer and length:
def buffer_get( l, fn ):
	actual_len = l
	while actual_len == l:
		l *= 2
		v = create_unicode_buffer( l )
		actual_len = fn( v, len( v ) )
		if not actual_len: return
	return strip_win32_string( v )

# Returns name of pid:s process:
def process_name( pid ):
	# Get process of window:
	process = kernel32.OpenProcess( PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, 0, pid )
	if not process: return

	# Get process basename (test for sublime_text.exe):
	try: return buffer_get( 130, lambda v, l: psapi.GetModuleBaseNameW( process, None, v, l ) )
	except: return
	finally: kernel32.CloseHandle( process )

# Determines if a window is sublime window:
def is_sublime( hwnd ):
	className = buffer_get( 15, lambda v, l: user32.GetClassNameW( hwnd, v, l ) )
	if className != "PX_WINDOW_CLASS": return False

	pid = get_pid( hwnd )
	name = process_name( pid )
	return name and name.rsplit( '.', 2 )[0] == "sublime_text"

"""
Move event logic:
"""

def metrics():
	[l, t, w, h] = [user32.GetSystemMetrics( w ) for w in [76, 77, 78, 79]]
	return [l, t, w - l, h + t]

# Converts (x, y) from coordinates of system with
# origin at (xf, yf) to one with origin at (xt - xf, yt - yf).
def map_coordinates( xf, yf, xt, yt, x, y ):
	return (x - (xt - xf), y - (yt - yf))

entered_windows = []
def handle_event( self, x, y ):
	global win_map, entered_windows

	# Get window where cursor is located:
	p = POINT()
	user32.GetPhysicalCursorPos( byref( p ) )
	x, y = p.x, p.y
	hwnd = get_hwnd( x, y )
	if not (hwnd and hwnd in win_map): return

	# Map cursor pos to window coordinates:
	rect = RECT()
	if not user32.GetWindowRect( hwnd, byref( rect ) ): return
#	DPI scaling issues? the outcommented code works fine on non-scaled, works bad on scaled.
#	if dwmapi.DwmGetWindowAttribute( hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, byref( rect ), sizeof( RECT ) ):
#		return
	x, y = map_coordinates( 0, 0, rect.l, rect.t, x, y )

	# Add to stack of entered_window:
	window = win_map[hwnd]
	if window not in entered_windows: entered_windows.append( window )

	# Move!
	self.move( window, x, y )
	return window

win_map = {}
def register_new_window( window ):
	global win_map
	windows = win_map.values()
	if window in windows: return

	def cb( hwnd, lParam ):
		if (hwnd in win_map): return 1
		if (not is_sublime( hwnd )): return 1
		win_map[hwnd] = window
		return 0

	user32.EnumWindows( EnumWindowsProc( cb ), None )

class MoveEvent( MoveEventMeta ):
	def run( self ):
		def py_cb( nCode, wParam, lParam ):
			global entered_windows
			if nCode >= 0 and wParam == WM_MOUSEMOVE:
				# Handle move events:
				[l, t, r, b] = metrics()
				[x, y] = [lParam.contents.pt.x, lParam.contents.pt.y]
				window = handle_event( self, max( l, min( r, x ) ), max( t, min( b, y ) ) )

				# Handle leave events:
				leaving = entered_windows[:]
				entered_windows = []
				for w in leaving:
					if w != window: self.leave( w )
					else: entered_windows.append( w )

			return user32.CallNextHookEx( None, nCode, wParam, lParam )

		# Register callback:
		cb = HookProc( py_cb )
		self.hook = user32.SetWindowsHookExA( WH_MOUSE_LL, cb, MODULE_HANDLE, 0 )

		# Event pump:
		atexit.register( self.stop )
		while self.alive:
			msg = user32.GetMessageW( None, 0, 0, 0 )
			user32.TranslateMessage( byref( msg ) )
			user32.DispatchMessageW( byref( msg ) )

	def _stop( self ):
		user32.UnhookWindowsHookEx( self.hook )