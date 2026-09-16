# -*- coding: utf-8 -*-
"""Base screen abstract interface defining the screen lifecycle."""


class BaseScreen:
    """Base class for all RetroHub screens."""
    def __init__(self, engine=None):
        self.engine = engine
        self.selected_idx = 0
        self.scroll_offset = 0

    def on_enter(self, params=None):
        """Called when screen is pushed onto stack or navigated to."""
        pass

    def on_exit(self):
        """Called when screen is popped or replaced."""
        pass

    def handle_input(self, inputs):
        """Process input keys and return True if consumed."""
        return False

    def update(self, dt):
        """Periodic logic update."""
        pass

    def render(self, engine):
        """Render the screen's main content area."""
        pass

    def get_header_title(self):
        """Return the title string to display in header bar."""
        return "RetroHub"

    def get_footer_actions(self):
        """Return list of tuple action definitions for footer: (btn_key, label_str, btn_col, txt_col, is_dark)."""
        return []
