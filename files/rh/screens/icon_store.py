# -*- coding: utf-8 -*-
"""Full-screen 3x2 Grid Emulator Icon Store (6 cards per page)."""

import os
import math
import threading
from .. import state
from ..paths import EMUS_DIR, SDCARD_PATH
from ..i18n import tr
from ..icon_manager import (
    load_icons_catalog,
    install_icon_pack,
    restore_stock_icons,
    has_stock_backup,
    get_icon_preview_path,
)
from .base import BaseScreen


class IconStoreScreen(BaseScreen):
    """Full-screen 3x2 Grid Emulator Icon Store."""

    COLS = 3
    ROWS = 2
    ITEMS_PER_PAGE = 6

    def __init__(self, engine=None):
        super().__init__(engine)
        self.raw_icons = []
        self.filtered_items = []
        self.selected_idx = 0
        self.filter_mode = "all"  # "all", "installed", "available"
        self.downloading_icon = False
        self.dl_icon_info = {}
        self.dl_pct = 0
        self.dl_msg = ""

    def on_enter(self, params=None):
        self.refresh_catalog()

    def refresh_catalog(self, force_reload=False):
        """Reloads catalog data instantly from cache and applies current filter."""
        self.raw_icons = load_icons_catalog(force_reload=force_reload) or []
        self.apply_filter()

    def apply_filter(self):
        """Applies filter mode ('all', 'installed', 'available') to items list."""
        self.filtered_items = []

        for it in self.raw_icons:
            is_active = it.get("is_active", False)
            if self.filter_mode == "installed" and not is_active:
                continue
            if self.filter_mode == "available" and is_active:
                continue

            lbl = tr("icon_active_badge") if is_active else tr("icon_not_installed_badge")
            item = dict(it)
            item["type"] = "icon_pack"
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

        mode_str = tr("icon_filter_all")
        if self.filter_mode == "installed":
            mode_str = tr("icon_filter_installed")
        elif self.filter_mode == "available":
            mode_str = tr("icon_filter_available")

        cur_info = ""
        if 0 <= self.selected_idx < total_items:
            it = self.filtered_items[self.selected_idx]
            name_str = it.get("name", it.get("folder", ""))
            size_str = f" • {it.get('size_str')}" if it.get("size_str") else ""
            cur_info = f" • #{self.selected_idx + 1} {name_str}{size_str}"

        return f"{tr('icon_store_title')}{cur_info} • [{mode_str}] • {cur_page}/{total_pages}"

    def get_footer_actions(self):
        actions = []
        if self.filtered_items and 0 <= self.selected_idx < len(self.filtered_items):
            item = self.filtered_items[self.selected_idx]
            if item.get("is_active"):
                actions.append(("A", tr("icon_btn_apply"), (0, 210, 255), (220, 225, 235), True))
            else:
                actions.append(("A", tr("icon_btn_apply"), (0, 230, 150), (220, 225, 235), True))

        if has_stock_backup():
            actions.append(("X", tr("icon_btn_restore_stock"), (255, 140, 0), (220, 225, 235), True))

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

        # Restore stock icons with X
        if btn_x and not self.downloading_icon:
            if has_stock_backup():
                self.downloading_icon = True
                self.dl_pct = 10
                self.dl_msg = "Đang khôi phục icon gốc..." if state.current_lang == "VI" else "Restoring stock icons..."

                def _bg_restore():
                    def _on_prog(pct, msg):
                        self.dl_pct = pct
                        self.dl_msg = msg

                    ok, msg = restore_stock_icons(on_progress=_on_prog)
                    self.downloading_icon = False
                    if self.engine:
                        self.engine.toast(msg, text_color=(0, 255, 160) if ok else (255, 100, 100))
                    self.refresh_catalog(force_reload=True)

                threading.Thread(target=_bg_restore, daemon=True).start()
                return True
            else:
                self.engine.toast("Chưa có bản sao lưu gốc!" if state.current_lang == "VI" else "No stock backup yet!")
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

        # 2D Grid Navigation in 3x2 Matrix
        page = self.selected_idx // self.ITEMS_PER_PAGE
        slot_in_page = self.selected_idx % self.ITEMS_PER_PAGE
        col = slot_in_page % self.COLS
        row = slot_in_page // self.COLS

        if btn_left:
            if col > 0:
                self.selected_idx -= 1
            else:
                # Wrap to previous row or previous page
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                else:
                    self.selected_idx = num_items - 1
            return True

        elif btn_right:
            if col < self.COLS - 1 and self.selected_idx + 1 < num_items:
                self.selected_idx += 1
            else:
                # Wrap to next row or next page
                if self.selected_idx < num_items - 1:
                    self.selected_idx += 1
                else:
                    self.selected_idx = 0
            return True

        elif btn_up:
            if row == 1:
                self.selected_idx -= self.COLS
            else:
                # Row 0: jump up to previous page same column
                if page > 0:
                    target = (page - 1) * self.ITEMS_PER_PAGE + (self.ROWS - 1) * self.COLS + col
                    self.selected_idx = min(num_items - 1, target)
                else:
                    # Wrap around to bottom of catalog
                    total_pages = max(1, math.ceil(num_items / self.ITEMS_PER_PAGE))
                    last_page = total_pages - 1
                    target = min(num_items - 1, last_page * self.ITEMS_PER_PAGE + (self.ROWS - 1) * self.COLS + col)
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

        # Download / Apply with A
        if btn_a and 0 <= self.selected_idx < num_items and not self.downloading_icon:
            item = self.filtered_items[self.selected_idx]
            self.downloading_icon = True
            self.dl_icon_info = dict(item)
            self.dl_pct = 5
            self.dl_msg = tr("icon_installing")

            def _bg_install():
                def _on_prog(pct, msg):
                    self.dl_pct = pct
                    self.dl_msg = msg

                ok, msg = install_icon_pack(item, on_progress=_on_prog)
                self.downloading_icon = False
                if self.engine:
                    self.engine.toast(msg, text_color=(0, 255, 160) if ok else (255, 100, 100))
                self.refresh_catalog(force_reload=True)

            threading.Thread(target=_bg_install, daemon=True).start()
            return True

        return False

    def render(self, engine):
        """Renders the full-screen 3x2 Grid UI (pure thumbnail gallery with corner badge)."""
        total_items = len(self.filtered_items)
        if total_items == 0:
            engine.draw_text(
                "Không tìm thấy bộ icon phù hợp!" if state.current_lang == "VI" else "No matching icon packs found!",
                engine.font_item,
                state.SCREEN_W // 2,
                state.SCREEN_H // 2,
                140, 160, 190,
                center_x=True, center_y=True
            )
            return

        page = self.selected_idx // self.ITEMS_PER_PAGE
        start_idx = page * self.ITEMS_PER_PAGE
        page_items = self.filtered_items[start_idx : start_idx + self.ITEMS_PER_PAGE]

        margin_x = 24
        start_y = 66
        gap_x = 16
        gap_y = 14

        total_grid_w = state.SCREEN_W - (margin_x * 2)  # 1024 - 48 = 976
        card_w = (total_grid_w - (self.COLS - 1) * gap_x) // self.COLS  # ~314px
        card_h = 312  # 312 * 2 + 14 = 638px

        for slot_idx, item in enumerate(page_items):
            actual_idx = start_idx + slot_idx
            is_sel = (actual_idx == self.selected_idx)
            is_active = item.get("is_active", False)

            col = slot_idx % self.COLS
            row = slot_idx // self.COLS

            card_x = margin_x + col * (card_w + gap_x)
            card_y = start_y + row * (card_h + gap_y)

            # 1. Card Container & Border
            if is_sel:
                engine.fill_rect(card_x, card_y, card_w, card_h, 24, 40, 68, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(card_x + 3, card_y + 3, card_w - 6, 3, 0, 246, 246, 255)
            else:
                engine.fill_rect(card_x, card_y, card_w, card_h, 16, 22, 36, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 36, 50, 78, 255, thickness=1)

            # 2. Thumbnail Image Area
            img_x = card_x + 4
            img_y = card_y + 4
            img_w = card_w - 8
            img_h = card_h - 52

            engine.fill_rect(img_x, img_y, img_w, img_h, 10, 14, 22, 255)

            prev_path = item.get("preview_path")
            if prev_path and os.path.exists(prev_path):
                engine.draw_proportional_boxart(prev_path, img_x, img_y, img_w, img_h)
            else:
                engine.draw_text("ICON PACK", engine.font_badge,
                                 img_x + img_w // 2, img_y + img_h // 2 - 10,
                                 90, 115, 150, center_x=True, center_y=True)
                engine.draw_text(item.get("folder", ""), engine.font_badge,
                                 img_x + img_w // 2, img_y + img_h // 2 + 15,
                                 70, 90, 120, center_x=True, center_y=True)

            # 3. Status Badge Top-Right
            badge_text = tr("icon_active_badge") if is_active else tr("icon_not_installed_badge")
            bg_r, bg_g, bg_b = (0, 160, 90) if is_active else (45, 60, 90)
            fg_r, fg_g, fg_b = (255, 255, 255) if is_active else (180, 205, 240)

            bw = engine.measure_text(badge_text, engine.font_badge) + 14
            bh = 22
            bx = img_x + img_w - bw - 6
            by = img_y + 6
            engine.fill_rect(bx, by, bw, bh, bg_r, bg_g, bg_b, 220)
            engine.draw_rect(bx, by, bw, bh, 255, 255, 255, 60, thickness=1)
            engine.draw_text(badge_text, engine.font_badge, bx + bw // 2, by + bh // 2, fg_r, fg_g, fg_b, center_x=True, center_y=True)

            # 4. Meta Badge Top-Left (Icon count or size)
            meta_txt = item.get("size_str", "")
            if meta_txt:
                mbw = engine.measure_text(meta_txt, engine.font_badge) + 10
                mbh = 20
                mbx = img_x + 6
                mby = img_y + 6
                engine.fill_rect(mbx, mby, mbw, mbh, 15, 20, 30, 200)
                engine.draw_rect(mbx, mby, mbw, mbh, 255, 255, 255, 40, thickness=1)
                engine.draw_text(meta_txt, engine.font_badge, mbx + mbw // 2, mby + mbh // 2, 200, 215, 235, center_x=True, center_y=True)

            # 5. Bottom Card Footer Bar (Title & Info)
            meta_h = 56
            meta_y = card_y + card_h - meta_h
            engine.fill_rect(card_x + 4, meta_y, card_w - 8, meta_h - 4, 22, 30, 48, 255)
            engine.draw_line(card_x + 4, meta_y, card_x + card_w - 4, meta_y, 42, 56, 88, 255)

            raw_title = item.get("name", item.get("folder", "Icon Pack"))
            max_title_w = card_w - 28
            title_str = raw_title
            if engine.measure_text(title_str, engine.font_item) > max_title_w:
                while title_str and engine.measure_text(title_str + "...", engine.font_item) > max_title_w:
                    title_str = title_str[:-1]
                title_str = title_str.rstrip() + "..."

            sub_info = f"{item.get('author', 'Burst')} • {item.get('version', '1.0')}"
            title_color = (255, 255, 255) if is_sel else (210, 220, 235)
            sub_color = (0, 240, 240) if is_sel else (130, 150, 180)

            # Draw 2 lines with comfortable vertical spacing
            engine.draw_text(
                title_str,
                engine.font_item,
                card_x + 12,
                meta_y + 8,
                *title_color
            )

            engine.draw_text(
                sub_info,
                engine.font_badge,
                card_x + 12,
                meta_y + 32,
                *sub_color
            )

        # ----------------------------------------------------------------------
        # 6. Global Downloading / Progress Overlay Modal (Spacious & Clean)
        # ----------------------------------------------------------------------
        if self.downloading_icon:
            overlay_w = 780
            overlay_h = 240
            ox = (state.SCREEN_W - overlay_w) // 2
            oy = (state.SCREEN_H - overlay_h) // 2

            # Background dimming
            engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 200)

            # Dialog container
            engine.fill_rect(ox, oy, overlay_w, overlay_h, 18, 26, 44, 255)
            engine.draw_rect(ox, oy, overlay_w, overlay_h, 0, 230, 255, 255, thickness=3)

            # 1. Header
            header_txt = "ĐANG CÀI ĐẶT BỘ ICON" if state.current_lang == "VI" else "INSTALLING ICON PACK"
            engine.draw_text(header_txt, engine.font_title, ox + overlay_w // 2, oy + 32, 0, 230, 255, center_x=True)

            # 2. Icon Pack Name
            name = self.dl_icon_info.get("name", "Icon Pack")
            if engine.measure_text(name, engine.font_item) > overlay_w - 60:
                while name and engine.measure_text(name + "...", engine.font_item) > overlay_w - 60:
                    name = name[:-1]
                name = name.rstrip() + "..."
            engine.draw_text(name, engine.font_item, ox + overlay_w // 2, oy + 76, 255, 255, 255, center_x=True)

            # 3. Status Message
            msg = self.dl_msg or ("Đang xử lý..." if state.current_lang == "VI" else "Processing...")
            engine.draw_text(msg, engine.font_sub, ox + overlay_w // 2, oy + 120, 150, 210, 255, center_x=True)

            # 4. Progress Bar
            pb_w = overlay_w - 80
            pb_h = 24
            pbx = ox + 40
            pby = oy + 165
            engine.fill_rect(pbx, pby, pb_w, pb_h, 28, 38, 60, 255)
            engine.draw_rect(pbx, pby, pb_w, pb_h, 70, 95, 135, 255, thickness=1)

            fill_w = int(pb_w * (max(0, min(100, self.dl_pct)) / 100.0))
            if fill_w > 0:
                engine.fill_rect(pbx + 1, pby + 1, fill_w - 2, pb_h - 2, 0, 220, 140, 255)

            pct_str = f"{int(self.dl_pct)}%"
            engine.draw_text(pct_str, engine.font_badge, ox + overlay_w // 2, pby + pb_h // 2, 255, 255, 255, center_x=True, center_y=True)
