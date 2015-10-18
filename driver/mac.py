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

from .base import DriverMeta, MoveEventMeta, find_key, map_coordinates

from os import popen
from ctypes import *
from ctypes.util import find_library

def lib( l ):
	path = find_library( l )
	if not path: quit( "Can't find %s!" % l )
	return CDLL( path )

Q = lib( "quartz" )

class Window( object ):
	def __init__( self ):
		pass

	def pid( self ):
		pass

	def title( self ):
		pass

# Checks if window is a sublime text window:
def is_sublime( win ):
	pid = win.pid()
	if not pid: return False
	r = popen( "ps -p %s -c -o command" % pid ).read().split()
	if len( r ) and "sublime_text" in r[-1]: return True
	# Fallback approach:
	title = win.title()
	return title.endswith( ' - Sublime Text' ) if title else False


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
		# Create win_map, Initialize X11: Threading, get Display:
		self.win_map = {}
		pass

	def window_coordinates( self, _id ):
		# Fetch window or quit if not available:
		win = find_key( self.win_map, _id )
		if not win: return
		return None

	def window_width( self, _id ):
		win = find_key( self.win_map, _id )
		return None

	def register_new_window( self, _id ):
		if find_key( self.win_map, _id ): return
		return None

	def tracker( self, move, leave ):
		return MoveEvent( self, move, leave )