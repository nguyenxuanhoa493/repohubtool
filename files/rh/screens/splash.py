# -*- coding: utf-8 -*-
"""Boot Splash Manager and Full-Screen Preview Screen."""

import os
from .. import state
from ..paths import SPLASH_TEMP_PREVIEW
from ..i18n import tr
from ..splash import (scan_splash_images, apply_splash_update,
                     restore_original_splash, convert_and_fit_splash)
from .base import BaseScreen


class SplashScreen(BaseScreen):
    """Boot splash image manager and converter screen."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.view_mode = "list"  # list or preview
        self.images = []
        self.selected_idx = 0
        self.scroll_top = 0
        self.preview_path = None

    def on_enter(self, params=None):
        self.show_list()

    def show_list(self):
        self.view_mode = "list"
        self.images = scan_splash_images() or []
        self.selected_idx = 0
        self.scroll_top = 0

    def get_header_title(self):
        return "XEM TRƯỚC ẢNH KHỞI ĐỘNG" if self.view_mode == "preview" else tr("splash_title")

    def get_footer_actions(self):
        if self.view_mode == "preview":
            return [
                ("A", "Cài làm ảnh khởi động", (0, 230, 150), (220, 225, 235), True),
                ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
            ]
        return [
            ("A", "Xem trước", (0, 230, 150), (220, 225, 235), True),
            ("Y", "Khôi phục gốc", (255, 200, 0), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_y = inputs.get("btn_y")

        if btn_b:
            if self.view_mode == "preview":
                self.show_list()
            else:
                self.engine.pop_screen()
            return True

        if self.view_mode == "list":
            if btn_y:
                # Restore original
                ok, msg = restore_original_splash()
                self.engine.toast(msg)
                return True

            num_items = len(self.images)
            if num_items == 0:
                return False
            max_visible = 6

            if btn_up:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                else:
                    self.selected_idx = num_items - 1
                    self.scroll_top = max(0, num_items - max_visible)
                if self.selected_idx < self.scroll_top:
                    self.scroll_top = self.selected_idx
                return True
            elif btn_down:
                if self.selected_idx < num_items - 1:
                    self.selected_idx += 1
                else:
                    self.selected_idx = 0
                    self.scroll_top = 0
                if self.selected_idx >= self.scroll_top + max_visible:
                    self.scroll_top = self.selected_idx - max_visible + 1
                return True

            if btn_a and 0 <= self.selected_idx < len(self.images):
                img_p = self.images[self.selected_idx]
                self.preview_path = img_p
                self.view_mode = "preview"
                return True

        elif self.view_mode == "preview":
            if btn_a and self.preview_path:
                ok, msg = apply_splash_update(self.preview_path)
                self.engine.toast(msg)
                self.show_list()
                return True

        return False

    def render(self, engine):
        if self.view_mode == "preview":
            # Full screen image preview
            if self.preview_path and os.path.exists(self.preview_path):
                engine.draw_proportional_boxart(self.preview_path, 0, 0, state.SCREEN_W, state.SCREEN_H)
            return

        # List of available splashes
        num_items = len(self.images)
        panel_margin = 40
        panel_x = panel_margin
        panel_w = state.SCREEN_W - (panel_margin * 2)

        card_h = 76
        gap = 10
        start_y = 64 + 14
        max_visible = 6

        if not self.images:
            engine.draw_text("CHƯA CÓ ẢNH TRONG THƯ MỤC /mnt/SDCARD/Splash/", engine.font_item, state.SCREEN_W // 2, state.SCREEN_H // 2, 140, 160, 190, center_x=True, center_y=True)
            return

        max_scroll = max(0, num_items - max_visible)
        if self.selected_idx < self.scroll_top:
            self.scroll_top = self.selected_idx
        elif self.selected_idx >= self.scroll_top + max_visible:
            self.scroll_top = self.selected_idx - max_visible + 1
        self.scroll_top = max(0, min(max_scroll, self.scroll_top))

        vis_imgs = self.images[self.scroll_top : self.scroll_top + max_visible]

        for i, ip in enumerate(vis_imgs):
            actual_idx = self.scroll_top + i
            cy = start_y + i * (card_h + gap)
            is_sel = (actual_idx == self.selected_idx)
            fn = os.path.basename(ip)

            if is_sel:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 28, 44, 75, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                text_r, text_g, text_b = 255, 255, 255
            else:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 19, 26, 42, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 40, 54, 85, 255, thickness=1)
                text_r, text_g, text_b = 200, 210, 225

            item_title = f"{actual_idx + 1}. {fn[:42]}"
            engine.draw_text(item_title, engine.font_item, panel_x + 28, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)
