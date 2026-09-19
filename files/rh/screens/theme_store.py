import os
import math
import threading
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
        self.downloading_theme = False
        self.dl_theme_info = {}
        self.dl_pct = 0
        self.dl_msg = ""

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

        cur_info = ""
        if 0 <= self.selected_idx < total_items:
            it = self.filtered_items[self.selected_idx]
            name_str = it.get("name", it.get("folder", ""))
            size_str = f" • {it.get('size_str')}" if it.get("size_str") else ""
            cur_info = f" • #{self.selected_idx + 1} {name_str}{size_str}"

        return f"{tr('theme_store_title')}{cur_info} • [{mode_str}] • {cur_page}/{total_pages}"

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
        if btn_x and 0 <= self.selected_idx < num_items and not self.downloading_theme:
            item = self.filtered_items[self.selected_idx]
            if item.get("is_installed"):
                ok, msg = uninstall_theme(item.get("folder", ""))
                self.engine.toast(msg)
                self.refresh_catalog(force_reload=True)
                return True

        # Download / Install with A
        if btn_a and 0 <= self.selected_idx < num_items and not self.downloading_theme:
            item = self.filtered_items[self.selected_idx]
            self.downloading_theme = True
            self.dl_theme_info = dict(item)
            self.dl_pct = 5
            self.dl_msg = tr("theme_installing")

            def _bg_install():
                def _on_prog(pct, msg):
                    self.dl_pct = pct
                    self.dl_msg = msg

                ok, msg = install_theme(item, on_progress=_on_prog)
                self.downloading_theme = False
                if self.engine:
                    self.engine.toast(msg, text_color=(0, 255, 160) if ok else (255, 100, 100))
                self.refresh_catalog(force_reload=True)

            threading.Thread(target=_bg_install, daemon=True).start()
            return True

        return False

    def render(self, engine):
        """Renders the full-screen 3x2 Grid UI (pure thumbnail gallery with corner icon)."""
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
        # 3x2 Grid Layout Calculations (Full screen cards)
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
        card_h = 312  # 312 * 2 + 14 = 638px (fits perfectly in 768px height)

        for slot_idx, item in enumerate(page_items):
            actual_idx = start_idx + slot_idx
            is_sel = (actual_idx == self.selected_idx)
            is_inst = item.get("is_installed", False)

            col = slot_idx % self.COLS
            row = slot_idx // self.COLS

            card_x = margin_x + col * (card_w + gap_x)
            card_y = start_y + row * (card_h + gap_y)

            # ------------------------------------------------------------------
            # 1. Card Container & Border
            # ------------------------------------------------------------------
            if is_sel:
                # Active Selection with Steam Cyan border & glow
                engine.fill_rect(card_x, card_y, card_w, card_h, 24, 40, 68, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(card_x + 3, card_y + 3, card_w - 6, 3, 0, 246, 246, 255)
            else:
                # Idle Card
                engine.fill_rect(card_x, card_y, card_w, card_h, 16, 22, 36, 255)
                engine.draw_rect(card_x, card_y, card_w, card_h, 36, 50, 78, 255, thickness=1)

            # ------------------------------------------------------------------
            # 2. Thumbnail Image Area (Upper Part of Card)
            # ------------------------------------------------------------------
            img_x = card_x + 4
            img_y = card_y + 4
            img_w = card_w - 8
            img_h = card_h - 52

            engine.fill_rect(img_x, img_y, img_w, img_h, 10, 14, 22, 255)

            prev_path = item.get("preview_path")
            if prev_path and os.path.exists(prev_path):
                engine.draw_proportional_boxart(prev_path, img_x, img_y, img_w, img_h)
            else:
                engine.draw_text("THEME PREVIEW", engine.font_badge,
                                 img_x + img_w // 2, img_y + img_h // 2 - 10,
                                 90, 115, 150, center_x=True, center_y=True)
                engine.draw_text(item.get("folder", ""), engine.font_badge,
                                 img_x + img_w // 2, img_y + img_h // 2 + 15,
                                 70, 90, 120, center_x=True, center_y=True)

            # ------------------------------------------------------------------
            # 3. Bottom Information Bar: STT + Theme Name + Status Icon
            # ------------------------------------------------------------------
            bar_x = card_x + 4
            bar_y = card_y + img_h + 4
            bar_w = card_w - 8
            bar_h = 44

            if is_sel:
                engine.fill_rect(bar_x, bar_y, bar_w, bar_h, 24, 38, 64, 255)
                engine.fill_rect(bar_x, bar_y, bar_w, 2, 0, 246, 246, 255)
            else:
                engine.fill_rect(bar_x, bar_y, bar_w, bar_h, 14, 18, 30, 255)
                engine.fill_rect(bar_x, bar_y, bar_w, 1, 35, 48, 72, 255)

            # STT Badge (#1, #2, ...)
            stt_str = f"#{actual_idx + 1}"
            stt_w = max(38, engine.measure_text(stt_str, engine.font_grid_title) + 12)
            stt_h = 28
            stt_x = bar_x + 6
            stt_y = bar_y + (bar_h - stt_h) // 2

            if is_sel:
                engine.fill_rect(stt_x, stt_y, stt_w, stt_h, 0, 210, 255, 255)
                engine.draw_text(stt_str, engine.font_grid_title, stt_x + stt_w // 2, stt_y + stt_h // 2, 0, 24, 48, center_x=True, center_y=True)
            else:
                engine.fill_rect(stt_x, stt_y, stt_w, stt_h, 24, 34, 52, 255)
                engine.draw_text(stt_str, engine.font_grid_title, stt_x + stt_w // 2, stt_y + stt_h // 2, 170, 195, 225, center_x=True, center_y=True)

            # Status Icon on Right (✓ or ☁)
            icon_w = 32
            icon_h = 28
            icon_x = bar_x + bar_w - icon_w - 6
            icon_y = bar_y + (bar_h - icon_h) // 2

            if is_inst:
                engine.fill_rect(icon_x, icon_y, icon_w, icon_h, 12, 45, 26, 225)
                engine.draw_rect(icon_x, icon_y, icon_w, icon_h, 0, 230, 130, 255, thickness=1)
                engine.draw_text("✓", engine.font_badge, icon_x + icon_w // 2, icon_y + icon_h // 2, 0, 245, 150, center_x=True, center_y=True)
            else:
                engine.fill_rect(icon_x, icon_y, icon_w, icon_h, 16, 28, 48, 205)
                engine.draw_rect(icon_x, icon_y, icon_w, icon_h, 0, 190, 240, 220, thickness=1)
                engine.draw_text("☁", engine.font_badge, icon_x + icon_w // 2, icon_y + icon_h // 2, 0, 230, 255, center_x=True, center_y=True)

            # Theme Name in Middle
            t_name = item.get("name", item.get("folder", ""))
            name_x = stt_x + stt_w + 8
            name_max_w = icon_x - name_x - 6
            name_lines = engine.wrap_text_to_width(t_name, engine.font_grid_title, name_max_w, max_lines=1)
            disp_name = name_lines[0] if name_lines else t_name
            t_col = (255, 255, 255) if is_sel else (205, 218, 235)
            engine.draw_text(disp_name, engine.font_grid_title, name_x, bar_y + bar_h // 2, t_col[0], t_col[1], t_col[2], center_y=True)

        # ----------------------------------------------------------------------
        # 4. Live Download & Installation Progress Modal Overlay
        # ----------------------------------------------------------------------
        if self.downloading_theme:
            # Dim Backdrop
            engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 10, 14, 24, 210)

            # Center Dialog Box
            mw = 660
            mh = 240
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            engine.fill_rect(mx, my, mw, mh, 18, 25, 42, 255)
            engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

            # Sub-Header
            engine.fill_rect(mx + 2, my + 2, mw - 4, 44, 24, 36, 62, 255)
            engine.draw_text(tr("theme_progress_title"), engine.font_sub, mx + 20, my + 24, 0, 246, 246, center_y=True)

            # Theme Name
            t_name = self.dl_theme_info.get("name", self.dl_theme_info.get("folder", "Theme"))
            engine.draw_text(t_name[:40], engine.font_badge, mx + mw - 20, my + 24, 255, 215, 0, center_y=True, right_align=True)

            # Progress Bar Track
            bar_margin = 32
            bar_w = mw - bar_margin * 2
            bar_h = 26
            bar_x = mx + bar_margin
            bar_y = my + 110

            pct = max(0, min(100, self.dl_pct))
            msg_str = self.dl_msg or ("Đang xử lý..." if state.current_lang == "VI" else "Processing...")

            engine.fill_rect(bar_x, bar_y, bar_w, bar_h, 12, 18, 32, 255)
            engine.draw_rect(bar_x, bar_y, bar_w, bar_h, 45, 65, 105, 255, thickness=2)

            fill_w = int((bar_w - 4) * (pct / 100.0))
            if fill_w > 0:
                engine.fill_rect(bar_x + 2, bar_y + 2, fill_w, bar_h - 4, 0, 230, 150, 255)

            # Text Above Bar
            engine.draw_text(tr("theme_progress_label"), engine.font_sub, bar_x, bar_y - 18, 180, 205, 235, center_y=True)
            engine.draw_text(f"{pct}%", engine.font_badge, bar_x + bar_w, bar_y - 18, 0, 255, 160, center_y=True, right_align=True)

            # Text Below Bar
            engine.draw_text(msg_str[:55], engine.font_sub, bar_x, bar_y + 36, 200, 220, 245)

            # Note
            engine.draw_text(tr("theme_wait_hint"), engine.font_footer, mx + mw // 2, my + mh - 24, 150, 175, 205, center_x=True, center_y=True)


