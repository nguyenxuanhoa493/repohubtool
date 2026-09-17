# -*- coding: utf-8 -*-
"""Unified Full-screen Game Details, Download Progress & Action Dashboard Modal."""

import os
import time
import threading
from .. import state
from ..paths import SDCARD_PATH, resolve_rom_dir
from ..i18n import tr
from ..storage import human_bytes
from ..catalog import clean_game_title, get_system_display_name
from ..cheat_manager import has_cheat_file, check_or_download_single_cheat
from ..boxart_scraper import scrape_boxart_for_single_rom
from ..j2me import (resolution_of_path, pretty_resolution,
                   DEFAULT_PHONE_MODE, load_default_phone_mode)
from ..emulators import resolve as resolve_emulator
from ..ui.boxart import resolve_game_img_path
from ..downloader import (enqueue_download, start_next_queued, dl_state,
                         download_state_for, is_download_running, cancel_active_download)
from .base import BaseModal


def _act_ids(sys_code):
    """Action button layout per system for downloaded games."""
    if sys_code == "JAVA":
        return ["PLAY", "RES", "GET_BOXART", "REGET", "DEL", "CLOSE"]
    return ["PLAY", "PLAY_CHEAT", "GET_CHEAT", "GET_BOXART", "NETPLAY", "REGET", "DEL", "CLOSE"]


