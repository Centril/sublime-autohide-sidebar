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

ID = 'sublime-autohide-sidebar'

#
# Import stuff:
#
from sublime import active_window, windows, load_settings, set_timeout_async
from sublime_plugin import EventListener
from .counter import Counter

#
# Cross platform mouse movement event handler 
#
from .driver import Driver

#
# Constants:
#
HIDE_DEFAULT_X = 450

def hs_padding_x():
	global settings
	return settings.get( 'hide_show_padding_x' )

#
# Per window wrapper:
#
class Wrapper( object ):
	def __init__( self, window ):
		global D
		self.id = window.id()
		self.window = window
		self.toggled = False
		self.suspended = False

		D.register_new_window( self.id )
		if self.is_sidebar_open(): self._toggle()

	# Thanks https://github.com/titoBouzout
	# https://github.com/SublimeText/SideBarFolders/blob/fb4b2ba5b8fe5b14453eebe8db05a6c1b918e029/SideBarFolders.py#L59-L75
	def is_sidebar_open( self ):
		view = self.window.active_view()
		if view:
			sel1 = view.sel()[0]
			self.window.run_command( 'focus_side_bar' )
			self.window.run_command( 'move',
				{"by": "characters", "forward": True} )
			sel2 = view.sel()[0]
			if sel1 != sel2:
				self.window.run_command( 'move',
					{"by": "characters", "forward": False} )
				return False
			else:
				group, index = self.window.get_view_index( view )
				self.window.focus_view( view )
				self.window.focus_group( group )
				return True
		return True # by default assume it's open if no view is opened

	# Toggles the sidebar:
	def _toggle( self ): self.window.run_command( "toggle_side_bar", ID )

	def toggle_suspended( self ):
		self.suspended = not self.suspended
		self.toggled = not self.toggled

	# Given an x coordinate: whether or not sidebar should hide:
	def should_hide( self, x ):
		global D
		w = D.window_width( self.id ) or HIDE_DEFAULT_X
		w2 = self.window.active_view().viewport_extent()[0] or 0
		return x >= (w - w2 - hs_padding_x() * 2)

	# Given an x coordinate: whether or not sidebar should show:
	def should_show( self, x ): return x < hs_padding_x()

	# Toggles side bar if pred is fulfilled and flips toggled state:
	def win_if_toggle( self, pred ):
		if self.suspended: return
		if pred( self.toggled ):
			self.toggled = not self.toggled
			self._toggle()

	# Hides sidebar if it should be hidden, or shows if it should:
	def hide_or_show( self ):
		global D
		if self.suspended: return
		r = D.window_coordinates( self.id )
		self.toggled = (not self.should_hide( r[0] )
						if self.is_sidebar_open()
						else self.should_show( r[0] ) )\
						if r else False
		if (self.toggled if r else self.is_sidebar_open()): self._toggle()

	# On move handler:
	def move( self, x ):
		self.win_if_toggle( lambda s:
			(self.should_hide if s else self.should_show)( x ))

	# On leave handler:
	def leave( self ): self.win_if_toggle( lambda s: s )

#
# Making and getting wrappers:
#
def reset_wrappers():
	global wrappers
	wrappers = {}

# Returns a wrapper for _id:
def wrapper( _id ):
	global wrappers
	return wrappers[_id or active_window().id()]

# Registers a new window:
def register_new( window ):
	global wrappers
	w = Wrapper( window )
	wrappers[w.id] = w
	return w

# Returns the wrapper, registers it if not:
def wrapper_or_register( window ):
	global wrappers
	_id = window.id()
	return wrapper( _id ) if _id in wrappers else register_new( window )

#
# Plugin listeners & loading:
#

# Get an on_load_counter, or set one if not before:
on_load_counters = {}
def on_load_counter( _id ):
	global on_load_counters
	if _id not in on_load_counters: on_load_counters[_id] = Counter()
	return on_load_counters[_id]

# Hide sidebars in new windows:
class Listener( EventListener ):
	# Non-fake toggle_side_bar: Suspend tracking for this window!
	def on_window_command( self, window, name, args ):
		if name == 'toggle_side_bar' and args != ID:
			wrapper( window.id() ).toggle_suspended()

	# Wait: last on_load in sequence => make or get wrapper and hide/show it.
	def on_load( self, view ):
		w = view.window()
		c = on_load_counter( w.id() )
		c.inc()

		# Handle on_load, get the appropriate wrapper or make one:
		set_timeout_async( lambda: not c.dec() and
			wrapper_or_register( w ).hide_or_show(), 0 )

def plugin_loaded():
	print( "pre-load-settings")
	# Load settings:
	global settings
	settings = load_settings( 'sublime-autohide-sidebar.sublime-settings' )
	print( "post-load-settings" )

	# Hide ALL sidebars:
	global D, T
	D = Driver()
	reset_wrappers()
	for w in windows(): register_new( w )

	# Start receiving events:
	def move( _id, x, y ): wrapper( _id ).move( x )
	def leave( _id ): wrapper( _id ).leave()
	T = D.tracker( move, leave )
	T.start()
	print( "post-T.start()")

def plugin_unloaded():
	print("stop#1")
	# Stop receiving events:
	global D, T
	T.stopx()