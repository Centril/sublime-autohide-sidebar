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

__author__ = "Mazdak Farrokhzad"
__copyright__ = "Copyright 2015, Mazdak Farrokhzad"
__credits__ = []
__license__ = "GPL3+"
__version__ = "0.0.1"
__maintainer__ = "Mazdak Farrokhzad"
__email__ = "twingoow@gmail.com"
__status__ = "Development"

import sublime, sublime_plugin

# TEMPORARY @TODO REMOVE
sublime.log_commands( True )

# Cross platform mouse movement event handler 
import sys
if sys.platform == 'darwin':
	from mac import MoveEvent
elif sys.platform == 'win32':
	from .windows import MoveEvent
else:
	from x11 import MoveEvent

# Holds toggled states per window:
states = {}

# Thanks https://github.com/titoBouzout
# https://github.com/SublimeText/SideBarFolders/blob/fb4b2ba5b8fe5b14453eebe8db05a6c1b918e029/SideBarFolders.py#L59-L75
def is_sidebar_open( window ):
	view = window.active_view()
	if view:
		sel1 = view.sel()[0]
		window.run_command('focus_side_bar')
		window.run_command('move', {"by": "characters", "forward": True})
		sel2 = view.sel()[0]
		if sel1 != sel2:
			window.run_command('move', {"by": "characters", "forward": False})
			return False
		else:
			group, index = window.get_view_index(view)
			window.focus_view(view)
			window.focus_group(group)
			return True
	return True # by default assume it's open if no view is opened

# Toggles the sidebar:
def _toggle( window ):
	window.run_command( "toggle_side_bar" )

# Toggles side bar and remembers state:
def toggle( window ):
	global states
	_id = window.id()
	old = states[_id]
	states[_id] = not old
	_toggle( window )

# Given an x coordinate: whether or not sidebar should hide:
def should_hide( x ):
	return x >= 300

# Given an x coordinate: whether or not sidebar should show:
def should_show( x ):
	return x < 50

# Forces the sidebar of a window to hide:
def force_hide( window ):
	global states
	print( 1337 )
	_id = window.id()
	if is_sidebar_open( window ):
		_toggle( window )
	states[_id] = False


# Hide ALL sidebars:
for w in sublime.windows(): force_hide( w )

for window in sublime.windows():
	_id = window.id()
	if is_sidebar_open( window ):
		_toggle( window )
	states[_id] = False

# Hide new windows:
class NewWindowListener( sublime_plugin.EventListener ):
	def on_window_command( self, window, name, args ):
		if name == "new_window":
			print( "new window!!!" )
			force_hide( window )

class M( MoveEvent ):
	def move( self, x, y ):
		window = sublime.active_window()
		_id = window.id()
		if (should_hide if states[_id] else should_show)( x ): toggle( window )

	def leave( self ):
		window = sublime.active_window()
		_id = window.id()
		if states[_id]: toggle( window )

m = M()
m.start()
#m.stop()