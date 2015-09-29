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
from ctypes.wintypes import LONG, INT, WPARAM, LPARAM, DWORD
[user32, kernel32, version, psapi, dwmapi] = [windll.user32, windll.kernel32, windll.version, windll.psapi, windll.dwmapi]

class POINT( Structure ):
	_fields_ = [('x', LONG), ('y', LONG)]

class RECT( Structure ):
	_fields_ = [('l', LONG), ('t', LONG), ('r', LONG), ('b', LONG)]

class MSLLHOOKSTRUCT( Structure ):
	_fields_ = [("pt", POINT)]

WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
GA_ROOT = 2
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
#DWMWA_EXTENDED_FRAME_BOUNDS = 9

HOOKPROC = WINFUNCTYPE( LONG, INT, WPARAM, POINTER( MSLLHOOKSTRUCT ) )
MODULE_HANDLE = windll.kernel32.GetModuleHandleW( None )

# Get the window where point resides:
def get_hwnd( x, y ):
	hwnd = user32.WindowFromPhysicalPoint( POINT( x, y ) )
	return user32.GetAncestor( hwnd, GA_ROOT ) if hwnd else None

def get_pid( hwnd ):
	pid = DWORD()
	user32.GetWindowThreadProcessId( hwnd, byref( pid ) )
	return pid

def process_name( pid ):
	# Get process of window:
	process = kernel32.OpenProcess( PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, 0, pid )
	if not process:
		return

	# Get process basename (test for sublime_text.exe):
	try:
		# We will immediately double the length up to MAX_PATH, but the
		# path may be longer, so we retry until the returned string is
		# shorter than our buffer.
		name_len = actual_len = 130
		while actual_len == name_len:
			name_len *= 2
			name = create_unicode_buffer( name_len )
			actual_len = psapi.GetModuleBaseNameW( process, None, name, len( name ) )
			if not actual_len:
				return

		return name[:]
	except:
		return
	finally:
		kernel32.CloseHandle( process )

def metrics():
	[l, t, w, h] = [user32.GetSystemMetrics( w ) for w in [76, 77, 78, 79]]
	return [l, t, w - l, h + t]

# Converts (x, y) from coordinates of system with
# origin at (xf, yf) to one with origin at (xt - xf, yt - yf).
def map_coordinates( xf, yf, xt, yt, x, y ):
	return (x - (xt - xf), y - (yt - yf))

def handle_event( self, x, y ):
	p = POINT()
	user32.GetPhysicalCursorPos( byref( p ) )
	x, y = p.x, p.y

	hwnd = get_hwnd( x, y )
	if not hwnd: return

	active = user32.GetForegroundWindow()
	if hwnd != active: return

	pid = get_pid( hwnd )
	name = process_name( pid )
	if not (name and name.rsplit( '.', 2 )[0] == "sublime_text"): return

	rect = RECT()
	if not user32.GetWindowRect( active, byref( rect ) ): return
#	DPI scaling issues?
#	if dwmapi.DwmGetWindowAttribute( active, DWMWA_EXTENDED_FRAME_BOUNDS, byref( rect ), sizeof( RECT ) ):
#		return
	x, y = map_coordinates( 0, 0, rect.l, rect.t, x, y )

	self.move( x, y )
	return True

class MoveEvent( MoveEventMeta ):
	def run( self ):
		def py_cb( nCode, wParam, lParam ):
			if nCode >= 0 and wParam == WM_MOUSEMOVE:
				[l, t, r, b] = metrics()
				[x, y] = [lParam.contents.pt.x, lParam.contents.pt.y]
				
				if not handle_event( self, max( l, min( r, x ) ), max( t, min( b, y ) ) ):
					self.leave()
			return user32.CallNextHookEx( None, nCode, wParam, lParam )

		# Register callback:
		cb = HOOKPROC( py_cb )
		self.hook = user32.SetWindowsHookExA( WH_MOUSE_LL, cb, MODULE_HANDLE, 0 )

		# Event pump:
		atexit.register( self.stop )
		while self.alive:
			msg = user32.GetMessageW( None, 0, 0, 0 )
			user32.TranslateMessage( byref( msg ) )
			user32.DispatchMessageW( byref( msg ) )

	def _stop( self ):
		user32.UnhookWindowsHookEx( self.hook )