# -*- coding: utf-8 -*-
"""Theme Store Screen: Full-screen 3x2 Grid UI, Live Previews, and On-Demand Download."""

import os
import math
from .. import state
from ..paths import THEMES_DIR, SDCARD_PATH
from ..i18n import tr
from ..theme_manager import (
    load_themes_catalog,
    install_theme,
    uninstall_theme,
    get_theme_preview_path,
)
from .base import BaseScreen


class ThemeStoreScreen(BaseScreen):
    """Full-screen 3x2 Grid Theme Store (6 cards per page)."""

    COLS = 3
    ROWS = 2
    ITEMS_PER_PAGE = 6

    def __init__(self, engine=None):
        super().__init__(engine)
        self.raw_themes = []
        self.filtered_items = []
        self.selected_idx = 0
        self.filter_mode = "all"  # "all", "installed", "available"

    def on_enter(self, params=None):
        self.refresh_catalog()

    def refresh_catalog(self, force_reload=False):
        """Reloads catalog data instantly from cache and applies current filter."""
        self.raw_themes = load_themes_catalog(force_reload=force_reload) or []
        self.apply_filter()

    def apply_filter(self):
        """Applies filter mode ('all', 'installed', 'available') to items list."""
        self.filtered_items = []

        for t in self.raw_themes:
            is_inst = t.get("is_installed", False)
            if self.filter_mode == "installed" and not is_inst:
                continue
            if self.filter_mode == "available" and is_inst:
                continue

            lbl = tr("theme_installed_badge") if is_inst else tr("theme_not_installed_badge")
            item = dict(t)
            item["type"] = "theme"
            item["label"] = lbl
            self.filtered_items.append(item)

        # Number items nicely (1 to N)
        for idx, it in enumerate(self.filtered_items):
            it["display_title"] = f"{idx + 1}. {it.get('name', it.get('folder', ''))}"

        if self.selected_idx >= len(self.filtered_items):
            self.selected_idx = max(0, len(self.filtered_items) - 1)

    def get_header_title(self):
        total_items = len(self.filtered_items)
        cur_page = (self.selected_idx // self.ITEMS_PER_PAGE) + 1 if total_items > 0 else 1
        total_pages = max(1, math.ceil(total_items / self.ITEMS_PER_PAGE)) if total_items > 0 else 1

        mode_str = tr("theme_filter_all")
        if self.filter_mode == "installed":
            mode_str = tr("theme_filter_installed")
        elif self.filter_mode == "available":
            mode_str = tr("theme_filter_available")

        return f"{tr('theme_store_title')} • [{mode_str}] • {cur_page}/{total_pages} ({total_items})"

    def get_footer_actions(self):
        if not self.filtered_items or self.selected_idx < 0 or self.selected_idx >= len(self.filtered_items):
            return [("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False)]

        item = self.filtered_items[self.selected_idx]
        actions = []

        if item.get("is_installed"):
            actions.append(("A", tr("theme_btn_reinstall"), (0, 210, 255), (220, 225, 235), True))
            actions.append(("X", tr("theme_btn_uninstall"), (255, 75, 75), (220, 225, 235), True))
        else:
            actions.append(("A", tr("theme_btn_install"), (0, 230, 150), (220, 225, 235), True))

        actions.append(("Y", tr("theme_btn_filter"), (0, 230, 255), (220, 225, 235), False))
        actions.append(("L1/R1", "Trang" if state.current_lang == "VI" else "Page", (70, 95, 140), (220, 225, 235), False))
        actions.append(("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False))
        return actions

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_y = inputs.get("btn_y")
        btn_l1 = inputs.get("btn_l1")
        btn_r1 = inputs.get("btn_r1")
        btn_l2 = inputs.get("btn_l2")
        btn_r2 = inputs.get("btn_r2")

        if btn_b:
            self.engine.pop_screen()
            return True

        # Toggle Filter Mode with Y
        if btn_y:
            modes = ["all", "installed", "available"]
            curr_idx = modes.index(self.filter_mode) if self.filter_mode in modes else 0
            self.filter_mode = modes[(curr_idx + 1) % len(modes)]
            self.selected_idx = 0
            self.apply_filter()
            return True

        num_items = len(self.filtered_items)
        if num_items == 0:
            return False

        # Quick Page Switch with Shoulder Buttons (L1/R1, L2/R2)
        if btn_l1 or btn_l2:
            self.selected_idx = max(0, self.selected_idx - self.ITEMS_PER_PAGE)
            return True
        elif btn_r1 or btn_r2:
            self.selected_idx = min(num_items - 1, self.selected_idx + self.ITEMS_PER_PAGE)
            return True

        # 3x2 Grid D-Pad Navigation
        page_slot = self.selected_idx % self.ITEMS_PER_PAGE
        col = page_slot % self.COLS
        row = page_slot // self.COLS

        if btn_left:
            if col > 0:
                self.selected_idx -= 1
            else:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                else:
                    self.selected_idx = num_items - 1
            return True

        elif btn_right:
            if self.selected_idx < num_items - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
            return True

        elif btn_up:
            if row == 1:
                self.selected_idx -= self.COLS
            else:
                # Row 0: jump up to previous page same column if exists
                if self.selected_idx >= self.ITEMS_PER_PAGE:
                    self.selected_idx -= self.COLS
                elif self.selected_idx >= self.COLS:
                    self.selected_idx -= self.COLS
                else:
                    # Wrap around to bottom
                    last_page_base = ((num_items - 1) // self.ITEMS_PER_PAGE) * self.ITEMS_PER_PAGE
                    target = min(num_items - 1, last_page_base + 3 + col)
                    if target >= num_items:
                        target = min(num_items - 1, last_page_base + col)
                    self.selected_idx = target
            return True

        elif btn_down:
            if row == 0:
                if self.selected_idx + self.COLS < num_items:
                    self.selected_idx += self.COLS
                else:
                    self.selected_idx = num_items - 1
            else:
                # Row 1: jump down to next page same column
                if self.selected_idx + self.COLS < num_items:
                    self.selected_idx += self.COLS
                elif self.selected_idx < num_items - 1:
                    self.selected_idx = num_items - 1
                else:
                    # Wrap around to top
                    self.selected_idx = min(num_items - 1, col)
            return True

        # Uninstall Theme with X
        if btn_x and 0 <= self.selected_idx < num_items:
            item = self.filtered_items[self.selected_idx]
            if item.get("is_installed"):
                ok, msg = uninstall_theme(item.get("folder", ""))
                self.engine.toast(msg)
                self.refresh_catalog(force_reload=True)
                return True

        # Download / Install with A
        if btn_a and 0 <= self.selected_idx < num_items:
            item = self.filtered_items[self.selected_idx]
            self.engine.toast(tr("theme_installing"))
            ok, msg = install_theme(item)
            self.engine.toast(msg)
            self.refresh_catalog(force_reload=True)
            return True

        return False

    def render(self, engine):
        """Renders the full-screen 3x2 Grid UI."""
        total_items = len(self.filtered_items)
        if total_items == 0:
            engine.draw_text(
                "Không tìm thấy theme phù hợp!" if state.current_lang == "VI" else "No matching themes found!",
                engine.font_item,
                state.SCREEN_W // 2,
                state.SCREEN_H // 2,
                140, 160, 190,
                center_x=True, center_y=True
            )
            return

        # ----------------------------------------------------------------------
        # 3x2 Grid Layout Calculations
        # ----------------------------------------------------------------------
        page = self.selected_idx // self.ITEMS_PER_PAGE
        start_idx = page * self.ITEMS_PER_PAGE
        page_items = self.filtered_items[start_idx : start_idx + self.ITEMS_PER_PAGE]

        margin_x = 24
        start_y = 66
        gap_x = 16
        gap_y = 14

        total_grid_w = state.SCREEN_W - (margin_x * 2)  # 1024 - 48 = 976
        card_w = (total_grid_w - (self.COLS - 1) * gap_x) // self.COLS  # ~314px
        card_h = 308  # Height: 2 rows fit in 630px

        for slot_idx, item in enumerate(page_items):
            actual_idx = start_idx + slot_idx
            is_sel = (actual_idx == self.selected_idx)
            is_inst = item.get("is_installed", False)

            col = slot_idx % self.COLS
            row = slot_idx // self.COLS

            card_x = margin_x + col * (card_w + gap_x)
            card_y = start_y + row * (card_h + gap_y)

            # ------------------------------------------------------------------
            # 1. Card Container & Borders
            # ------------------------------------------------------------------
            if is_sel:
                # Active Selection with Steam Cyan border & glow
                engine.fill_rect(card_x, card_y, card_w, card_h, 26, 42, 70, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(card_x + 3, card_y + 3, card_w - 6, 3, 0, 246, 246, 255)
            else:
                # Idle Card
                engine.fill_rect(card_x, card_y, card_w, card_h, 18, 25, 40, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 38, 52, 80, 255, thickness=1)

            # ------------------------------------------------------------------
            # 2. Preview Thumbnail Box
            # ------------------------------------------------------------------
            img_x = card_x + 6
            img_y = card_y + 6
            img_w = card_w - 12
            img_h = 210

            engine.fill_rect(img_x, img_y, img_w, img_h, 10, 14, 22, 255)
            engine.draw_rect(img_x, img_y, img_w, img_h, 30, 42, 65, 255, thickness=1)

            prev_path = item.get("preview_path")
            if prev_path and os.path.exists(prev_path):
                engine.draw_proportional_boxart(prev_path, img_x + 2, img_y + 2, img_w - 4, img_h - 4)
            else:
                engine.draw_text("THEME PREVIEW", engine.font_badge,
                                 img_x + img_w // 2, img_y + img_h // 2 - 10,
                                 90, 115, 150, center_x=True, center_y=True)
                engine.draw_text(item.get("folder", ""), engine.font_badge,
                                 img_x + img_w // 2, img_y + img_h // 2 + 15,
                                 70, 90, 120, center_x=True, center_y=True)

            # ------------------------------------------------------------------
            # 3. Card Bottom Info (Title & Badges)
            # ------------------------------------------------------------------
            title_y = card_y + 230
            title_str = item.get("display_title", item.get("name", ""))
            if len(title_str) > 23:
                title_str = title_str[:21] + ".."

            if is_sel:
                tr_c, tg_c, tb_c = (255, 255, 255)
            else:
                tr_c, tg_c, tb_c = (205, 218, 235)

            engine.draw_text(title_str, engine.font_item, card_x + 10, title_y, tr_c, tg_c, tb_c, center_y=True)

            # Badge & Size info row
            badge_y = card_y + 266
            badge_h = 30
            badge_w = 95
            badge_x = card_x + 10

            if is_inst:
                b_bg = (15, 45, 30)
                b_border = (0, 180, 100)
                b_text = (0, 230, 150)
                b_label = tr("theme_installed_badge")
            else:
                b_bg = (24, 38, 62)
                b_border = (50, 80, 130)
                b_text = (0, 230, 255)
                b_label = tr("theme_not_installed_badge")

            engine.fill_rect(badge_x, badge_y, badge_w, badge_h, b_bg[0], b_bg[1], b_bg[2], 255)
            engine.draw_rect(badge_x, badge_y, badge_w, badge_h, b_border[0], b_border[1], b_border[2], 255, thickness=1)
            engine.draw_text(b_label, engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2,
                             b_text[0], b_text[1], b_text[2], center_x=True, center_y=True)

            # Extra info (Size) on the right side of the badge
            size_str = item.get("size_str", "")
            if size_str:
                engine.draw_text(size_str, engine.font_badge, card_x + card_w - 12, badge_y + badge_h // 2,
                                 140, 160, 190, right_align=True, center_y=True)