class GameActionModal(BaseModal):
    """Unified Full-screen Game Details, Live Download Progress & Action Dashboard Modal."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.selected_opt = 0
        self.game_info = {}
        self.sys_code = ""
        self.rom_path = ""
        self.img_path = ""
        self.on_launch_cb = None
        self.on_delete_cb = None
        self.on_netplay_cb = None
        self.on_res_cb = None
        self.on_download_success_cb = None
        self.was_downloading = False

    def open(self, data=None):
        super().open(data)
        self.selected_opt = 0
        self.game_info = self.data.get("game_info") or {}
        self.sys_code = self.data.get("sys_code", "")
        self.rom_path = self.data.get("rom_path", "")
        self.img_path = self.data.get("img_path", "")
        self.on_launch_cb = self.data.get("on_launch")
        self.on_delete_cb = self.data.get("on_delete")
        self.on_netplay_cb = self.data.get("on_netplay")
        self.on_res_cb = self.data.get("on_res")
        self.on_download_success_cb = self.data.get("on_download_success")
        self.was_downloading = False

        # Auto-resolve rom path if not provided
        fname = self.game_info.get("filename", "")
        if not self.rom_path and fname and self.sys_code:
            r_dir = resolve_rom_dir(self.sys_code)
            if r_dir:
                cand = os.path.join(r_dir, fname)
                if os.path.exists(cand):
                    self.rom_path = cand

        # Auto-resolve boxart if not provided
        if not self.img_path and fname and self.sys_code:
            self.img_path = resolve_game_img_path(self.sys_code, fname)

    def is_downloaded(self):
        if self.rom_path and os.path.exists(self.rom_path):
            return True
        fname = self.game_info.get("filename", "")
        if fname and self.sys_code:
            r_dir = resolve_rom_dir(self.sys_code)
            if r_dir and os.path.exists(os.path.join(r_dir, fname)):
                self.rom_path = os.path.join(r_dir, fname)
                return True
        return False

    def is_downloading(self):
        if not self.game_info:
            return False
        return download_state_for(self.game_info) in ("downloading", "queued") or (
            is_download_running() and dl_state.get("active") and dl_state.get("title") == self.game_info.get("title")
        )

    def _check_download_transition(self):
        """Detect when background/active download finishes and transition smoothly."""
        dling = self.is_downloading()
        if dling:
            self.was_downloading = True
            return

        if self.was_downloading:
            self.was_downloading = False
            fname = self.game_info.get("filename", "")
            r_dir = resolve_rom_dir(self.sys_code)
            downloaded = False
            if r_dir and fname and os.path.exists(os.path.join(r_dir, fname)):
                downloaded = True
                self.rom_path = os.path.join(r_dir, fname)
            elif dl_state.get("status") == "success":
                downloaded = True

            if downloaded:
                if not self.img_path:
                    self.img_path = resolve_game_img_path(self.sys_code, fname)
                self.selected_opt = 0
                if self.on_download_success_cb:
                    self.on_download_success_cb(self.sys_code, self.game_info)
                if self.engine:
                    self.engine.toast("Tải game thành công!", text_color=(0, 255, 160))

    def handle_input(self, inputs):
        if not self.active:
            return False

        self._check_download_transition()

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        # ----------------------------------------------------
        # 1. State: Downloading
        # ----------------------------------------------------
        if self.is_downloading():
            if btn_b:
                # Run in background & dismiss modal
                self.close()
                return True
            if btn_x:
                cancel_active_download()
                self.was_downloading = False
                if self.engine:
                    self.engine.toast("Đã hủy tải game!")
                return True
            return True

        # ----------------------------------------------------
        # 2. State: Pre-Download (Not yet downloaded)
        # ----------------------------------------------------
        if not self.is_downloaded():
            if btn_b:
                self.close()
                return True
            if btn_a:
                # Start download
                msg = enqueue_download(self.sys_code, self.game_info)
                start_next_queued(background=False)
                self.was_downloading = True
                if msg and self.engine:
                    self.engine.toast(msg)
                return True
            if btn_x:
                # Fetch Boxart
                fname = self.game_info.get("filename", "")
                g_title = self.game_info.get("title", "")
                if self.engine:
                    self.engine.toast("Đang tải ảnh bìa...")
                def _bg_boxart_predl():
                    ok, res = scrape_boxart_for_single_rom(self.sys_code, fname, g_title)
                    if ok:
                        self.img_path = res
                        if self.engine:
                            self.engine.toast("Đã tải xong ảnh bìa!")
                    else:
                        if self.engine:
                            self.engine.toast(res)
                threading.Thread(target=_bg_boxart_predl, daemon=True).start()
                return True
            return True

        # ----------------------------------------------------
        # 3. State: Downloaded (Action Dashboard Grid)
        # ----------------------------------------------------
        acts = _act_ids(self.sys_code)
        num_acts = len(acts)
        cols = 3

        if btn_b:
            self.close()
            return True

        if btn_up:
            if self.selected_opt >= cols:
                self.selected_opt -= cols
            else:
                target = self.selected_opt + ((num_acts - 1 - self.selected_opt) // cols) * cols
                if target >= num_acts:
                    target -= cols
                self.selected_opt = max(0, target)
            return True
        elif btn_down:
            if self.selected_opt + cols < num_acts:
                self.selected_opt += cols
            else:
                self.selected_opt = self.selected_opt % cols
            return True
        elif btn_left:
            if self.selected_opt > 0:
                self.selected_opt -= 1
            else:
                self.selected_opt = num_acts - 1
            return True
        elif btn_right:
            if self.selected_opt < num_acts - 1:
                self.selected_opt += 1
            else:
                self.selected_opt = 0
            return True

        if btn_a:
            act_id = acts[self.selected_opt] if 0 <= self.selected_opt < num_acts else None
            if act_id == "CLOSE":
                self.close()
                return True
            elif act_id == "PLAY":
                self.close()
                if self.on_launch_cb:
                    self.on_launch_cb(self.sys_code, self.game_info, with_cheat=False)
                return True
            elif act_id == "PLAY_CHEAT":
                self.close()
                if self.on_launch_cb:
                    self.on_launch_cb(self.sys_code, self.game_info, with_cheat=True)
                return True
            elif act_id == "GET_CHEAT":
                fname = self.game_info.get("filename", "")
                g_title = self.game_info.get("title", "")
                if self.engine:
                    self.engine.toast("Đang tải Cheat Code..." if state.current_lang == "VI" else "Downloading Cheats...")
                def _bg_cheat():
                    ok, msg = check_or_download_single_cheat(self.sys_code, fname, g_title)
                    if self.engine:
                        self.engine.toast(msg)
                threading.Thread(target=_bg_cheat, daemon=True).start()
                return True
            elif act_id == "GET_BOXART":
                fname = self.game_info.get("filename", "")
                g_title = self.game_info.get("title", "")
                if self.engine:
                    self.engine.toast("Đang tải ảnh bìa..." if state.current_lang == "VI" else "Scraping Boxart...")
                def _bg_boxart():
                    ok, res = scrape_boxart_for_single_rom(self.sys_code, fname, g_title)
                    if ok:
                        self.img_path = res
                        if self.engine:
                            self.engine.toast("Đã tải xong ảnh bìa!" if state.current_lang == "VI" else "Boxart downloaded!")
                    else:
                        if self.engine:
                            self.engine.toast(res)
                threading.Thread(target=_bg_boxart, daemon=True).start()
                return True
            elif act_id == "NETPLAY":
                self.close()
                if self.on_netplay_cb:
                    self.on_netplay_cb(self.sys_code, self.game_info)
                return True
            elif act_id == "DEL":
                self.close()
                if self.on_delete_cb:
                    self.on_delete_cb(self.sys_code, self.game_info)
                return True
            elif act_id == "RES":
                if self.on_res_cb:
                    self.on_res_cb(self.sys_code, self.game_info, self.rom_path)
                return True
            elif act_id == "REGET":
                # Re-download trigger
                d_url = self.game_info.get("download_url") or self.game_info.get("url")
                enqueue_download(self.sys_code, self.game_info)
                start_next_queued(background=False)
                self.was_downloading = True
                if self.engine:
                    self.engine.toast("Bắt đầu tải lại game...")
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        self._check_download_transition()

        # Dim Backdrop
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 13, 17, 28, 255)

        is_dl = self.is_downloaded()
        is_dling = self.is_downloading()

        # ----------------------------------------------------------------------
        # Header Bar
        # ----------------------------------------------------------------------
        head_h = 58
        engine.fill_rect(0, 0, state.SCREEN_W, head_h, 20, 28, 48, 255)
        engine.fill_rect(0, head_h - 2, state.SCREEN_W, 2, 0, 246, 246, 255)

        if is_dling:
            header_str = "TIẾN ĐỘ TẢI GAME"
        elif not is_dl:
            header_str = "CHI TIẾT & TẢI GAME"
        else:
            header_str = tr("act_modal_title")

        engine.draw_text(header_str, engine.font_title, 28, head_h // 2, 0, 246, 246, center_y=True)

        g_title = clean_game_title(self.game_info.get("title") or "Game")
        disp_gt = f"[{self.sys_code}] {g_title}"
        if len(disp_gt) > 34:
            disp_gt = disp_gt[:31] + "..."
        gt_w = engine.measure_text(disp_gt, engine.font_badge)
        engine.draw_text(disp_gt, engine.font_badge, state.SCREEN_W - 28 - gt_w, head_h // 2, 255, 215, 0, center_y=True)

        # ----------------------------------------------------------------------
        # Footer Bar
        # ----------------------------------------------------------------------
        foot_h = 50
        fy = state.SCREEN_H - foot_h
        engine.fill_rect(0, fy, state.SCREEN_W, foot_h, 16, 22, 36, 255)
        engine.fill_rect(0, fy, state.SCREEN_W, 1, 40, 55, 85, 255)

        if is_dling:
            engine.draw_footer_btn(32, fy, foot_h, "B", "Chạy ngầm", (70, 95, 140), is_dark_btn=False)
            engine.draw_footer_btn(state.SCREEN_W - 175, fy, foot_h, "X", "Hủy tải", (255, 75, 75), is_dark_btn=True)
        elif not is_dl:
            fx = 32
            fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Tải game ngay", (0, 230, 150), is_dark_btn=True)
            fx = engine.draw_footer_btn(fx, fy, foot_h, "X", "Tải ảnh bìa", (0, 210, 255), is_dark_btn=False)
            engine.draw_footer_btn(state.SCREEN_W - 165, fy, foot_h, "B", "Đóng", (255, 75, 75), is_dark_btn=False)
        else:
            fx = 32
            fx = engine.draw_footer_btn(fx, fy, foot_h, "◄►▲▼", "Chọn hành động" if state.current_lang == "VI" else "Navigate", (70, 95, 140), is_dark_btn=False)
            fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Thực hiện" if state.current_lang == "VI" else "Confirm", (0, 230, 150))
            engine.draw_footer_btn(state.SCREEN_W - 165, fy, foot_h, "B", "Quay lại" if state.current_lang == "VI" else "Back", (255, 70, 70), is_dark_btn=False)

        # ----------------------------------------------------------------------
        # Body Geometry
        # ----------------------------------------------------------------------
        body_y = head_h + 14
        body_h = fy - body_y - 12
        pad_x = 28
        gap_col = 20

        left_w = int((state.SCREEN_W - pad_x * 2 - gap_col) * 0.38)
        right_w = (state.SCREEN_W - pad_x * 2 - gap_col) - left_w
        left_x = pad_x
        right_x = left_x + left_w + gap_col

        # ----------------------------------------------------------------------
        # 1. Left Card: Boxart Preview
        # ----------------------------------------------------------------------
        engine.fill_rect(left_x, body_y, left_w, body_h, 18, 25, 42, 255)
        engine.draw_rect(left_x, body_y, left_w, body_h, 45, 60, 95, 255, thickness=2)

        box_pad = 16
        box_w = left_w - box_pad * 2
        box_h = body_h - box_pad * 2 - 40
        box_x = left_x + box_pad
        box_y = body_y + box_pad

        drawn_img = False
        if self.img_path and os.path.exists(self.img_path):
            drawn_img = engine.draw_proportional_boxart(self.img_path, box_x, box_y, box_w, box_h)
        if not drawn_img:
            engine.draw_default_boxart_avatar(box_x, box_y, box_w, box_h, self.sys_code, g_title)

        t_lines = engine.wrap_text_to_width(g_title, engine.font_sub, left_w - 24, max_lines=2)
        ty = body_y + body_h - 40
        for tl in t_lines:
            engine.draw_text(tl, engine.font_sub, left_x + left_w // 2, ty, 255, 255, 255, center_x=True, center_y=True)
            ty += 24

        # ----------------------------------------------------------------------
        # 2. Right Card: Info Header
        # ----------------------------------------------------------------------
        fname = self.game_info.get("filename", "")
        f_size_str = self.game_info.get("file_size_str", "")
        if not f_size_str:
            if self.rom_path and os.path.exists(self.rom_path):
                f_size_str = human_bytes(os.path.getsize(self.rom_path))
            else:
                f_size_str = "--"

        info_h = 100
        engine.fill_rect(right_x, body_y, right_w, info_h, 18, 25, 42, 255)
        engine.draw_rect(right_x, body_y, right_w, info_h, 45, 60, 95, 255, thickness=1)

        sys_disp = get_system_display_name(self.sys_code)
        engine.draw_text(f"• Tên game: {g_title[:38]}", engine.font_sub, right_x + 18, body_y + 16, 255, 255, 255)
        engine.draw_text(f"• Hệ máy: {self.sys_code} ({sys_disp})", engine.font_sub, right_x + 18, body_y + 44, 0, 230, 255)
        engine.draw_text(f"• Tệp tin: {fname[:38]}", engine.font_sub, right_x + 18, body_y + 72, 200, 215, 235)

        engine.draw_text(f"Dung lượng: {f_size_str}", engine.font_sub, right_x + right_w - 22, body_y + 44, 255, 215, 0, right_align=True)

        bottom_y = body_y + info_h + 14
        bottom_h = body_h - info_h - 14

        # ----------------------------------------------------------------------
        # 3. Right Card (Bottom): Dynamic Content by State
        # ----------------------------------------------------------------------

        # CASE A: DOWNLOADING LIVE PROGRESS
        if is_dling:
            engine.fill_rect(right_x, bottom_y, right_w, bottom_h, 18, 25, 42, 255)
            engine.draw_rect(right_x, bottom_y, right_w, bottom_h, 0, 246, 246, 255, thickness=2)

            # Sub-Header
            engine.fill_rect(right_x + 2, bottom_y + 2, right_w - 4, 46, 24, 36, 62, 255)
            engine.draw_text("TIẾN TRÌNH TẢI & GIẢI NÉN ROM", engine.font_sub, right_x + 20, bottom_y + 25, 0, 246, 246, center_y=True)

            bar_margin = 32
            bar_w = right_w - bar_margin * 2
            bar_h = 24
            bar_x = right_x + bar_margin
            bar_y = bottom_y + 130

            pct = max(0, min(100, dl_state.get("progress_pct", 0)))
            speed_str = dl_state.get("speed_str", "0 KB/s")
            status_msg = dl_state.get("msg", "Đang tải dữ liệu...")
            down_str = dl_state.get("downloaded_str", "")

            # Progress Bar Track
            engine.fill_rect(bar_x, bar_y, bar_w, bar_h, 12, 18, 32, 255)
            engine.draw_rect(bar_x, bar_y, bar_w, bar_h, 45, 65, 105, 255, thickness=2)

            # Progress Bar Fill
            fill_w = int((bar_w - 4) * (pct / 100.0))
            if fill_w > 0:
                engine.fill_rect(bar_x + 2, bar_y + 2, fill_w, bar_h - 4, 0, 230, 150, 255)

            # Text Above Bar
            engine.draw_text("Tiến độ:", engine.font_sub, bar_x, bar_y - 18, 180, 205, 235, center_y=True)
            engine.draw_text(f"{pct}% ({speed_str})", engine.font_badge, bar_x + bar_w, bar_y - 18, 0, 255, 160, center_y=True, right_align=True)

            # Text Below Bar
            engine.draw_text(status_msg[:54], engine.font_sub, bar_x, bar_y + 36, 200, 220, 245)
            if down_str:
                engine.draw_text(f"Đã tải: {down_str}", engine.font_badge, bar_x + bar_w, bar_y + 36, 255, 215, 0, right_align=True)

            # Quick Helper Note
            note_y = bottom_y + bottom_h - 70
            engine.fill_rect(bar_x, note_y, bar_w, 48, 22, 32, 54, 255)
            engine.draw_rect(bar_x, note_y, bar_w, 48, 45, 65, 105, 255, thickness=1)
            engine.draw_text("💡 Nhấn (B) để Chạy ngầm hoặc (X) để Hủy tải bất kỳ lúc nào.", engine.font_footer, bar_x + bar_w // 2, note_y + 24, 170, 195, 225, center_x=True, center_y=True)

        # CASE B: PRE-DOWNLOAD (NOT DOWNLOADED)
        elif not is_dl:
            engine.fill_rect(right_x, bottom_y, right_w, bottom_h, 18, 25, 42, 255)
            engine.draw_rect(right_x, bottom_y, right_w, bottom_h, 45, 60, 95, 255, thickness=1)

            # Hero Card: TẢI GAME NGAY
            hero_pad = 24
            hero_w = right_w - hero_pad * 2
            hero_x = right_x + hero_pad
            hero_y = bottom_y + 28
            hero_h = 160

            # Glowing Hero Container
            engine.fill_rect(hero_x, hero_y, hero_w, hero_h, 24, 40, 68, 255)
            engine.draw_rect(hero_x, hero_y, hero_w, hero_h, 0, 246, 246, 255, thickness=3)
            engine.fill_rect(hero_x + 4, hero_y + 4, hero_w - 8, 4, 0, 246, 246, 255)

            # Hero Icon & Text
            engine.draw_text("TẢI GAME VÀO MÁY NGAY", engine.font_title, hero_x + 32, hero_y + 44, 0, 255, 180, center_y=True)
            engine.draw_text("• Tự động tải ROM từ kho dữ liệu tốc độ cao", engine.font_sub, hero_x + 32, hero_y + 82, 220, 235, 255)
            engine.draw_text("• Tự động giải nén, thiết lập giả lập và cào ảnh bìa", engine.font_sub, hero_x + 32, hero_y + 114, 180, 205, 235)

            # Button Badge in Hero Card
            engine.draw_footer_btn(hero_x + hero_w - 180, hero_y + hero_h // 2 - 24, 48, "A", "Tải về ngay", (0, 230, 150), is_dark_btn=True)

            # Secondary Action: Tải ảnh bìa
            sec_y = hero_y + hero_h + 24
            sec_h = 80
            engine.fill_rect(hero_x, sec_y, hero_w, sec_h, 20, 28, 48, 255)
            engine.draw_rect(hero_x, sec_y, hero_w, sec_h, 40, 58, 92, 255, thickness=1)

            engine.draw_text("Tìm và tải lại ảnh bìa độ nét cao (Boxart Scraping)", engine.font_sub, hero_x + 24, sec_y + sec_h // 2, 200, 215, 235, center_y=True)
            engine.draw_footer_btn(hero_x + hero_w - 165, sec_y + (sec_h - 44) // 2, 44, "X", "Tải ảnh bìa", (0, 210, 255), is_dark_btn=False)

        # CASE C: DOWNLOADED (ACTION GRID)
        else:
            has_cheat = has_cheat_file(self.sys_code, fname)
            cheat_col = (0, 230, 120) if has_cheat else (255, 215, 0)
            cheat_lbl = ("Đã có Cheat" if state.current_lang == "VI" else "Cheat Ready") if has_cheat else tr("act_get_cheat_title")

            rom_p = self.rom_path or os.path.join(SDCARD_PATH, "Roms", self.sys_code, fname)

            _act_look = {
                "PLAY":       (tr("act_play_title"), (0, 230, 150)),
                "PLAY_CHEAT": (tr("act_play_cheat_title"), (255, 170, 0)),
                "GET_CHEAT":  (cheat_lbl, cheat_col),
                "GET_BOXART": (tr("act_get_boxart_title"), (0, 246, 246)),
                "NETPLAY":    (tr("act_netplay_title"), (0, 210, 255)),
                "REGET":      (tr("act_reget_title"), (255, 200, 0)),
                "DEL":        (tr("act_del_title"), (255, 80, 80)),
                "RES":        (pretty_resolution(resolution_of_path(rom_p)), (255, 200, 0)),
                "CLOSE":      (tr("act_close_title"), (180, 200, 230)),
            }
            acts = _act_ids(self.sys_code)
            actions = [(i, _act_look[i][0], _act_look[i][1]) for i in acts if i in _act_look]

            cols = 3
            rows = 3
            gap_x = 12
            gap_y = 10
            tile_w = (right_w - (cols - 1) * gap_x) // cols
            tile_h = (bottom_h - (rows - 1) * gap_y) // rows

            for t_idx, (act_id, t_title, t_col) in enumerate(actions):
                r_idx = t_idx // cols
                c_idx = t_idx % cols
                tx = right_x + c_idx * (tile_w + gap_x)
                ty = bottom_y + r_idx * (tile_h + gap_y)
                is_t_sel = (t_idx == self.selected_opt)
                is_cheat_ready = (act_id == "GET_CHEAT" and has_cheat)

                if is_t_sel:
                    if is_cheat_ready:
                        engine.fill_rect(tx, ty, tile_w, tile_h, 20, 56, 44, 255)
                        engine.draw_rect(tx, ty, tile_w, tile_h, 0, 255, 140, 255, thickness=3)
                        engine.fill_rect(tx + 4, ty + 4, tile_w - 8, 4, 0, 255, 140, 255)
                    else:
                        engine.fill_rect(tx, ty, tile_w, tile_h, 32, 52, 90, 255)
                        engine.draw_rect(tx, ty, tile_w, tile_h, 0, 246, 246, 255, thickness=3)
                        engine.fill_rect(tx + 4, ty + 4, tile_w - 8, 4, t_col[0], t_col[1], t_col[2], 255)
                else:
                    if is_cheat_ready:
                        engine.fill_rect(tx, ty, tile_w, tile_h, 14, 32, 26, 255)
                        engine.draw_rect(tx, ty, tile_w, tile_h, 0, 220, 110, 255, thickness=2)
                        engine.fill_rect(tx + 4, ty + 4, tile_w - 8, 3, 0, 220, 110, 255)
                    else:
                        engine.fill_rect(tx, ty, tile_w, tile_h, 18, 26, 44, 255)
                        engine.draw_rect(tx, ty, tile_w, tile_h, 40, 58, 92, 255, thickness=1)

                ib_sz = min(72, tile_h - 38)
                ib_x = tx + (tile_w - ib_sz) // 2
                ib_y = ty + max(6, (tile_h - ib_sz - 28) // 2 - 3)
                engine.fill_rect(ib_x, ib_y, ib_sz, ib_sz, 14, 20, 34, 255)
                engine.draw_rect(ib_x, ib_y, ib_sz, ib_sz, t_col[0], t_col[1], t_col[2], 255, thickness=2)
                engine.draw_action_vector_icon(act_id, ib_x + ib_sz // 2, ib_y + ib_sz // 2, 70, t_col[0], t_col[1], t_col[2], 255)

                txt_y = ib_y + ib_sz + 20
                engine.draw_text(t_title, engine.font_sub, tx + tile_w // 2, txt_y, 255, 255, 255, center_x=True, center_y=True)
