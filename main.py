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
from .counter import Counter

# TEMPORARY @TODO REMOVE
#sublime.log_commands( True )

# Cross platform mouse movement event handler 
import sys
if sys.platform == 'darwin':
	from .mac import MoveEvent, register_new_window, window_coordinates
elif sys.platform == 'win32':
	from .windows import MoveEvent, register_new_window, window_coordinates
else:
	from .x11 import MoveEvent, register_new_window, window_coordinates

# Holds toggled states and on_load counter per window:
states = {}
on_load_counter = {}
last_window = sublime.active_window().id()

# Thanks https://github.com/titoBouzout
# https://github.com/SublimeText/SideBarFolders/blob/fb4b2ba5b8fe5b14453eebe8db05a6c1b918e029/SideBarFolders.py#L59-L75
def is_sidebar_open( window ):
	view = window.active_view()
	if view:
		sel1 = view.sel()[0]
		window.run_command( 'focus_side_bar' )
		window.run_command( 'move', {"by": "characters", "forward": True} )
		sel2 = view.sel()[0]
		if sel1 != sel2:
			window.run_command( 'move', {"by": "characters", "forward": False} )
			return False
		else:
			group, index = window.get_view_index( view )
			window.focus_view( view )
			window.focus_group( group )
			return True
	return True # by default assume it's open if no view is opened

# Toggles the sidebar:
def _toggle( window ): window.run_command( "toggle_side_bar" )

# Toggles side bar and remembers state:
def toggle( window ):
	global states
	_id = window.id()
	old = states[_id]
	states[_id] = not old
	_toggle( window )

# Given an x coordinate: whether or not sidebar should hide:
def should_hide( x ): return x >= 300

# Given an x coordinate: whether or not sidebar should show:
def should_show( x ): return x < 25

# Registers a new window:
def register_new( _id ):
	global on_load_counter
	register_new_window( _id )
	on_load_counter[_id] = Counter()

# Hides sidebar if it should be hidden, or shows if it should:
def hide_or_show( _id, window ):
	global states
	r = window_coordinates( _id )
	states[_id] = (not should_hide( r[0] ) if is_sidebar_open( window ) else should_show( r[0] )) if r else False
	if (states[_id] if r else is_sidebar_open( window )): _toggle( window )

def window_from_id( _id ):
	if _id:
		for w in sublime.windows():
			if _id == w.id(): return w
	else: return sublime.active_window()

def win_if_toggle( _id, pred ):
	global states
	window = window_from_id( _id )
	if window and pred( states[_id] ): toggle( window )

# Hide sidebars in new windows:
class NewWindowListener( sublime_plugin.EventListener ):
	def on_post_window_command( self, window, name, args ):
		if name != "new_window": return
		global states, last_window
		last_window += 1
		_id = last_window

		register_new( _id )

		states[_id] = False
		if is_sidebar_open( window ): _toggle( window )

	def on_load(self, view):
		global on_load_counter
		window = view.window()
		_id = window.id()
		c = on_load_counter[_id]
		c.inc()
		sublime.set_timeout_async( lambda: not c.dec() and hide_or_show( _id, window ), 0 )

class Tracker( MoveEvent ):
	def move( self, _id, x, y ): win_if_toggle( _id, lambda s: (should_hide if s else should_show)( x ) )
	def leave( self, _id ): win_if_toggle( _id, lambda s: s )

T = Tracker()

def plugin_loaded():
	# Hide ALL sidebars:
	for window in sublime.windows():
		_id = window.id()
		register_new( _id )
		if is_sidebar_open( window ): _toggle( window )
		states[_id] = False

	T.start()

def plugin_unloaded():
	T.stop()