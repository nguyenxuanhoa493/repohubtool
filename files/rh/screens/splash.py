# -*- coding: utf-8 -*-
"""Boot Splash Manager with Side-by-Side Preset Library, Live Preview, and SD File Browser."""

import os
from .. import state
from ..paths import SDCARD_PATH, SPLASH_TEMP_PREVIEW, SPLASH_TEMP_BMP, SPLASH_BACKUP_FILE, SPLASH_SYS_FILE
from ..i18n import tr
from ..splash import (scan_splash_images, scan_directory_for_images,
                     apply_splash_update, restore_original_splash,
                     convert_and_fit_splash)
from .base import BaseScreen


class SplashScreen(BaseScreen):
    """Side-by-side Boot Splash screen: Left is Preset List / Browser, Right is Live Preview."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.view_mode = "list"  # "list" or "browser"
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0

        # File browser state
        self.browser_dir = SDCARD_PATH
        self.browser_items = []
        self.browser_idx = 0
        self.browser_scroll = 0

        # Current live preview state
        self.preview_path = None
        self.preview_title = ""
        self.preview_subtitle = ""

    def on_enter(self, params=None):
        self.show_list()

    def show_list(self):
        """Build preset library and default actions for left column."""
        self.view_mode = "list"
        self.selected_idx = 0
        self.scroll_top = 0
        self.items = [
            {
                "id": "browse",
                "type": "action",
                "title": tr("splash_browse_item"),
                "label": tr("view"),
                "is_browse": True
            },
            {
                "id": "restore",
                "type": "action",
                "title": tr("splash_restore_item"),
                "label": tr("view"),
                "is_restore": True
            }
        ]

        scanned = scan_splash_images() or []
        for s in scanned:
            self.items.append({
                "id": f"img_{s['path']}",
                "type": "image",
                "title": s["filename"],
                "path": s["path"],
                "size_str": s.get("size_str", ""),
                "dir": s.get("dir", ""),
                "label": s.get("size_str", "")
            })

        for idx, it in enumerate(self.items):
            it["display_title"] = f"{idx + 1}. {it['title']}"

        self.update_current_preview()

    def open_browser(self, dir_path=None):
        """Open SD card file browser on the left column."""
        if dir_path is None:
            dir_path = SDCARD_PATH
        self.view_mode = "browser"
        self.browser_dir = os.path.normpath(dir_path)
        self.browser_items = scan_directory_for_images(self.browser_dir) or []
        self.browser_idx = 0
        self.browser_scroll = 0
        for idx, it in enumerate(self.browser_items):
            it["display_title"] = f"{idx + 1}. {it['title']}"

        self.update_current_preview()

    def update_current_preview(self):
        """Update the right-hand preview panel based on current cursor selection."""
        if self.view_mode == "list":
            if not self.items or self.selected_idx < 0 or self.selected_idx >= len(self.items):
                self.preview_path = None
                self.preview_title = ""
                self.preview_subtitle = ""
                return

            item = self.items[self.selected_idx]
            if item.get("type") == "image":
                self.preview_path = item["path"]
                self.preview_title = item.get("title", "")
                self.preview_subtitle = f"{item.get('dir', '')} • {item.get('size_str', '')}"
            elif item.get("id") == "restore":
                if os.path.exists(SPLASH_BACKUP_FILE):
                    self.preview_path = SPLASH_BACKUP_FILE
                    self.preview_title = "Ảnh khởi động GỐC (Backup)" if state.current_lang == "VI" else "Original Splash (Backup)"
                    self.preview_subtitle = "TrimUI Default Bootlogo"
                elif os.path.exists(SPLASH_SYS_FILE):
                    self.preview_path = SPLASH_SYS_FILE
                    self.preview_title = "Ảnh khởi động hiện tại" if state.current_lang == "VI" else "Current Boot Splash"
                    self.preview_subtitle = "/etc/splash.png"
                else:
                    self.preview_path = None
                    self.preview_title = tr("splash_restore_item")
                    self.preview_subtitle = "TrimUI Default"
            elif item.get("id") == "browse":
                self.preview_title = tr("splash_browse_item")
                self.preview_subtitle = "Duyệt SD Card để chọn ảnh" if state.current_lang == "VI" else "Browse SD card to pick image"

        elif self.view_mode == "browser":
            if not self.browser_items or self.browser_idx < 0 or self.browser_idx >= len(self.browser_items):
                self.preview_path = None
                self.preview_title = ""
                self.preview_subtitle = ""
                return

            item = self.browser_items[self.browser_idx]
            if item.get("type") == "file":
                self.preview_path = item["path"]
                self.preview_title = item.get("filename", item.get("title", ""))
                self.preview_subtitle = f"Tệp ảnh • {item.get('size_str', '')}"
            elif item.get("id") == "fb_up":
                self.preview_title = tr("fb_up")
                self.preview_subtitle = "Lên thư mục cha" if state.current_lang == "VI" else "Go to parent folder"
            else:
                self.preview_title = item.get("title", "")
                self.preview_subtitle = "Thư mục" if state.current_lang == "VI" else "Directory"

    def get_header_title(self):
        if self.view_mode == "browser":
            return tr("fb_title")
        return tr("splash_title")

    def get_footer_actions(self):
        if self.view_mode == "browser":
            if self.browser_items and 0 <= self.browser_idx < len(self.browser_items):
                item = self.browser_items[self.browser_idx]
                if item.get("type") == "file":
                    return [
                        ("A", tr("splash_btn_apply"), (0, 230, 150), (220, 225, 235), True),
                        ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
                    ]
            return [
                ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
                ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
            ]

        # List mode
        if self.items and 0 <= self.selected_idx < len(self.items):
            item = self.items[self.selected_idx]
            if item.get("type") == "image":
                return [
                    ("A", tr("splash_btn_apply"), (0, 230, 150), (220, 225, 235), True),
                    ("Y", "Khôi phục gốc" if state.current_lang == "VI" else "Restore Default", (255, 200, 0), (220, 225, 235), True),
                    ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
                ]
            elif item.get("id") == "restore":
                return [
                    ("A", "Khôi phục gốc" if state.current_lang == "VI" else "Restore Default", (255, 200, 0), (220, 225, 235), True),
                    ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
                ]

        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
            ("Y", "Khôi phục gốc" if state.current_lang == "VI" else "Restore Default", (255, 200, 0), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def _apply_image(self, img_path):
        """Convert and apply selected image as boot splash with toast notification."""
        self.engine.toast(tr("splash_converting"))
        ok_conv = convert_and_fit_splash(img_path, SPLASH_TEMP_PREVIEW, state.SCREEN_W, state.SCREEN_H)
        if not ok_conv:
            self.engine.toast(tr("splash_err"))
            return False
        ok_apply, msg = apply_splash_update(SPLASH_TEMP_PREVIEW, SPLASH_TEMP_BMP)
        self.engine.toast(msg)
        return ok_apply

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_y = inputs.get("btn_y")

        # ----------------------------------------------------------------------
        # View Mode: FILE BROWSER
        # ----------------------------------------------------------------------
        if self.view_mode == "browser":
            if btn_b:
                norm_curr = os.path.normpath(self.browser_dir)
                norm_sd = os.path.normpath(SDCARD_PATH)
                if norm_curr != norm_sd and norm_curr != "/" and norm_curr != "":
                    parent_dir = os.path.dirname(norm_curr)
                    if not parent_dir:
                        parent_dir = SDCARD_PATH
                    self.open_browser(parent_dir)
                else:
                    self.show_list()
                return True

            num_items = len(self.browser_items)
            if num_items == 0:
                return False
            max_visible = 6

            if btn_up:
                if self.browser_idx > 0:
                    self.browser_idx -= 1
                else:
                    self.browser_idx = num_items - 1
                    self.browser_scroll = max(0, num_items - max_visible)
                if self.browser_idx < self.browser_scroll:
                    self.browser_scroll = self.browser_idx
                self.update_current_preview()
                return True
            elif btn_down:
                if self.browser_idx < num_items - 1:
                    self.browser_idx += 1
                else:
                    self.browser_idx = 0
                    self.browser_scroll = 0
                if self.browser_idx >= self.browser_scroll + max_visible:
                    self.browser_scroll = self.browser_idx - max_visible + 1
                self.update_current_preview()
                return True

            if btn_a and 0 <= self.browser_idx < len(self.browser_items):
                item = self.browser_items[self.browser_idx]
                if item.get("type") == "dir":
                    self.open_browser(item.get("path"))
                elif item.get("type") == "file":
                    self._apply_image(item.get("path"))
                    self.show_list()
                return True

            return False

        # ----------------------------------------------------------------------
        # View Mode: LIST (Side-by-Side Main Splash Manager)
        # ----------------------------------------------------------------------
        if self.view_mode == "list":
            if btn_b:
                self.engine.pop_screen()
                return True

            if btn_y:
                ok, msg = restore_original_splash()
                self.engine.toast(msg)
                self.update_current_preview()
                return True

            num_items = len(self.items)
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

            if btn_a and 0 <= self.selected_idx < len(self.items):
                item = self.items[self.selected_idx]
                if item.get("id") == "browse":
                    self.open_browser(SDCARD_PATH)
                elif item.get("id") == "restore":
                    ok, msg = restore_original_splash()
                    self.engine.toast(msg)
                    self.update_current_preview()
                elif item.get("type") == "image":
                    self._apply_image(item["path"])
                return True

        return False

    def render(self, engine):
        # ----------------------------------------------------------------------
        # Layout Geometry: Side-by-Side 2 Columns
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
        # 1. Render Left Column (List / Browser)
        # ----------------------------------------------------------------------
        if self.view_mode == "browser":
            # Sub-header banner for current directory
            sub_bar_h = 32
            engine.fill_rect(left_x, start_y, left_w, sub_bar_h, 20, 28, 46, 255)
            engine.draw_rect(left_x, start_y, left_w, sub_bar_h, 45, 60, 95, 255, thickness=1)
            dir_display = self.browser_dir if len(self.browser_dir) <= 38 else "..." + self.browser_dir[-35:]
            engine.draw_text(f"📁 {dir_display}", engine.font_badge, left_x + 14, start_y + sub_bar_h // 2, 0, 230, 255, center_y=True)

            b_start_y = start_y + sub_bar_h + 8
            b_card_h = 68
            b_gap = 6
            num_items = len(self.browser_items)

            if not self.browser_items:
                engine.draw_text(tr("fb_empty"), engine.font_item, left_x + left_w // 2, b_start_y + 120, 140, 160, 190, center_x=True, center_y=True)
            else:
                max_scroll = max(0, num_items - max_visible)
                if self.browser_idx < self.browser_scroll:
                    self.browser_scroll = self.browser_idx
                elif self.browser_idx >= self.browser_scroll + max_visible:
                    self.browser_scroll = self.browser_idx - max_visible + 1
                self.browser_scroll = max(0, min(max_scroll, self.browser_scroll))

                vis_items = self.browser_items[self.browser_scroll : self.browser_scroll + max_visible]

                for i, it in enumerate(vis_items):
                    actual_idx = self.browser_scroll + i
                    cy = b_start_y + i * (b_card_h + b_gap)
                    is_sel = (actual_idx == self.browser_idx)
                    is_dir = (it.get("type") == "dir")

                    if is_sel:
                        engine.fill_rect(left_x, cy, left_w, b_card_h, 28, 44, 75, 255)
                        engine.draw_rect(left_x, cy, left_w, b_card_h, 0, 246, 246, 255, thickness=3)
                        engine.fill_rect(left_x + 3, cy + 6, 8, b_card_h - 12, 0, 246, 246, 255)
                        text_r, text_g, text_b = 255, 255, 255
                    else:
                        if is_dir:
                            engine.fill_rect(left_x, cy, left_w, b_card_h, 22, 30, 48, 255)
                            engine.draw_rect(left_x, cy, left_w, b_card_h, 50, 70, 110, 255, thickness=1)
                            text_r, text_g, text_b = 220, 235, 255
                        else:
                            engine.fill_rect(left_x, cy, left_w, b_card_h, 19, 26, 42, 255)
                            engine.draw_rect(left_x, cy, left_w, b_card_h, 40, 54, 85, 255, thickness=1)
                            text_r, text_g, text_b = 200, 210, 225

                    title_str = it.get("display_title", it.get("title", ""))
                    if len(title_str) > 28:
                        title_str = title_str[:26] + ".."
                    engine.draw_text(title_str, engine.font_item, left_x + 24, cy + (b_card_h // 2), text_r, text_g, text_b, center_y=True)

                    if it.get("size_str"):
                        badge_w = 95
                        badge_h = 34
                        badge_x = left_x + left_w - badge_w - 14
                        badge_y = cy + (b_card_h - badge_h) // 2
                        engine.fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                        engine.draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                        engine.draw_text(it["size_str"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 230, 255, center_x=True, center_y=True)

        else:
            # Main Preset List Mode
            num_items = len(self.items)
            max_scroll = max(0, num_items - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            elif self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            self.scroll_top = max(0, min(max_scroll, self.scroll_top))

            vis_items = self.items[self.scroll_top : self.scroll_top + max_visible]

            for i, item in enumerate(vis_items):
                actual_idx = self.scroll_top + i
                cy = start_y + i * (card_h + gap)
                is_sel = (actual_idx == self.selected_idx)
                is_browse = item.get("is_browse", False)
                is_restore = item.get("is_restore", False)

                if is_sel:
                    engine.fill_rect(left_x, cy, left_w, card_h, 28, 44, 75, 255)
                    engine.draw_rect(left_x, cy, left_w, card_h, 0, 246, 246, 255, thickness=3)
                    engine.fill_rect(left_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                    text_r, text_g, text_b = 255, 255, 255
                else:
                    if is_browse:
                        engine.fill_rect(left_x, cy, left_w, card_h, 20, 32, 52, 255)
                        engine.draw_rect(left_x, cy, left_w, card_h, 0, 180, 220, 200, thickness=1)
                        text_r, text_g, text_b = 0, 230, 255
                    elif is_restore:
                        engine.fill_rect(left_x, cy, left_w, card_h, 28, 26, 38, 255)
                        engine.draw_rect(left_x, cy, left_w, card_h, 160, 130, 50, 180, thickness=1)
                        text_r, text_g, text_b = 255, 215, 110
                    else:
                        engine.fill_rect(left_x, cy, left_w, card_h, 19, 26, 42, 255)
                        engine.draw_rect(left_x, cy, left_w, card_h, 40, 54, 85, 255, thickness=1)
                        text_r, text_g, text_b = 200, 210, 225

                title_str = item.get("display_title", item.get("title", ""))
                if len(title_str) > 28:
                    title_str = title_str[:26] + ".."
                engine.draw_text(title_str, engine.font_item, left_x + 24, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

                if item.get("label"):
                    badge_w = 95
                    badge_h = 38
                    badge_x = left_x + left_w - badge_w - 14
                    badge_y = cy + (card_h - badge_h) // 2

                    badge_text_col = (0, 230, 255)
                    if is_restore:
                        badge_text_col = (255, 200, 0)
                    elif is_browse:
                        badge_text_col = (0, 246, 246)

                    engine.fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                    engine.draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                    engine.draw_text(item["label"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, badge_text_col[0], badge_text_col[1], badge_text_col[2], center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 2. Render Right Column: LIVE PREVIEW PANEL
        # ----------------------------------------------------------------------
        # Panel Background & Border
        engine.fill_rect(right_x, right_y, right_w, right_h, 15, 20, 34, 255)
        engine.draw_rect(right_x, right_y, right_w, right_h, 45, 65, 105, 255, thickness=2)

        # Panel Header
        p_hdr_h = 38
        engine.fill_rect(right_x + 2, right_y + 2, right_w - 4, p_hdr_h, 22, 32, 54, 255)
        engine.fill_rect(right_x + 2, right_y + p_hdr_h + 1, right_w - 4, 2, 0, 246, 246, 255)
        engine.draw_text("XEM TRƯỚC (LIVE PREVIEW)" if state.current_lang == "VI" else "LIVE PREVIEW",
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
            engine.draw_text("CHỌN ẢNH ĐỂ XEM TRƯỚC" if state.current_lang == "VI" else "SELECT IMAGE TO PREVIEW",
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
