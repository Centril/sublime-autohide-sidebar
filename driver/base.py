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

from threading import Thread
import atexit

"""
Utils:
"""

def find_key( _dict, needle ):
	return next( (k for k, v in _dict.items() if v == needle), None )

# Converts (x, y) from coordinates of system with
# origin at (xf, yf) to one with origin at (xt - xf, yt - yf).
def map_coordinates( xf, yf, xt, yt, x, y ):
	return (x - (xt - xf), y - (yt - yf))

"""
Move driver:
"""
class MoveEventMeta( Thread ):
	def __init__( self, driver, move, leave, daemon = True ):
		Thread.__init__( self )
		self.daemon = daemon
		self.alive = False
		self.driver = driver
		self.move = move
		self.leave = leave

	def start( self ):
		self.alive = True
		Thread.start( self )

	def stopx( self ):
		if self.alive:
			self.alive = False
			self._stopx()

	def _stopx( self ): pass
	def run( self ): pass

"""
Driver:
"""
class DriverMeta( object ):
	def __init__( self ): pass
	def window_coordinates( self, _id ): pass
	def window_width( self, _id ): pass
	def register_new_window( self, _id ): pass
	def tracker( self, move, leave ): pass