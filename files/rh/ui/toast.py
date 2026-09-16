# -*- coding: utf-8 -*-
"""Toast notification manager for rendering non-blocking notifications on top of the UI."""

import time
from .. import state
from .primitives import fill_rect, draw_rect, draw_text


class ToastManager:
    """Manages and renders temporary overlay notifications at the topmost layer."""
    def __init__(self):
        self.message = None
        self.timestamp = 0.0
        self.duration = 3.0
        self.text_color = (0, 246, 246)
        self.bg_color = (14, 26, 46, 250)
        self.border_color = (0, 246, 246, 255)

    def show(self, msg, duration=3.0, text_color=(0, 246, 246), bg_color=(14, 26, 46, 250), border_color=(0, 246, 246, 255)):
        """Display a toast notification."""
        if not msg:
            return
        self.message = str(msg)
        self.timestamp = time.time()
        self.duration = duration
        self.text_color = text_color
        self.bg_color = bg_color
        self.border_color = border_color

    def clear(self):
        self.message = None

    def is_active(self):
        if not self.message:
            return False
        return (time.time() - self.timestamp) < self.duration

    def render(self, renderer, font_toast, text_texture_cache=None):
        if not self.is_active():
            return
        now = time.time()
        toast_margin = 40
        tw = state.SCREEN_W - (toast_margin * 2)
        th = 48
        tx = toast_margin
        ty = state.SCREEN_H - th - 52
        
        bg_r, bg_g, bg_b, bg_a = self.bg_color if len(self.bg_color) == 4 else (*self.bg_color, 250)
        bd_r, bd_g, bd_b, bd_a = self.border_color if len(self.border_color) == 4 else (*self.border_color, 255)
        tx_r, tx_g, tx_b = self.text_color[:3]

        fill_rect(renderer, tx, ty, tw, th, bg_r, bg_g, bg_b, bg_a)
        draw_rect(renderer, tx, ty, tw, th, bd_r, bd_g, bd_b, bd_a, thickness=2)
        draw_text(renderer, self.message, font_toast, tx + tw // 2, ty + th // 2,
                  tx_r, tx_g, tx_b, center_x=True, center_y=True, text_texture_cache=text_texture_cache)
