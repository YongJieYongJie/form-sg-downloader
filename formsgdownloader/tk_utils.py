"""This tk_utils module provides various wrapper classes for `tk` and `ttk`
widgets to expose a more consistent API.
"""


import tkinter as tk
from tkinter import ttk
from collections import namedtuple


MenuAction = namedtuple('MenuAction', 'name handler')


class YjMenu(tk.Menu):
    """Wrapper class for `tk.Menu`. Provides a skeletal main menu with a
    single "File" menu, and consistent API for adding either commands or
    submenus.
    """

    def __init__(self, master, *args, **kwargs):

        super().__init__(master, *args, **kwargs)

        menu_items = [
            ('File', [
                MenuAction('Exit', master.quit),
            ]),
        ]

        for name, handler_or_submenu in menu_items:
            self.add_command_or_submenu(name, handler_or_submenu)

    def add_to_file_menu(self, name, handler):
        """Add a menu item `name` to the "File" menu that triggers `handler`
        when clicked.
        """

        file_menu_index = self.index('File') - 1 # Tcl is 1-based index
        file_menu = list(self.children.values())[file_menu_index]
        file_menu.insert_command(index=0, label=name, command=handler)

    def add_command_or_submenu(self, name, handler_or_submenu):
        """Add a top-level menu item `name` that either (a) triggers a
        handler `handler_or_submenu` when clicked, or (b) is a submenu
        where `handler_or_submenu` contains an iterable tuples of (i) name,
        handler or (ii) name, submenu which will be processed recursively.
        """

        try: # Assume there is submenu
            submenu = tk.Menu(self, tearoff=0)
            for submenu_name, handler in handler_or_submenu:
                submenu.add_command(label=submenu_name, command=handler)
            self.add_cascade(label=name, menu=submenu)
        except TypeError: # Unable to unpack tuple, assume no submenu
            self.add_command(label=name, command=handler_or_submenu)


class YjTreeview(ttk.Treeview):
    """Wrapper class for `ttk.Treeview`, for use as a "detailed list" display
    without nesting.

    Args:
      parent (tk widget): The parent widget.
      columns (tuple of string): The columns of the detail view.
      *args (various): Passed directly to `ttk.Treeview`.
      **kwargs (various): Passed directly to `ttk.Treeview`.
    """

    def __init__(self, parent, *args, **kwargs):

        # Separating the first columns from the rest because it is treated
        #   differently by tk/tcl.
        if 'columns' in kwargs and len(kwargs['columns']) > 0:
            first_column, *the_rest = kwargs['columns']
            kwargs['columns'] = kwargs['columns'][1:]

        super().__init__(parent, *args, **kwargs)

        self.heading('#0', text=first_column)
        for header in the_rest:
            self.heading(header, text=header)

    def add_item(self, *column_values):
        """Adds an item

        Args:
            *columns_value (tuple of strings): A tuple of string corresponding
                to each column of the item to be added.
        """

        self.insert('', 'end', text=column_values[0],
            values=tuple(column_values[1:]))
