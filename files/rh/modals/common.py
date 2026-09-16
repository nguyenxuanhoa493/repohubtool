# -*- coding: utf-8 -*-
"""Reusable common modals: Exit confirmation, Resolution picker, QR viewer, and Info dialogs."""

import os
import json
import time
import threading
from .. import state
from ..i18n import tr
from ..j2me import (RESOLUTIONS, pretty_resolution, resolution_of_path,
                   move_to_resolution)
from .base import BaseModal


class ExitModal(BaseModal):
    """Exit confirmation dialog."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.selected_btn = 0  # 0: Yes (Exit), 1: Cancel

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        if btn_b:
            self.close()
            return True

        if btn_left or btn_right:
            self.selected_btn = 1 - self.selected_btn
            return True

        if btn_a:
            if self.selected_btn == 0:
                self.engine.running = False
            self.close()
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 200)

        mw = 580
        mh = 240
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        engine.fill_rect(mx, my, mw, mh, 18, 25, 42, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

        title = "THOÁT ỨNG DỤNG?" if state.current_lang == "VI" else "EXIT RETROHUB?"
        engine.draw_text(title, engine.font_title, mx + mw // 2, my + 45, 255, 215, 0, center_x=True, center_y=True)

        msg = "Bạn có chắc chắn muốn quay về giao diện chính?" if state.current_lang == "VI" else "Are you sure you want to return to system menu?"
        engine.draw_text(msg, engine.font_sub, mx + mw // 2, my + 95, 200, 215, 235, center_x=True, center_y=True)

        btn_w = 200
        btn_h = 48
        by = my + mh - 70

        # Button Yes
        bx1 = mx + 60
        is_sel1 = (self.selected_btn == 0)
        engine.fill_rect(bx1, by, btn_w, btn_h, 45, 20, 24 if is_sel1 else 28, 255)
        engine.draw_rect(bx1, by, btn_w, btn_h, 255 if is_sel1 else 160, 70 if is_sel1 else 60, 70 if is_sel1 else 60, 255, thickness=2 if is_sel1 else 1)
        engine.draw_text("[A] Thoát" if state.current_lang == "VI" else "[A] Exit", engine.font_badge, bx1 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)

        # Button Cancel
        bx2 = mx + mw - 60 - btn_w
        is_sel2 = (self.selected_btn == 1)
        engine.fill_rect(bx2, by, btn_w, btn_h, 20, 45, 34 if is_sel2 else 28, 255)
        engine.draw_rect(bx2, by, btn_w, btn_h, 0 if is_sel2 else 70, 230 if is_sel2 else 140, 140 if is_sel2 else 90, 255, thickness=2 if is_sel2 else 1)
        engine.draw_text("[B] Hủy" if state.current_lang == "VI" else "[B] Cancel", engine.font_badge, bx2 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)


class ResolutionModal(BaseModal):
    """Resolution picker modal for J2ME Java titles."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.selected_idx = 0
        self.rom_path = ""
        self.sys_code = "JAVA"
        self.game_info = None

    def open(self, data=None):
        super().open(data)
        self.rom_path = self.data.get("rom_path", "")
        self.sys_code = self.data.get("sys_code", "JAVA")
        self.game_info = self.data.get("game_info") or {}
        cur_res = resolution_of_path(self.rom_path)
        if cur_res in RESOLUTIONS:
            self.selected_idx = RESOLUTIONS.index(cur_res)
        else:
            self.selected_idx = 0

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")

        if btn_b:
            self.close()
            return True

        if btn_up:
            if self.selected_idx > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = len(RESOLUTIONS) - 1
            return True
        elif btn_down:
            if self.selected_idx < len(RESOLUTIONS) - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
            return True

        if btn_a:
            target_res = RESOLUTIONS[self.selected_idx]
            new_p = move_to_resolution(self.rom_path, target_res)
            if new_p:
                self.rom_path = new_p
                self.engine.toast(f"Đã đổi độ phân giải: {pretty_resolution(target_res)}")
            self.close()
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

        row_h = 54
        rw = 420
        rh_ = 96 + row_h * len(RESOLUTIONS)
        rx = (state.SCREEN_W - rw) // 2
        ry = (state.SCREEN_H - rh_) // 2

        engine.fill_rect(rx, ry, rw, rh_, 16, 22, 38, 255)
        engine.draw_rect(rx, ry, rw, rh_, 0, 246, 246, 255, thickness=3)
        engine.fill_rect(rx + 3, ry + 3, rw - 6, 56, 24, 34, 58, 255)
        engine.draw_text(tr("act_res_title"), engine.font_item, rx + rw // 2, ry + 31,
                         0, 246, 246, center_x=True, center_y=True)

        cur_res = resolution_of_path(self.rom_path)
        for r_i, r_folder in enumerate(RESOLUTIONS):
            ry_i = ry + 68 + r_i * row_h
            is_sel = (r_i == self.selected_idx)
            is_cur = (r_folder == cur_res)
            if is_sel:
                engine.fill_rect(rx + 12, ry_i, rw - 24, row_h - 6, 32, 50, 85, 255)
                engine.draw_rect(rx + 12, ry_i, rw - 24, row_h - 6, 0, 246, 246, 255, thickness=2)

            col = (0, 255, 160) if is_cur else (225, 235, 250)
            engine.draw_text(pretty_resolution(r_folder), engine.font_item, rx + 40,
                             ry_i + (row_h - 6) // 2, col[0], col[1], col[2], center_y=True)

            bx = rx + rw - 46
            by = ry_i + (row_h - 6) // 2 - 10
            engine.draw_rect(bx, by, 20, 20, 90, 110, 145, 255, thickness=2)
            if is_cur:
                engine.fill_rect(bx + 5, by + 5, 10, 10, 0, 255, 160, 255)


class TwoColInfoModal(BaseModal):
    """Two-column key-value or guide information dialog."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.title = ""
        self.rows = []
        self.style = "normal"

    def open(self, data=None):
        super().open(data)
        self.title = self.data.get("title", "Thông tin")
        self.rows = self.data.get("rows", [])
        self.style = self.data.get("style", "normal")

    def handle_input(self, inputs):
        if not self.active:
            return False

        if inputs.get("btn_a") or inputs.get("btn_b"):
            self.close()
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 200)

        mw = 760 if self.style == "big" else 680
        mh = 400
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        engine.fill_rect(mx, my, mw, mh, 18, 25, 42, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

        engine.fill_rect(mx + 3, my + 3, mw - 6, 56, 24, 34, 58, 255)
        engine.draw_text(self.title, engine.font_item, mx + mw // 2, my + 31, 0, 246, 246, center_x=True, center_y=True)

        start_y = my + 80
        for idx, row in enumerate(self.rows):
            ry = start_y + idx * 40
            if isinstance(row, (tuple, list)) and len(row) == 2:
                lbl, val = str(row[0]), str(row[1])
                engine.draw_text(lbl, engine.font_sub, mx + 40, ry, 160, 180, 210)
                engine.draw_text(val, engine.font_sub, mx + 260, ry, 255, 255, 255)
            elif isinstance(row, str):
                engine.draw_text(row, engine.font_sub, mx + 40, ry, 220, 235, 255)

        # Close hint
        close_txt = "[B] Đóng" if state.current_lang == "VI" else "[B] Close"
        engine.draw_text(close_txt, engine.font_badge, mx + mw // 2, my + mh - 30, 140, 160, 190, center_x=True, center_y=True)


class StreamLoadingModal(BaseModal):
    """Modal displaying loading status when opening YouTube stream."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.video_data = {}
        self.status_msg = "Đang kết nối YouTube..."
        self.cancelled = False

    def open(self, data=None):
        super().open(data)
        self.video_data = self.data.get("video_data") or {}
        self.status_msg = "Đang phân tích luồng phát video..."
        self.cancelled = False

        def _bg_worker():
            v_id = self.video_data.get("id")
            v_title = self.video_data.get("title", "Video YouTube")
            if not v_id:
                self.close()
                return

            try:
                from ..yt_player import extract_stream_fast
                stream_url, title = extract_stream_fast(v_id)
                if self.cancelled:
                    return

                if stream_url:
                    self.status_msg = "Đang chuyển sang RetroArch..."
                    import json
                    info_path = "/tmp/yt_stream_info.json"
                    with open(info_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "video_id": v_id,
                            "stream_url": stream_url,
                            "title": title or v_title
                        }, f)

                    from ..yt import build_play_command
                    play_cmd = build_play_command(v_id, info_path)
                    with open("/tmp/launch_game.sh", "w", encoding="utf-8") as f:
                        f.write(play_cmd)
                    os.chmod("/tmp/launch_game.sh", 0o755)
                    with open("/tmp/rh_last_screen.txt", "w", encoding="utf-8") as f:
                        f.write("youtube")

                    # Clean handoff to launch.sh
                    self.engine.running = False
                else:
                    self.close()
                    self.engine.toast("Không thể lấy link video (có thể bị chặn vùng hoặc giới hạn độ tuổi)!")
            except Exception as e:
                self.close()
                self.engine.toast(f"Lỗi mở luồng: {e}")

        import threading
        threading.Thread(target=_bg_worker, daemon=True).start()

    def handle_input(self, inputs):
        if not self.active:
            return False

        if inputs.get("btn_b"):
            self.cancelled = True
            self.close()
            self.engine.toast("Đã hủy mở video!")
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        mw = 700
        mh = 270
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        engine.fill_rect(mx, my, mw, mh, 18, 25, 42, 255)
        engine.draw_rect(mx, my, mw, mh, 230, 33, 23, 255, thickness=3)

        # Header
        engine.fill_rect(mx + 3, my + 3, mw - 6, 52, 230, 33, 23, 255)
        engine.draw_text("ĐANG MỞ LUỒNG PHÁT YOUTUBE", engine.font_item, mx + mw // 2, my + 29, 255, 255, 255, center_x=True, center_y=True)

        # Video Title
        v_title = self.video_data.get("title", "Video")
        t_lines = engine.wrap_text_to_width(v_title, engine.font_item, mw - 60, max_lines=2)
        ty = my + 78
        for tl in t_lines:
            engine.draw_text(tl, engine.font_item, mx + 30, ty, 255, 255, 255)
            ty += 28

        # Status text with dots
        dots = "." * (int(time.time() * 2) % 4)
        engine.draw_text(f"▶ {self.status_msg}{dots}", engine.font_badge, mx + 30, my + mh - 50, 0, 230, 255)

        # Cancel button
        engine.draw_footer_btn(mx + mw - 160, my + mh - 58, 42, "B", "Hủy bỏ", btn_color=(255, 75, 75), is_dark_btn=False)
