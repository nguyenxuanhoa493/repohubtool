# -*- coding: utf-8 -*-
"""Full-screen Game Details & Action Modal."""

import os
import time
import threading
from .. import state
from ..paths import SDCARD_PATH
from ..i18n import tr
from ..storage import human_bytes
from ..catalog import clean_game_title
from ..cheat_manager import has_cheat_file, check_or_download_single_cheat
from ..boxart_scraper import scrape_boxart_for_single_rom
from ..j2me import (resolution_of_path, pretty_resolution,
                   DEFAULT_PHONE_MODE, load_default_phone_mode)
from ..emulators import resolve as resolve_emulator
from .base import BaseModal


def _act_ids(sys_code):
    """Action button layout per system."""
    if sys_code == "JAVA":
        return ["PLAY", "RES", "GET_BOXART", "REGET", "DEL", "CLOSE"]
    return ["PLAY", "PLAY_CHEAT", "GET_CHEAT", "GET_BOXART", "NETPLAY", "REGET", "DEL", "CLOSE"]


class GameActionModal(BaseModal):
    """Full-screen game information & action dashboard modal."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.selected_opt = 0
        self.game_info = None
        self.sys_code = ""
        self.rom_path = ""
        self.img_path = ""
        self.on_launch_cb = None
        self.on_delete_cb = None
        self.on_netplay_cb = None
        self.on_res_cb = None

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

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

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
                self.engine.toast("Đang tải Cheat Code..." if state.current_lang == "VI" else "Downloading Cheats...")
                def _bg_cheat():
                    ok, msg = check_or_download_single_cheat(self.sys_code, fname, g_title)
                    self.engine.toast(msg)
                threading.Thread(target=_bg_cheat, daemon=True).start()
                return True
            elif act_id == "GET_BOXART":
                fname = self.game_info.get("filename", "")
                g_title = self.game_info.get("title", "")
                self.engine.toast("Đang tải ảnh bìa..." if state.current_lang == "VI" else "Scraping Boxart...")
                def _bg_boxart():
                    ok, res = scrape_boxart_for_single_rom(self.sys_code, fname, g_title)
                    if ok:
                        self.img_path = res
                        self.engine.toast("Đã tải xong ảnh bìa!" if state.current_lang == "VI" else "Boxart downloaded!")
                    else:
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
                self.close()
                # Re-download trigger
                from ..downloader import enqueue_download, start_next_queued
                d_url = self.game_info.get("download_url")
                if d_url:
                    enqueue_download(self.game_info, self.sys_code)
                    start_next_queued()
                    self.engine.toast(tr("dl_queue_next"))
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        # Full-Screen Modal Overlay
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 13, 17, 28, 255)

        head_h = 58
        engine.fill_rect(0, 0, state.SCREEN_W, head_h, 20, 28, 48, 255)
        engine.fill_rect(0, head_h - 2, state.SCREEN_W, 2, 0, 246, 246, 255)

        header_str = tr("act_modal_title")
        engine.draw_text(header_str, engine.font_title, 28, head_h // 2, 0, 246, 246, center_y=True)

        g_title = clean_game_title(self.game_info.get("title") or "Game")
        disp_gt = f"[{self.sys_code}] {g_title}"
        if len(disp_gt) > 34:
            disp_gt = disp_gt[:31] + "..."
        gt_w = engine.measure_text(disp_gt, engine.font_badge)
        engine.draw_text(disp_gt, engine.font_badge, state.SCREEN_W - 28 - gt_w, head_h // 2, 255, 215, 0, center_y=True)

        foot_h = 50
        fy = state.SCREEN_H - foot_h
        engine.fill_rect(0, fy, state.SCREEN_W, foot_h, 16, 22, 36, 255)
        engine.fill_rect(0, fy, state.SCREEN_W, 1, 40, 55, 85, 255)

        fx = 32
        fx = engine.draw_footer_btn(fx, fy, foot_h, "◄►▲▼", "Chọn hành động" if state.current_lang == "VI" else "Navigate", (70, 95, 140), is_dark_btn=False)
        fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Thực hiện" if state.current_lang == "VI" else "Confirm", (0, 230, 150))
        engine.draw_footer_btn(state.SCREEN_W - 165, fy, foot_h, "B", "Quay lại" if state.current_lang == "VI" else "Back", (255, 70, 70), is_dark_btn=False)

        # Body Layout
        body_y = head_h + 14
        body_h = fy - body_y - 12
        pad_x = 28
        gap_col = 20

        left_w = int((state.SCREEN_W - pad_x * 2 - gap_col) * 0.38)
        right_w = (state.SCREEN_W - pad_x * 2 - gap_col) - left_w
        left_x = pad_x
        right_x = left_x + left_w + gap_col

        # 1. Left Card: Boxart Preview
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

        # 2. Right Card: Info Top + Actions Grid
        fname = self.game_info.get("filename", "")
        rom_p = self.rom_path or os.path.join(SDCARD_PATH, "Roms", self.sys_code, fname)
        f_size_str = "--"
        if os.path.exists(rom_p):
            f_size_str = human_bytes(os.path.getsize(rom_p))

        info_h = 100
        engine.fill_rect(right_x, body_y, right_w, info_h, 18, 25, 42, 255)
        engine.draw_rect(right_x, body_y, right_w, info_h, 45, 60, 95, 255, thickness=1)

        engine.draw_text(f"• Tệp tin: {fname[:40]}", engine.font_sub, right_x + 16, body_y + 16, 200, 215, 235)
        engine.draw_text(f"• Dung lượng: {f_size_str}", engine.font_sub, right_x + 16, body_y + 44, 0, 230, 255)
        engine.draw_text(f"• Hệ máy: {self.sys_code}", engine.font_sub, right_x + 16, body_y + 72, 255, 215, 0)

        grid_y = body_y + info_h + 14
        grid_h = body_h - info_h - 14

        has_cheat = has_cheat_file(self.sys_code, fname)
        cheat_col = (0, 230, 120) if has_cheat else (255, 215, 0)
        cheat_lbl = ("Đã có Cheat" if state.current_lang == "VI" else "Cheat Ready") if has_cheat else tr("act_get_cheat_title")

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
        tile_h = (grid_h - (rows - 1) * gap_y) // rows

        for t_idx, (act_id, t_title, t_col) in enumerate(actions):
            r_idx = t_idx // cols
            c_idx = t_idx % cols
            tx = right_x + c_idx * (tile_w + gap_x)
            ty = grid_y + r_idx * (tile_h + gap_y)
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
