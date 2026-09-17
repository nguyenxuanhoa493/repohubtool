# -*- coding: utf-8 -*-
"""Theme Store Screen: Side-by-side Theme Catalog, Live Preview, and Immutable Stock Backup/Restore."""

import os
from .. import state
from ..paths import THEMES_DIR, THEME_BACKUP_DIR, SDCARD_PATH
from ..i18n import tr
from ..theme_manager import (
    load_themes_catalog,
    install_theme,
    uninstall_theme,
    restore_default_theme,
    get_theme_preview_path,
    ensure_default_theme_backup,
)
from .base import BaseScreen


class ThemeStoreScreen(BaseScreen):
    """Side-by-side Theme Store screen: Left is Catalog list, Right is Live Preview."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.raw_themes = []
        self.filtered_items = []
        self.selected_idx = 0
        self.scroll_top = 0
        self.filter_mode = "all"  # "all", "installed", "available"

        # Current live preview state
        self.preview_path = None
        self.preview_title = ""
        self.preview_subtitle = ""
        self.preview_badge = ""

    def on_enter(self, params=None):
        ensure_default_theme_backup()
        self.refresh_catalog()

    def refresh_catalog(self):
        """Reloads catalog data and applies current filter."""
        self.raw_themes = load_themes_catalog() or []
        self.apply_filter()

    def apply_filter(self):
        """Applies filter mode ('all', 'installed', 'available') to items list."""
        self.filtered_items = []

        # 1. Special immutable restore action item is always on top
        self.filtered_items.append({
            "id": "restore_stock",
            "type": "restore",
            "title": tr("theme_restore_stock_item"),
            "display_title": f"⭐ {tr('theme_restore_stock_item')}",
            "label": tr("theme_btn_restore"),
            "is_restore": True,
            "folder": "stock_backup"
        })

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

        # Re-index display titles
        num = 1
        for it in self.filtered_items:
            if it.get("type") == "theme":
                it["display_title"] = f"{num}. {it.get('name', it.get('folder', ''))}"
                num += 1

        if self.selected_idx >= len(self.filtered_items):
            self.selected_idx = max(0, len(self.filtered_items) - 1)
        self.update_current_preview()

    def update_current_preview(self):
        """Updates the right-hand preview panel based on cursor selection."""
        if not self.filtered_items or self.selected_idx < 0 or self.selected_idx >= len(self.filtered_items):
            self.preview_path = None
            self.preview_title = ""
            self.preview_subtitle = ""
            self.preview_badge = ""
            return

        item = self.filtered_items[self.selected_idx]
        if item.get("type") == "restore":
            self.preview_path = None
            self.preview_title = tr("theme_restore_stock_item")
            self.preview_subtitle = "Khôi phục theme mặc định xuất xưởng ban đầu" if state.current_lang == "VI" else "Restore original factory stock theme"
            self.preview_badge = "STOCK RESTORE"
        elif item.get("type") == "theme":
            folder = item.get("folder", "")
            self.preview_path = get_theme_preview_path(folder)
            self.preview_title = item.get("name", folder)
            size_str = item.get("size_str", "")
            font_str = f"Font: {item.get('font', 'Default')}" if item.get("font") else ""
            parts = [p for p in [folder, font_str, size_str] if p]
            self.preview_subtitle = " • ".join(parts)
            self.preview_badge = tr("theme_installed_badge") if item.get("is_installed") else tr("theme_not_installed_badge")

    def get_header_title(self):
        total_themes = len([x for x in self.raw_themes])
        installed_count = len([x for x in self.raw_themes if x.get("is_installed")])
        mode_str = tr("theme_filter_all")
        if self.filter_mode == "installed":
            mode_str = tr("theme_filter_installed")
        elif self.filter_mode == "available":
            mode_str = tr("theme_filter_available")
        return f"{tr('theme_store_title')} [{mode_str}: {installed_count}/{total_themes}]"

    def get_footer_actions(self):
        if not self.filtered_items or self.selected_idx < 0 or self.selected_idx >= len(self.filtered_items):
            return [("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False)]

        item = self.filtered_items[self.selected_idx]
        if item.get("type") == "restore":
            return [
                ("A", tr("theme_btn_restore"), (255, 200, 0), (220, 225, 235), True),
                ("Y", f"{tr('theme_btn_filter')}: {self.filter_mode.upper()}", (0, 230, 255), (220, 225, 235), False),
                ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
            ]

        actions = []
        if item.get("is_installed"):
            actions.append(("A", tr("theme_btn_install"), (0, 230, 150), (220, 225, 235), True))
            actions.append(("X", tr("theme_btn_uninstall"), (255, 75, 75), (220, 225, 235), True))
        else:
            actions.append(("A", tr("theme_btn_install"), (0, 230, 150), (220, 225, 235), True))

        actions.append(("Y", f"{tr('theme_btn_filter')}", (0, 230, 255), (220, 225, 235), False))
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

        if btn_b:
            self.engine.pop_screen()
            return True

        # Toggle Filter Mode with Y
        if btn_y:
            modes = ["all", "installed", "available"]
            curr_idx = modes.index(self.filter_mode) if self.filter_mode in modes else 0
            self.filter_mode = modes[(curr_idx + 1) % len(modes)]
            self.selected_idx = 0
            self.scroll_top = 0
            self.apply_filter()
            return True

        num_items = len(self.filtered_items)
        if num_items == 0:
            return False
        max_visible = 6

        # Fast page scroll with Left/Right
        if btn_left:
            self.selected_idx = max(0, self.selected_idx - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            self.update_current_preview()
            return True
        elif btn_right:
            self.selected_idx = min(num_items - 1, self.selected_idx + max_visible)
            if self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            self.update_current_preview()
            return True

        if btn_up:
            if self.selected_idx > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = num_items - 1
                self.scroll_top = max(0, num_items - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            self.update_current_preview()
            return True
        elif btn_down:
            if self.selected_idx < num_items - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
                self.scroll_top = 0
            if self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            self.update_current_preview()
            return True

        # Uninstall Theme with X
        if btn_x and 0 <= self.selected_idx < num_items:
            item = self.filtered_items[self.selected_idx]
            if item.get("type") == "theme" and item.get("is_installed"):
                ok, msg = uninstall_theme(item.get("folder", ""))
                self.engine.toast(msg)
                self.refresh_catalog()
                return True

        # Install or Restore with A
        if btn_a and 0 <= self.selected_idx < num_items:
            item = self.filtered_items[self.selected_idx]
            if item.get("type") == "restore":
                ok, msg = restore_default_theme()
                self.engine.toast(msg)
                self.refresh_catalog()
                return True
            elif item.get("type") == "theme":
                self.engine.toast(tr("theme_installing"))
                ok, msg = install_theme(item)
                self.engine.toast(msg)
                self.refresh_catalog()
                return True

        return False

    def render(self, engine):
        # ----------------------------------------------------------------------
        # Layout Geometry: Side-by-Side 2 Columns (Left List, Right Preview)
        # ----------------------------------------------------------------------
        left_x = 30
        left_w = 480
        start_y = 64 + 14
        card_h = 74
        gap = 8
        max_visible = 6

        right_x = left_x + left_w + 24  # 534
        right_w = state.SCREEN_W - 30 - right_x  # 460
        right_y = start_y
        right_h = card_h * max_visible + gap * (max_visible - 1)  # 484

        # ----------------------------------------------------------------------
        # 1. Render Left Column (Catalog List)
        # ----------------------------------------------------------------------
        num_items = len(self.filtered_items)
        if num_items == 0:
            engine.draw_text("Không tìm thấy theme phù hợp!" if state.current_lang == "VI" else "No matching themes found!",
                             engine.font_item, left_x + left_w // 2, start_y + 120, 140, 160, 190, center_x=True, center_y=True)
        else:
            max_scroll = max(0, num_items - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            elif self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            self.scroll_top = max(0, min(max_scroll, self.scroll_top))

            vis_items = self.filtered_items[self.scroll_top : self.scroll_top + max_visible]

            for i, item in enumerate(vis_items):
                actual_idx = self.scroll_top + i
                cy = start_y + i * (card_h + gap)
                is_sel = (actual_idx == self.selected_idx)
                is_restore = item.get("is_restore", False)
                is_inst = item.get("is_installed", False)

                if is_sel:
                    engine.fill_rect(left_x, cy, left_w, card_h, 28, 44, 75, 255)
                    engine.draw_rect(left_x, cy, left_w, card_h, 0, 246, 246, 255, thickness=3)
                    engine.fill_rect(left_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                    text_r, text_g, text_b = 255, 255, 255
                else:
                    if is_restore:
                        engine.fill_rect(left_x, cy, left_w, card_h, 32, 28, 18, 255)
                        engine.draw_rect(left_x, cy, left_w, card_h, 180, 140, 40, 200, thickness=1)
                        text_r, text_g, text_b = 255, 215, 100
                    else:
                        engine.fill_rect(left_x, cy, left_w, card_h, 19, 26, 42, 255)
                        engine.draw_rect(left_x, cy, left_w, card_h, 40, 54, 85, 255, thickness=1)
                        text_r, text_g, text_b = 200, 210, 225

                title_str = item.get("display_title", item.get("name", ""))
                if len(title_str) > 27:
                    title_str = title_str[:25] + ".."
                engine.draw_text(title_str, engine.font_item, left_x + 24, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

                if item.get("label"):
                    badge_w = 100
                    badge_h = 38
                    badge_x = left_x + left_w - badge_w - 14
                    badge_y = cy + (card_h - badge_h) // 2

                    if is_restore:
                        badge_bg = (50, 40, 20)
                        badge_border = (180, 140, 40)
                        badge_text_col = (255, 200, 0)
                    elif is_inst:
                        badge_bg = (15, 45, 30)
                        badge_border = (0, 180, 100)
                        badge_text_col = (0, 230, 150)
                    else:
                        badge_bg = (30, 42, 68)
                        badge_border = (65, 90, 135)
                        badge_text_col = (0, 230, 255)

                    engine.fill_rect(badge_x, badge_y, badge_w, badge_h, badge_bg[0], badge_bg[1], badge_bg[2], 255)
                    engine.draw_rect(badge_x, badge_y, badge_w, badge_h, badge_border[0], badge_border[1], badge_border[2], 255, thickness=1)
                    engine.draw_text(item["label"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, badge_text_col[0], badge_text_col[1], badge_text_col[2], center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 2. Render Right Column: LIVE PREVIEW PANEL
        # ----------------------------------------------------------------------
        engine.fill_rect(right_x, right_y, right_w, right_h, 15, 20, 34, 255)
        engine.draw_rect(right_x, right_y, right_w, right_h, 45, 65, 105, 255, thickness=2)

        # Panel Header
        p_hdr_h = 38
        engine.fill_rect(right_x + 2, right_y + 2, right_w - 4, p_hdr_h, 22, 32, 54, 255)
        engine.fill_rect(right_x + 2, right_y + p_hdr_h + 1, right_w - 4, 2, 0, 246, 246, 255)
        engine.draw_text("XEM TRƯỚC (THEME PREVIEW)" if state.current_lang == "VI" else "THEME PREVIEW",
                         engine.font_badge, right_x + right_w // 2, right_y + p_hdr_h // 2 + 1,
                         0, 246, 246, center_x=True, center_y=True)

        # Image Drawing Area
        img_x = right_x + 16
        img_y = right_y + p_hdr_h + 12
        img_w = right_w - 32
        img_h = right_h - p_hdr_h - 68

        engine.fill_rect(img_x, img_y, img_w, img_h, 8, 12, 20, 255)
        engine.draw_rect(img_x, img_y, img_w, img_h, 35, 48, 75, 255, thickness=1)

        if self.preview_path and os.path.exists(self.preview_path):
            engine.draw_proportional_boxart(self.preview_path, img_x + 2, img_y + 2, img_w - 4, img_h - 4)
        else:
            if self.preview_badge == "STOCK RESTORE":
                engine.draw_text("⭐ KHÔI PHỤC THEME MẶC ĐỊNH GỐC" if state.current_lang == "VI" else "⭐ RESTORE DEFAULT FACTORY THEME",
                                 engine.font_item, img_x + img_w // 2, img_y + img_h // 2 - 15,
                                 255, 215, 100, center_x=True, center_y=True)
                engine.draw_text("Bấm [A] để khôi phục giao diện gốc xuất xưởng" if state.current_lang == "VI" else "Press [A] to restore factory stock UI",
                                 engine.font_badge, img_x + img_w // 2, img_y + img_h // 2 + 20,
                                 160, 180, 210, center_x=True, center_y=True)
            else:
                engine.draw_text("THEME CHƯA CÓ ẢNH PREVIEW" if state.current_lang == "VI" else "NO PREVIEW AVAILABLE",
                                 engine.font_item, img_x + img_w // 2, img_y + img_h // 2,
                                 120, 145, 180, center_x=True, center_y=True)

        # Info Bottom Bar
        info_y = right_y + right_h - 46
        info_h = 36
        engine.fill_rect(right_x + 16, info_y, right_w - 32, info_h, 20, 28, 46, 255)
        engine.draw_rect(right_x + 16, info_y, right_w - 32, info_h, 50, 70, 110, 255, thickness=1)

        disp_title = self.preview_title
        if len(disp_title) > 34:
            disp_title = disp_title[:32] + ".."
        engine.draw_text(disp_title or "...", engine.font_badge, right_x + 28, info_y + info_h // 2, 0, 230, 255, center_y=True)
