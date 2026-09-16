# -*- coding: utf-8 -*-
"""Downloaded Games / Local Library Screen with System Tabs & Grid/List View."""

import os
import subprocess
from .. import state
from ..paths import SDCARD_PATH
from ..i18n import tr
from ..catalog import (scan_all_downloaded_games, alpha_index,
                      get_system_display_name, clean_game_title)
from ..ui.boxart import resolve_game_img_path
from ..emulators import resolve as resolve_emulator
from ..modals.game_action import GameActionModal
from ..modals.alphabet import AlphabetModal
from ..modals.common import ResolutionModal
from .base import BaseScreen


class LibraryScreen(BaseScreen):
    """Local downloaded ROMs library with system tabs, grid/list view, and game action launcher."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.all_games = []
        self.system_tabs = ["ALL"]
        self.current_tab_idx = 0
        self.filtered_games = []
        self.selected_idx = 0
        self.scroll_top = 0
        self.scroll_row = 0
        self.sort_mode = "downloads"  # "downloads" or "alpha"

    def on_enter(self, params=None):
        self.refresh_games()

    def refresh_games(self):
        """Scan and build system tabs list."""
        self.all_games = scan_all_downloaded_games()
        
        # Build available system tabs
        sys_set = []
        for g in self.all_games:
            sc = g.get("sys_code", "ROM")
            if sc not in sys_set:
                sys_set.append(sc)

        self.system_tabs = ["ALL"] + sys_set
        if self.current_tab_idx >= len(self.system_tabs):
            self.current_tab_idx = 0

        self.apply_filter()

    def apply_filter(self):
        """Filter games by selected system tab."""
        cur_tab = self.system_tabs[self.current_tab_idx]
        if cur_tab == "ALL":
            self.filtered_games = list(self.all_games)
        else:
            self.filtered_games = [g for g in self.all_games if g.get("sys_code") == cur_tab]

        if self.sort_mode == "alpha":
            self.filtered_games.sort(key=lambda g: str(clean_game_title(g.get("title", ""))).lower())

        if self.selected_idx >= len(self.filtered_games):
            self.selected_idx = max(0, len(self.filtered_games) - 1)

    def get_header_title(self):
        cur_tab = self.system_tabs[self.current_tab_idx]
        cnt = len(self.filtered_games)
        tab_name = get_system_display_name(cur_tab) if cur_tab != "ALL" else tr("lib_tab_all")
        return f"{tr('lib_title')} - {tab_name} ({cnt})"

    def get_footer_actions(self):
        v_mode_txt = "Dạng lưới" if state.downloaded_view_mode == "list" else "Danh sách"
        actions = [
            ("A", tr("footer_action"), (0, 230, 150), (220, 225, 235), True),
            ("X", v_mode_txt, (138, 43, 226), (220, 225, 235), False),
            ("Y", tr("footer_sort"), (255, 200, 0), (220, 225, 235), True),
            ("SEL", tr("footer_alpha"), (0, 210, 255), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]
        return actions

    def handle_input(self, inputs):
        btn_l1 = inputs.get("btn_l1")
        btn_r1 = inputs.get("btn_r1")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_y = inputs.get("btn_y")
        btn_select = inputs.get("btn_select")

        # L1 / R1: Switch system tab
        if btn_l1:
            if self.current_tab_idx > 0:
                self.current_tab_idx -= 1
            else:
                self.current_tab_idx = len(self.system_tabs) - 1
            self.selected_idx = 0
            self.scroll_top = 0
            self.scroll_row = 0
            self.apply_filter()
            return True

        if btn_r1:
            if self.current_tab_idx < len(self.system_tabs) - 1:
                self.current_tab_idx += 1
            else:
                self.current_tab_idx = 0
            self.selected_idx = 0
            self.scroll_top = 0
            self.scroll_row = 0
            self.apply_filter()
            return True

        if btn_b:
            self.engine.pop_screen()
            return True

        # X: Toggle Grid / List view mode
        if btn_x:
            state.downloaded_view_mode = "list" if state.downloaded_view_mode == "grid" else "grid"
            state.save_settings()
            return True

        # Y: Toggle Sort Order
        if btn_y:
            self.sort_mode = "alpha" if self.sort_mode == "downloads" else "downloads"
            self.apply_filter()
            sort_lbl = "Theo tên A-Z" if self.sort_mode == "alpha" else "Mới tải về"
            self.engine.toast(f"Sắp xếp: {sort_lbl}")
            return True

        # SELECT: Open Alphabet Quick Jump Modal
        if btn_select:
            avail, counts = alpha_index(self.filtered_games)

            def _on_jump(letter):
                if letter in avail:
                    self.selected_idx = avail[letter]
                    self.scroll_top = max(0, min(self.selected_idx, len(self.filtered_games) - 7))
                    self.scroll_row = self.selected_idx // 3

            self.engine.open_modal(AlphabetModal(self.engine), {
                "available_map": avail,
                "counts_map": counts,
                "on_select": _on_jump
            })
            return True

        total_games = len(self.filtered_games)
        if total_games == 0:
            return False

        if state.downloaded_view_mode == "grid":
            cols = 3
            rows = 2
            if btn_up:
                if self.selected_idx >= cols:
                    self.selected_idx -= cols
                else:
                    target = self.selected_idx + ((total_games - 1 - self.selected_idx) // cols) * cols
                    if target >= total_games:
                        target -= cols
                    self.selected_idx = max(0, target)
                cur_row = self.selected_idx // cols
                if cur_row < self.scroll_row:
                    self.scroll_row = cur_row
                elif cur_row >= self.scroll_row + rows:
                    self.scroll_row = cur_row - rows + 1
                return True
            elif btn_down:
                if self.selected_idx + cols < total_games:
                    self.selected_idx += cols
                else:
                    self.selected_idx = self.selected_idx % cols
                cur_row = self.selected_idx // cols
                if cur_row < self.scroll_row:
                    self.scroll_row = cur_row
                elif cur_row >= self.scroll_row + rows:
                    self.scroll_row = cur_row - rows + 1
                return True
            elif btn_left:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                else:
                    self.selected_idx = total_games - 1
                cur_row = self.selected_idx // cols
                if cur_row < self.scroll_row:
                    self.scroll_row = cur_row
                elif cur_row >= self.scroll_row + rows:
                    self.scroll_row = cur_row - rows + 1
                return True
            elif btn_right:
                if self.selected_idx < total_games - 1:
                    self.selected_idx += 1
                else:
                    self.selected_idx = 0
                cur_row = self.selected_idx // cols
                if cur_row < self.scroll_row:
                    self.scroll_row = cur_row
                elif cur_row >= self.scroll_row + rows:
                    self.scroll_row = cur_row - rows + 1
                return True
        else:
            max_vis = 7
            if btn_up:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                else:
                    self.selected_idx = total_games - 1
                    self.scroll_top = max(0, total_games - max_vis)
                if self.selected_idx < self.scroll_top:
                    self.scroll_top = self.selected_idx
                return True
            elif btn_down:
                if self.selected_idx < total_games - 1:
                    self.selected_idx += 1
                else:
                    self.selected_idx = 0
                    self.scroll_top = 0
                if self.selected_idx >= self.scroll_top + max_vis:
                    self.scroll_top = self.selected_idx - max_vis + 1
                return True

        if btn_a:
            g = self.filtered_games[self.selected_idx]
            sc = g.get("sys_code", "ROM")
            fn = g.get("filename", "")
            rp = g.get("path") or g.get("rom_path") or os.path.join(SDCARD_PATH, "Roms", sc, fn)
            ip = resolve_game_img_path(sc, fn)

            def _on_launch(sys_code, game_info, with_cheat=False, netplay_param=None):
                self.launch_game(sys_code, game_info, with_cheat=with_cheat, netplay_param=netplay_param)

            def _on_delete(sys_code, game_info):
                self.delete_game(sys_code, game_info)

            def _on_netplay(sys_code, game_info):
                from ..modals.netplay import NetplayModal
                self.engine.open_modal(NetplayModal(self.engine), {
                    "sys_code": sys_code,
                    "game_info": game_info,
                    "rom_path": rp,
                    "on_launch": _on_launch
                })

            def _on_res(sys_code, game_info, rom_path):
                self.engine.open_modal(ResolutionModal(self.engine), {
                    "sys_code": sys_code,
                    "game_info": game_info,
                    "rom_path": rom_path
                })

            self.engine.open_modal(GameActionModal(self.engine), {
                "sys_code": sc,
                "game_info": g,
                "rom_path": rp,
                "img_path": ip,
                "on_launch": _on_launch,
                "on_delete": _on_delete,
                "on_netplay": _on_netplay,
                "on_res": _on_res
            })
            return True

        return False

    def launch_game(self, sys_code, game_info, with_cheat=False, netplay_param=None):
        """Launch emulator for target game with arguments."""
        rom_p = game_info.get("path") or game_info.get("rom_path") or ""
        fn = game_info.get("filename", "")
        if not rom_p or not os.path.exists(rom_p):
            candidates = [
                os.path.join(SDCARD_PATH, "Roms", sys_code, fn),
                os.path.join(SDCARD_PATH, "Roms", f"({sys_code})", fn),
            ]
            for c in candidates:
                if fn and os.path.exists(c):
                    rom_p = c
                    break

        if not rom_p or not os.path.exists(rom_p):
            self.engine.toast("Không tìm thấy file ROM trên thẻ nhớ!")
            return

        emu_dir, script_path = resolve_emulator(sys_code)
        if not script_path or not os.path.exists(script_path):
            self.engine.toast(f"Không tìm thấy giả lập cho hệ {sys_code}!")
            return

        title_display = clean_game_title(game_info.get("title", "Game"))
        self.engine.toast(f"Đang khởi động {title_display}...")

        handoff_script = f"""#!/bin/sh
