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

#
# Cross platform mouse movement event handler 
#
import sys
if sys.platform == 'darwin':
	from .mac import MoveEvent,\
		driver_load, register_new_window, window_coordinates, window_width
elif sys.platform == 'win32':
	from .windows import MoveEvent,\
		driver_load, register_new_window, window_coordinates, window_width
else:
	from .X11 import Driver