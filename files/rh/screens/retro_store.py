# -*- coding: utf-8 -*-
"""Retro Store Screen - 3x2 Grid Menu."""

import os
from .. import state
from ..i18n import tr
from ..paths import APP_DIR
from .base import BaseScreen


class RetroStoreScreen(BaseScreen):
    """3x2 Grid Retro Store Hub containing Game Store, Theme Store, Icon Store, Emus Store, Cheat Code, Save Manager."""

    COLS = 3
    ROWS = 2
    TOTAL_ITEMS = 6

    def __init__(self, engine=None):
        super().__init__(engine)
        self.selected_idx = 0
        self.items = []

    def on_enter(self, params=None):
        self.items = [
            {
                "id": "item_games",
                "title": tr("retro_store_games"),
                "sub": tr("retro_store_games_sub"),
                "icon": os.path.join(APP_DIR, "assets", "emus_preview", "ic-arcade.png"),
                "action": "screen:store",
                "badge": "40K+ ROMs"
            },
            {
                "id": "item_themes",
                "title": tr("retro_store_themes"),
                "sub": tr("retro_store_themes_sub"),
                "icon": os.path.join(APP_DIR, "assets", "themes_preview", "TRIMUI_Blue.png"),
                "action": "screen:theme_store",
                "badge": "Themes"
            },
            {
                "id": "item_icons",
                "title": tr("retro_store_icons"),
                "sub": tr("retro_store_icons_sub"),
                "icon": os.path.join(APP_DIR, "assets", "icons_preview", "burst.png"),
                "action": "screen:icon_store",
                "badge": "Icon Packs"
            },
            {
                "id": "item_emus",
                "title": tr("retro_store_emus"),
                "sub": tr("retro_store_emus_sub"),
                "icon": os.path.join(APP_DIR, "assets", "emus_preview", "ic-ppsspp.png"),
                "action": "screen:emu_store",
                "badge": "Emulators"
            },
            {
                "id": "item_cheats",
                "title": tr("retro_store_cheats"),
                "sub": tr("retro_store_cheats_sub"),
                "icon": os.path.join(APP_DIR, "assets", "emus_preview", "ic-pico8.png"),
                "action": "modal:cheat",
                "badge": "Cheats"
            },
            {
                "id": "item_boxart",
                "title": tr("retro_store_boxart"),
                "sub": tr("retro_store_boxart_sub"),
                "icon": os.path.join(APP_DIR, "assets", "ic-boxart.png"),
                "action": "modal:boxart",
                "badge": "Scraper"
            }
        ]

    def get_header_title(self):
        return tr("retro_store_title")

    def get_footer_actions(self):
        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

        if btn_b:
            self.engine.pop_screen()
            return True

        row = self.selected_idx // self.COLS
        col = self.selected_idx % self.COLS

        if btn_left:
            if col > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = min(len(self.items) - 1, row * self.COLS + (self.COLS - 1))
            return True

        if btn_right:
            if col < self.COLS - 1 and self.selected_idx + 1 < len(self.items):
                self.selected_idx += 1
            else:
                self.selected_idx = row * self.COLS
            return True

        if btn_up:
            if row > 0:
                self.selected_idx -= self.COLS
            else:
                target = (self.ROWS - 1) * self.COLS + col
                self.selected_idx = min(len(self.items) - 1, target)
            return True

        if btn_down:
            if row < self.ROWS - 1:
                target = (row + 1) * self.COLS + col
                self.selected_idx = min(len(self.items) - 1, target)
            else:
                self.selected_idx = col
            return True

        if btn_a and 0 <= self.selected_idx < len(self.items):
            it = self.items[self.selected_idx]
            act = it.get("action", "")
            if act == "screen:store":
                self.engine.push_screen("store")
            elif act == "screen:theme_store":
                self.engine.push_screen("theme_store")
            elif act == "screen:icon_store":
                self.engine.push_screen("icon_store")
            elif act == "screen:emu_store":
                self.engine.push_screen("emu_store")
            elif act == "modal:cheat":
                from ..modals.common import CheatModal
                self.engine.open_modal(CheatModal(self.engine))
            elif act == "modal:boxart":
                from ..modals.common import BoxartScraperModal
                self.engine.open_modal(BoxartScraperModal(self.engine))
            return True

        return False

    def render(self, engine):
        if not self.items:
            return

        margin_x = 24
        start_y = 66
        gap_x = 16
        gap_y = 14

        total_grid_w = state.SCREEN_W - (margin_x * 2)
        card_w = (total_grid_w - (self.COLS - 1) * gap_x) // self.COLS
        card_h = 312

        for idx, item in enumerate(self.items):
            is_sel = (idx == self.selected_idx)
            col = idx % self.COLS
            row = idx // self.COLS

            card_x = margin_x + col * (card_w + gap_x)
            card_y = start_y + row * (card_h + gap_y)

            # 1. Background & Border
            if is_sel:
                engine.fill_rect(card_x, card_y, card_w, card_h, 24, 40, 68, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(card_x + 3, card_y + 3, card_w - 6, 3, 0, 246, 246, 255)
            else:
                engine.fill_rect(card_x, card_y, card_w, card_h, 16, 22, 36, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 36, 50, 78, 255, thickness=1)

            # 2. Icon / Preview Box
            img_x = card_x + 4
            img_y = card_y + 4
            img_w = card_w - 8
            img_h = card_h - 52

            engine.fill_rect(img_x, img_y, img_w, img_h, 10, 14, 22, 255)

            icon_path = item.get("icon")
            if icon_path and os.path.exists(icon_path):
                engine.draw_proportional_boxart(icon_path, img_x, img_y, img_w, img_h)
            else:
                engine.draw_text(item.get("title", ""), engine.font_grid_title,
                                 img_x + img_w // 2, img_y + img_h // 2,
                                 90, 115, 150, center_x=True, center_y=True)

            # Badge in top right corner of image
            badge_text = item.get("badge")
            if badge_text:
                bw = max(60, engine.measure_text(badge_text, engine.font_badge) + 14)
                bh = 22
                bx = img_x + img_w - bw - 8
                by = img_y + 8
                engine.fill_rect(bx, by, bw, bh, 12, 24, 40, 230)
                engine.draw_rect(bx, by, bw, bh, 0, 210, 255, 200, thickness=1)
                engine.draw_text(badge_text, engine.font_badge, bx + bw // 2, by + bh // 2, 0, 230, 255, center_x=True, center_y=True)

            # 3. Bottom Information Bar: Title (Clean, no description)
            bar_x = card_x + 4
            bar_y = card_y + img_h + 4
            bar_w = card_w - 8
            bar_h = 44

            if is_sel:
                engine.fill_rect(bar_x, bar_y, bar_w, bar_h, 24, 38, 64, 255)
                engine.fill_rect(bar_x, bar_y, bar_w, 2, 0, 246, 246, 255)
                title_color = (255, 255, 255)
            else:
                engine.fill_rect(bar_x, bar_y, bar_w, bar_h, 14, 18, 30, 255)
                engine.fill_rect(bar_x, bar_y, bar_w, 1, 35, 48, 72, 255)
                title_color = (210, 220, 235)

            # STT Badge (#1, #2, ...)
            stt_str = f"#{idx + 1}"
            stt_w = max(36, engine.measure_text(stt_str, engine.font_grid_title) + 10)
            stt_h = 26
            stt_x = bar_x + 8
            stt_y = bar_y + (bar_h - stt_h) // 2

            if is_sel:
                engine.fill_rect(stt_x, stt_y, stt_w, stt_h, 0, 210, 255, 255)
                engine.draw_text(stt_str, engine.font_grid_title, stt_x + stt_w // 2, stt_y + stt_h // 2, 0, 24, 48, center_x=True, center_y=True)
            else:
                engine.fill_rect(stt_x, stt_y, stt_w, stt_h, 24, 34, 52, 255)
                engine.draw_text(stt_str, engine.font_grid_title, stt_x + stt_w // 2, stt_y + stt_h // 2, 170, 195, 225, center_x=True, center_y=True)

            # Title text vertically centered in bar
            title_x = stt_x + stt_w + 10
            title_y = bar_y + bar_h // 2
            engine.draw_text(item.get("title", ""), engine.font_item, title_x, title_y,
                             title_color[0], title_color[1], title_color[2], center_y=True)