cd "{emu_dir or os.path.dirname(script_path)}"
"{script_path}" "{rom_p}" {" " + str(netplay_param) if netplay_param else ""}
"""
        try:
            with open("/tmp/launch_game.sh", "w", encoding="utf-8") as f:
                f.write(handoff_script)
            os.chmod("/tmp/launch_game.sh", 0o755)
            with open("/tmp/rh_last_screen.txt", "w", encoding="utf-8") as f:
                f.write("library")
            self.engine.running = False
        except Exception as e:
            self.engine.toast(f"Lỗi khởi động: {e}")

    def delete_game(self, sys_code, game_info):
        """Delete local ROM file and associated assets."""
        rom_p = game_info.get("path") or game_info.get("rom_path") or ""
        fn = game_info.get("filename", "")
        if not rom_p or not os.path.exists(rom_p):
            candidates = [
                os.path.join(SDCARD_PATH, "Roms", sys_code, fn),
                os.path.join(SDCARD_PATH, "Roms", f"({sys_code})", fn),
            ]
            for c in candidates:
                if fn and os.path.exists(c):
                    rom_p = c
                    break

        if rom_p and os.path.exists(rom_p):
            try:
                os.remove(rom_p)
            except Exception:
                pass
        ip = resolve_game_img_path(sys_code, fn)
        if ip and os.path.exists(ip):
            try:
                os.remove(ip)
            except Exception:
                pass
        self.engine.toast("Đã xóa game!")
        self.refresh_games()

    def render(self, engine):
        # 1. System Tabs Bar (L1 / R1)
        tab_h = 38
        tab_y = 64
        engine.fill_rect(0, tab_y, state.SCREEN_W, tab_h, 17, 24, 40, 245)
        engine.fill_rect(0, tab_y + tab_h - 1, state.SCREEN_W, 1, 35, 48, 72, 255)

        engine.draw_text("< L1", engine.font_footer, 20, tab_y + tab_h // 2, 0, 220, 245, center_y=True)
        r1_txt = "R1 >"
        r1_w = engine.measure_text(r1_txt, engine.font_footer)
        engine.draw_text(r1_txt, engine.font_footer, state.SCREEN_W - 20 - r1_w, tab_y + tab_h // 2, 0, 220, 245, center_y=True)

        # Tab chips
        chip_start_x = 75
        chip_avail_w = state.SCREEN_W - 150
        num_tabs = len(self.system_tabs)
        max_vis_tabs = 8
        tab_scroll = max(0, min(self.current_tab_idx - max_vis_tabs // 2, num_tabs - max_vis_tabs)) if num_tabs > max_vis_tabs else 0

        vis_tabs = self.system_tabs[tab_scroll : tab_scroll + max_vis_tabs]
        chip_w = (chip_avail_w - (len(vis_tabs) - 1) * 8) // max(1, len(vis_tabs))

        for i, t_name in enumerate(vis_tabs):
            real_t_idx = tab_scroll + i
            tx = chip_start_x + i * (chip_w + 8)
            is_tab_sel = (real_t_idx == self.current_tab_idx)
            chip_label = tr("lib_tab_all") if t_name == "ALL" else t_name

            if is_tab_sel:
                engine.fill_rect(tx, tab_y + 4, chip_w, tab_h - 8, 0, 210, 255, 255)
                engine.draw_text(chip_label, engine.font_badge, tx + chip_w // 2, tab_y + tab_h // 2, 0, 20, 40, center_x=True, center_y=True)
            else:
                engine.fill_rect(tx, tab_y + 5, chip_w, tab_h - 10, 25, 35, 55, 255)
                engine.draw_text(chip_label, engine.font_badge, tx + chip_w // 2, tab_y + tab_h // 2, 170, 185, 210, center_x=True, center_y=True)

        # 2. Games Content Area
        content_y = tab_y + tab_h + 6
        content_h = state.SCREEN_H - content_y - 56 - 6

        if not self.filtered_games:
            engine.draw_text("CHƯA CÓ GAME NÀO TRONG MỤC NÀY", engine.font_item, state.SCREEN_W // 2, content_y + content_h // 2, 140, 160, 190, center_x=True, center_y=True)
            return

        if state.downloaded_view_mode == "grid":
            self.render_grid(engine, content_y, content_h)
        else:
            self.render_list(engine, content_y, content_h)

    def render_grid(self, engine, content_y, content_h):
        cols = 3
        rows = 2
        pad_x = 40
        gap_x = 18
        gap_y = 12

        card_w = (state.SCREEN_W - pad_x * 2 - (cols - 1) * gap_x) // cols
        card_h = (content_h - (rows - 1) * gap_y) // rows

        cur_row = self.selected_idx // cols
        if cur_row < self.scroll_row:
            self.scroll_row = cur_row
        elif cur_row >= self.scroll_row + rows:
            self.scroll_row = cur_row - rows + 1

        start_idx = self.scroll_row * cols
        vis_games = self.filtered_games[start_idx : start_idx + cols * rows]

        for i, g in enumerate(vis_games):
            real_idx = start_idx + i
            r = i // cols
            c = i % cols
            bx = pad_x + c * (card_w + gap_x)
            by = content_y + r * (card_h + gap_y)
            is_sel = (real_idx == self.selected_idx)

            if is_sel:
                engine.fill_rect(bx, by, card_w, card_h, 28, 44, 75, 255)
                engine.draw_rect(bx, by, card_w, card_h, 255, 215, 0, 255, thickness=3)
                engine.fill_rect(bx + 4, by + 4, card_w - 8, 4, 255, 215, 0, 255)
            else:
                engine.fill_rect(bx, by, card_w, card_h, 18, 25, 42, 255)
                engine.draw_rect(bx, by, card_w, card_h, 38, 52, 80, 255, thickness=1)

            # Boxart Image
            sc = g.get("sys_code", "ROM")
            fn = g.get("filename", "")
            ip = resolve_game_img_path(sc, fn)
            img_pad = 8
            img_w = card_w - img_pad * 2
            img_h = card_h - img_pad * 2 - 42
            ix = bx + img_pad
            iy = by + img_pad

            drawn = False
            if ip and os.path.exists(ip):
                drawn = engine.draw_proportional_boxart(ip, ix, iy, img_w, img_h)
            if not drawn:
                engine.draw_default_boxart_avatar(ix, iy, img_w, img_h, sc, g.get("title", ""))

            # Title
            clean_title = clean_game_title(g.get("title", ""))
            numbered_title = f"{real_idx + 1}. {clean_title}"
            t_lines = engine.wrap_text_to_width(numbered_title, engine.font_grid_title, card_w - 20, max_lines=2)
            t_col = (255, 255, 255) if is_sel else (200, 215, 235)
            if len(t_lines) == 1:
                engine.draw_text(t_lines[0], engine.font_grid_title, bx + card_w // 2, by + card_h - 22, t_col[0], t_col[1], t_col[2], center_x=True, center_y=True)
            elif len(t_lines) >= 2:
                engine.draw_text(t_lines[0], engine.font_grid_title, bx + card_w // 2, by + card_h - 30, t_col[0], t_col[1], t_col[2], center_x=True, center_y=True)
                engine.draw_text(t_lines[1], engine.font_grid_title, bx + card_w // 2, by + card_h - 13, t_col[0], t_col[1], t_col[2], center_x=True, center_y=True)

    def render_list(self, engine, content_y, content_h):
        pad_x = 28
        list_w = 560
        gap_x = 24
        preview_x = pad_x + list_w + gap_x
        preview_w = state.SCREEN_W - preview_x - pad_x

        card_h = 68
        card_gap = 6
        max_vis = 7
        total_list_h = max_vis * (card_h + card_gap) - card_gap
        start_list_y = content_y + 4
        preview_y = content_y + 4
        preview_h = total_list_h

        max_scroll = max(0, len(self.filtered_games) - max_vis)
        if self.selected_idx < self.scroll_top:
            self.scroll_top = self.selected_idx
        elif self.selected_idx >= self.scroll_top + max_vis:
            self.scroll_top = self.selected_idx - max_vis + 1
        self.scroll_top = max(0, min(max_scroll, self.scroll_top))

        vis_games = self.filtered_games[self.scroll_top : self.scroll_top + max_vis]
        show_sys_tag = (self.system_tabs[self.current_tab_idx] == "ALL")

        for i, g in enumerate(vis_games):
            real_idx = self.scroll_top + i
            cy = start_list_y + i * (card_h + card_gap)
            is_sel = (real_idx == self.selected_idx)

            if is_sel:
                engine.fill_rect(pad_x, cy, list_w, card_h, 24, 40, 70, 255)
                engine.draw_rect(pad_x, cy, list_w, card_h, 0, 246, 246, 255, thickness=2)
                engine.fill_rect(pad_x, cy + 6, 6, card_h - 12, 0, 246, 246, 255)
                text_r, text_g, text_b = 255, 255, 255
            else:
                engine.fill_rect(pad_x, cy, list_w, card_h, 15, 21, 35, 180)
                text_r, text_g, text_b = 185, 198, 220

            # System Tag Chip on left (Only when on 'ALL' tab)
            if show_sys_tag:
                sc = g.get("sys_code", "ROM")
                tag_w = 60
                tag_x = pad_x + 16
                tag_y = cy + (card_h - 26) // 2
                engine.fill_rect(tag_x, tag_y, tag_w, 26, 26, 36, 56, 255)
                engine.draw_text(sc, engine.font_badge, tag_x + tag_w // 2, tag_y + 13, 0, 210, 255, center_x=True, center_y=True)
                title_x = tag_x + tag_w + 12
            else:
                title_x = pad_x + 18

            # Clean Title (strip leading numbers like '097 - Contra' -> 'Contra')
            clean_title = clean_game_title(g.get("title", ""))
            numbered_title = f"{real_idx + 1}. {clean_title}"
            max_title_w = list_w - (title_x - pad_x) - 14
            title_text = engine.wrap_text_to_width(numbered_title, engine.font_item, max_title_w, max_lines=1)[0]
            engine.draw_text(title_text, engine.font_item, title_x, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

        # ----------------------------------------------------------------------
        # Right-side Boxart (Seamless, 2x Wide Size, No enclosing UI box)
        # ----------------------------------------------------------------------
        if 0 <= self.selected_idx < len(self.filtered_games):
            sel_g = self.filtered_games[self.selected_idx]
            sc = sel_g.get("sys_code", "ROM")
            fn = sel_g.get("filename", "")
            clean_title = clean_game_title(sel_g.get("title", ""))
            ip = resolve_game_img_path(sc, fn)

            drawn = False
            if ip and os.path.exists(ip):
                drawn = engine.draw_proportional_boxart(ip, preview_x, preview_y, preview_w, preview_h)
            if not drawn:
                engine.draw_default_boxart_avatar(preview_x, preview_y, preview_w, preview_h, sc, clean_title)
