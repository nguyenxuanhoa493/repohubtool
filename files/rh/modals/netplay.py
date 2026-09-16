# -*- coding: utf-8 -*-
"""Netplay Multiplayer Modal (Host / Join via Pinggy & Cloudflare Lobby)."""

import os
import time
import threading
from .. import state
from ..i18n import tr
from ..netplay import (is_netplay_tunnel_running, get_netplay_tunnel_info,
                      start_netplay_tunnel, stop_netplay_tunnel,
                      send_netplay_info_to_telegram, build_netplay_param,
                      find_local_rom_for_netplay, get_my_hosted_room_port)
from ..lobby import fetch_public_rooms, find_room_by_port
from ..emulators import resolve_core_name
from .base import BaseModal


class NetplayModal(BaseModal):
    """Multiplayer online Netplay modal controller."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.mode = "select"  # select, lobby, hosting, numpad
        self.selected_opt = 0
        self.game_info = None
        self.sys_code = ""
        self.rom_path = ""
        self.tunnel_info = None
        self.is_starting = False
        self.lobby_rooms = []
        self.lobby_cursor = 0
        self.lobby_loading = False
        self.lobby_err = None
        self.numpad_code = ""
        self.numpad_cursor = 0
        self.on_launch_cb = None

    def open(self, data=None):
        super().open(data)
        self.mode = "select"
        self.selected_opt = 0
        self.game_info = (self.data.get("game_info") or {}) if isinstance(self.data, dict) else {}
        self.sys_code = self.data.get("sys_code", "") if isinstance(self.data, dict) else ""
        self.rom_path = self.data.get("rom_path", "") if isinstance(self.data, dict) else ""
        self.on_launch_cb = self.data.get("on_launch") if isinstance(self.data, dict) else None
        self.tunnel_info = None
        self.is_starting = False
        self.lobby_rooms = []
        self.lobby_cursor = 0
        self.lobby_loading = False
        self.lobby_err = None
        self.numpad_code = ""
        self.numpad_cursor = 0

    def _direct_launch(self, sys_code, game_info, netplay_param=None):
        from ..emulators import resolve_emulator
        from ..helpers import clean_game_title
        from ..paths import SDCARD_PATH

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
            self.engine.toast("Không tìm thấy file ROM trên thẻ nhớ!" if state.current_lang == "VI" else "ROM file not found on SD card!")
            return

        emu_dir, script_path = resolve_emulator(sys_code)
        if not script_path or not os.path.exists(script_path):
            self.engine.toast(f"Không tìm thấy giả lập cho hệ {sys_code}!" if state.current_lang == "VI" else f"Emulator for {sys_code} not found!")
            return

        title_display = clean_game_title(game_info.get("title", "Game"))
        self.engine.toast(f"Đang khởi động {title_display}..." if state.current_lang == "VI" else f"Launching {title_display}...")

        handoff_script = f"""#!/bin/sh
cd "{emu_dir or os.path.dirname(script_path)}"
"{script_path}" "{rom_p}" {" " + str(netplay_param) if netplay_param else ""}
"""
        try:
            with open("/tmp/launch_game.sh", "w", encoding="utf-8") as f:
                f.write(handoff_script)
            os.chmod("/tmp/launch_game.sh", 0o755)
            with open("/tmp/rh_last_screen.txt", "w", encoding="utf-8") as f:
                f.write("home")
            self.engine.running = False
        except Exception as e:
            self.engine.toast(f"Lỗi khởi động: {e}")

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_y = inputs.get("btn_y")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        if self.mode == "select":
            if btn_b:
                self.close()
                return True
            if btn_left and self.selected_opt > 0:
                self.selected_opt -= 1
                return True
            elif btn_right and self.selected_opt < 2:
                self.selected_opt += 1
                return True
            if btn_a:
                if self.selected_opt == 0:
                    # Host Room
                    if not self.sys_code or not self.game_info or not self.game_info.get("title"):
                        self.engine.toast("Vui lòng vào Thư viện và chọn Game để Tạo phòng Host!" if state.current_lang == "VI" else "Select a Game from Library to Host!")
                        return True
                    self.start_hosting()
                elif self.selected_opt == 1:
                    # Public Lobby
                    self.open_lobby()
                elif self.selected_opt == 2:
                    # Private Code Input
                    self.mode = "numpad"
                    self.numpad_code = ""
                    self.numpad_cursor = 0
                return True

        elif self.mode == "lobby":
            if btn_b:
                self.mode = "select"
                return True
            if btn_y:
                self.open_lobby()
                return True
            if btn_up and self.lobby_cursor > 0:
                self.lobby_cursor -= 1
                return True
            elif btn_down and self.lobby_cursor < len(self.lobby_rooms) - 1:
                self.lobby_cursor += 1
                return True
            if btn_x:
                # Enter code directly or close own room
                my_port = get_my_hosted_room_port()
                if self.lobby_rooms and 0 <= self.lobby_cursor < len(self.lobby_rooms):
                    rm = self.lobby_rooms[self.lobby_cursor]
                    if isinstance(rm, dict) and my_port and str(rm.get("port")) == my_port:
                        stop_netplay_tunnel()
                        self.engine.toast("Đã đóng phòng của bạn!" if state.current_lang == "VI" else "Closed your room!")
                        self.open_lobby()
                        return True
                self.mode = "numpad"
                self.numpad_code = ""
                self.numpad_cursor = 0
                return True
            if btn_a:
                if self.lobby_rooms and 0 <= self.lobby_cursor < len(self.lobby_rooms):
                    rm = self.lobby_rooms[self.lobby_cursor]
                    if isinstance(rm, dict):
                        self.join_room(rm)
                return True

        elif self.mode == "hosting":
            if btn_b:
                stop_netplay_tunnel()
                self.mode = "select"
                self.engine.toast("Đã hủy và đóng phòng Netplay" if state.current_lang == "VI" else "Cancelled and closed Netplay room")
                return True
            if btn_x:
                # Resend Telegram
                t_info = get_netplay_tunnel_info()
                if t_info:
                    threading.Thread(target=lambda: send_netplay_info_to_telegram(
                        t_info.get("port", ""), self.sys_code, self.game_info.get("title", "")), daemon=True).start()
                    self.engine.toast("Đang gửi lại sang Telegram..." if state.current_lang == "VI" else "Resending to Telegram...")
                return True
            if btn_a:
                # Start Game as Host
                t_info = get_netplay_tunnel_info()
                if t_info:
                    netplay_param = build_netplay_param("host", "127.0.0.1", t_info.get("port", ""))
                    self.close()
                    if self.on_launch_cb:
                        self.on_launch_cb(self.sys_code, self.game_info, netplay_param=netplay_param)
                    else:
                        self._direct_launch(self.sys_code, self.game_info, netplay_param=netplay_param)
                return True

        elif self.mode == "numpad":
            if btn_b:
                self.mode = "select"
                return True
            # Numpad grid navigation 3x4 (1-9, C, 0, OK)
            if btn_left and self.numpad_cursor % 3 > 0:
                self.numpad_cursor -= 1
                return True
            elif btn_right and self.numpad_cursor % 3 < 2:
                self.numpad_cursor += 1
                return True
            elif btn_up and self.numpad_cursor >= 3:
                self.numpad_cursor -= 3
                return True
            elif btn_down and self.numpad_cursor + 3 < 12:
                self.numpad_cursor += 3
                return True
            if btn_a:
                keys = ["1","2","3","4","5","6","7","8","9","CLEAR","0","JOIN"]
                k = keys[self.numpad_cursor]
                if k == "CLEAR":
                    self.numpad_code = ""
                elif k == "JOIN":
                    self.submit_numpad_code()
                elif len(self.numpad_code) < 5:
                    self.numpad_code += k
                    if len(self.numpad_code) == 5:
                        self.submit_numpad_code()
                return True

        return True

    def start_hosting(self):
        self.mode = "hosting"
        self.is_starting = True
        self.tunnel_info = None

        def _bg_host():
            info = start_netplay_tunnel()
            self.is_starting = False
            self.tunnel_info = info
            if info:
                p_num = str(info.get("port", ""))
                send_netplay_info_to_telegram(p_num, self.sys_code, self.game_info.get("title", ""))
                self.engine.toast(f"Phòng Netplay đã mở: Mã {p_num}" if state.current_lang == "VI" else f"Netplay room open: Code {p_num}")
            else:
                self.engine.toast("Lỗi mở phòng Netplay!" if state.current_lang == "VI" else "Failed to open Netplay room!")

        threading.Thread(target=_bg_host, daemon=True).start()

    def open_lobby(self):
        self.mode = "lobby"
        self.lobby_loading = True
        self.lobby_err = None
        self.lobby_rooms = []
        self.lobby_cursor = 0

        def _bg_lobby():
            try:
                ok, rooms = fetch_public_rooms(force_refresh=True)
                if ok and isinstance(rooms, list):
                    self.lobby_rooms = rooms
                    self.lobby_err = None
                else:
                    self.lobby_rooms = []
                    self.lobby_err = str(rooms) if rooms else ("Không tải được phòng" if state.current_lang == "VI" else "Failed to fetch rooms")
                self.lobby_loading = False
            except Exception as e:
                self.lobby_rooms = []
                self.lobby_err = str(e)
                self.lobby_loading = False

        threading.Thread(target=_bg_lobby, daemon=True).start()

    def join_room(self, rm):
        if not rm or not isinstance(rm, dict):
            return
        my_port = get_my_hosted_room_port()
        port_str = str(rm.get("port", ""))
        if my_port and port_str == my_port:
            self.engine.toast("Không thể tự kết nối vào phòng của chính mình!" if state.current_lang == "VI" else "Cannot join your own room!")
            return

        h_name = rm.get("host_domain") or "a.pinggy.io"
        sys_c = rm.get("sys_code") or self.sys_code
        g_title = rm.get("game_title", "")

        # Check local ROM
        rom_p, found_sys = find_local_rom_for_netplay(sys_c, g_title)
        if not rom_p:
            self.engine.toast(f"Chưa có ROM '{g_title}'! Vui lòng tải trước." if state.current_lang == "VI" else f"Missing ROM '{g_title}'! Please download first.")
            return

        target_sys = found_sys or sys_c
        target_game = {"title": g_title, "path": rom_p, "sys_code": target_sys}
        netplay_param = build_netplay_param("client", h_name, port_str)

        self.close()
        if self.on_launch_cb:
            self.on_launch_cb(target_sys, target_game, netplay_param=netplay_param)
        else:
            self._direct_launch(target_sys, target_game, netplay_param=netplay_param)

    def submit_numpad_code(self):
        if len(self.numpad_code) < 4:
            self.engine.toast("Mã phòng cần ít nhất 4-5 số!" if state.current_lang == "VI" else "Room code needs 4-5 digits!")
            return

        code_str = self.numpad_code
        self.engine.toast(f"Đang tìm phòng {code_str}..." if state.current_lang == "VI" else f"Searching room {code_str}...")

        def _bg_join():
            rm = find_room_by_port(code_str)
            if not rm:
                self.engine.toast(f"Không tìm thấy phòng {code_str} trên Sảnh!" if state.current_lang == "VI" else f"Room {code_str} not found!")
                return
            self.join_room(rm)

        threading.Thread(target=_bg_join, daemon=True).start()

    def render(self, engine):
        if not self.active:
            return

        mw = state.SCREEN_W
        mh = state.SCREEN_H
        engine.fill_rect(0, 0, mw, mh, 13, 17, 28, 255)

        head_h = 58
        engine.fill_rect(0, 0, mw, head_h, 20, 28, 48, 255)
        engine.fill_rect(0, head_h - 2, mw, 2, 0, 246, 246, 255)

        g_title = (self.game_info.get("title") or "") if isinstance(self.game_info, dict) else ""
        sys_c = self.sys_code or ""
        if g_title and sys_c:
            disp_gt = f"[{sys_c}] {g_title}"
            if len(disp_gt) > 34:
                disp_gt = disp_gt[:31] + "..."
            gt_w = engine.measure_text(disp_gt, engine.font_badge)
            engine.draw_text(disp_gt, engine.font_badge, mw - 28 - gt_w, head_h // 2, 255, 215, 0, center_y=True)

        foot_h = 50
        fy = mh - foot_h
        engine.fill_rect(0, fy, mw, foot_h, 16, 22, 36, 255)
        engine.fill_rect(0, fy, mw, 1, 40, 55, 85, 255)

        if self.mode == "select":
            header_str = "NETPLAY 2 NGƯỜI (INTERNET)" if state.current_lang == "VI" else "2-PLAYER NETPLAY"
            engine.draw_text(header_str, engine.font_title, 28, head_h // 2, 0, 246, 246, center_y=True)

            card_margin = 32
            gap_c = 18
            card_w = (mw - card_margin * 2 - gap_c * 2) // 3
            card_y = 80
            card_h = fy - card_y - 18
            c1_x = card_margin
            c2_x = c1_x + card_w + gap_c
            c3_x = c2_x + card_w + gap_c

            # 3 Cards: Host, Public Lobby, Private Code
            for i, (cx, title_lbl, badge_lbl, sub_lines, b_col) in enumerate([
                (c1_x, "TẠO PHÒNG", "P1 • HOST", ["• Mở server Pinggy", "• Tự đăng lên Sảnh online", "• Báo mã qua Telegram"], (0, 255, 160)),
                (c2_x, "SẢNH ONLINE", "CỘNG ĐỒNG • LOBBY", ["• Xem phòng cộng đồng", "• Tự khớp ROM & Core", "• Bấm [A] vào chơi ngay"], (255, 215, 0)),
                (c3_x, "NHẬP MÃ (P2)", "P2 • RIÊNG TƯ", ["• Nhập mã 5 số từ Host", "• Bàn phím số Numpad ảo", "• Chơi riêng tư bạn bè"], (0, 230, 255)),
            ]):
                is_sel = (self.selected_opt == i)
                engine.fill_rect(cx, card_y, card_w, card_h, 24 if is_sel else 18, 40 if is_sel else 25, 64 if is_sel else 42, 255)
                engine.draw_rect(cx, card_y, card_w, card_h, b_col[0] if is_sel else 38, b_col[1] if is_sel else 52, b_col[2] if is_sel else 80, 255, thickness=3 if is_sel else 1)
                if is_sel:
                    engine.fill_rect(cx + 4, card_y + 4, card_w - 8, 6, b_col[0], b_col[1], b_col[2], 255)

                bw = card_w - 40
                bx = cx + 20
                engine.fill_rect(bx, card_y + 22, bw, 32, 14, 40, 30, 255)
                engine.draw_rect(bx, card_y + 22, bw, 32, b_col[0], b_col[1], b_col[2], 255, thickness=1)
                engine.draw_text(badge_lbl, engine.font_badge, cx + card_w // 2, card_y + 38, b_col[0], b_col[1], b_col[2], center_x=True, center_y=True)

                engine.draw_text(title_lbl, engine.font_item, cx + card_w // 2, card_y + 86, 255, 255, 255, center_x=True, center_y=True)
                engine.fill_rect(cx + 24, card_y + 116, card_w - 48, 1, 45, 60, 95, 255)

                for l_i, l_txt in enumerate(sub_lines):
                    engine.draw_text(l_txt, engine.font_sub, cx + 24, card_y + 144 + l_i * 44, 200, 215, 235)

            fx = 32
            fx = engine.draw_footer_btn(fx, fy, foot_h, "◄►", "Chọn chế độ" if state.current_lang == "VI" else "Select", (70, 95, 140), is_dark_btn=False)
            fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Tiếp tục" if state.current_lang == "VI" else "Continue", (0, 230, 150))
            engine.draw_footer_btn(mw - 165, fy, foot_h, "B", "Bỏ qua" if state.current_lang == "VI" else "Cancel", (255, 70, 70), is_dark_btn=False)

        elif self.mode == "hosting":
            header_str = "TẠO PHÒNG NETPLAY (HOST)" if state.current_lang == "VI" else "HOST NETPLAY"
            engine.draw_text(header_str, engine.font_title, 28, head_h // 2, 0, 246, 246, center_y=True)

            if self.is_starting:
                cx = 40
                cy = 90
                cw = mw - 80
                ch = fy - cy - 20
                engine.fill_rect(cx, cy, cw, ch, 18, 25, 42, 255)
                engine.draw_rect(cx, cy, cw, ch, 0, 246, 246, 255, thickness=2)
                engine.draw_text("ĐANG TẠO ĐƯỜNG TRUYỀN PINGGY QUA INTERNET...", engine.font_item, cx + cw // 2, cy + ch // 2 - 35, 255, 215, 0, center_x=True, center_y=True)
                engine.draw_text("Đang nhận mã phòng & đăng ký lên Sảnh online...", engine.font_sub, cx + cw // 2, cy + ch // 2 + 10, 200, 220, 245, center_x=True, center_y=True)
                engine.draw_footer_btn(mw - 165, fy, foot_h, "B", "Hủy bỏ" if state.current_lang == "VI" else "Cancel", (255, 70, 70), is_dark_btn=False)
            elif self.tunnel_info:
                p_num = str(self.tunnel_info.get("port", "-----"))
                h_name = str(self.tunnel_info.get("host", "a.pinggy.io"))

                bx = 32
                by = 80
                bw = mw - 64
                bh = 175
                engine.fill_rect(bx, by, bw, bh, 22, 30, 52, 255)
                engine.draw_rect(bx, by, bw, bh, 255, 215, 0, 255, thickness=2)
                engine.fill_rect(bx + 2, by + 2, 6, bh - 4, 255, 215, 0, 255)

                engine.draw_text("MÃ PHÒNG CỦA BẠN (GỬI MÃ 5 SỐ NÀY CHO NGƯỜI CHƠI 2):", engine.font_modal_lbl, bx + bw // 2, by + 34, 0, 230, 255, center_x=True, center_y=True)
                engine.draw_text(p_num, engine.font_huge, bx + bw // 2, by + 98, 255, 215, 0, center_x=True, center_y=True)
                engine.draw_text(f"Server: {h_name}  •  Port: 55435", engine.font_sub, bx + bw // 2, by + 146, 170, 190, 220, center_x=True, center_y=True)

                iy = by + bh + 16
                ih = fy - iy - 75
                engine.fill_rect(bx, iy, bw, ih, 18, 25, 42, 255)
                engine.draw_rect(bx, iy, bw, ih, 38, 52, 80, 255, thickness=1)

                core_n = resolve_core_name(sys_c)
                engine.draw_text(f"• Game: [{sys_c}] {g_title[:45]}  |  Core: {core_n or 'Tự động'}", engine.font_sub, bx + 24, iy + 26, 220, 235, 255)
                engine.draw_text("• Trạng thái: Đã đăng lên Sảnh online & gửi Telegram", engine.font_sub, bx + 24, iy + 62, 0, 255, 160)
                engine.draw_text("• Bấm [A] để vào game chờ người chơi 2. KHÔNG bấm [B] vì [B] sẽ hủy phòng!", engine.font_modal_lbl, bx + 24, iy + 98, 255, 215, 0)

                fx = 32
                fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Bắt đầu chơi (Host)", (0, 230, 150))
                fx = engine.draw_footer_btn(fx, fy, foot_h, "X", "Gửi lại Telegram", (0, 190, 255))
                engine.draw_footer_btn(mw - 180, fy, foot_h, "B", "Đóng phòng", (255, 70, 70), is_dark_btn=False)

        elif self.mode == "lobby":
            header_str = "SẢNH CHỜ CỘNG ĐỒNG" if state.current_lang == "VI" else "PUBLIC LOBBY"
            engine.draw_text(header_str, engine.font_title, 28, head_h // 2, 0, 246, 246, center_y=True)

            if self.lobby_loading:
                engine.draw_text("ĐANG TẢI DANH SÁCH PHÒNG TỪ CLOUDFLARE...", engine.font_item, mw // 2, mh // 2, 255, 215, 0, center_x=True, center_y=True)
            elif self.lobby_err:
                engine.draw_text(str(self.lobby_err).upper(), engine.font_item, mw // 2, mh // 2, 255, 100, 100, center_x=True, center_y=True)
            elif not self.lobby_rooms:
                engine.draw_text("HIỆN CHƯA CÓ PHÒNG NETPLAY NÀO ĐANG MỞ", engine.font_item, mw // 2, mh // 2, 255, 215, 0, center_x=True, center_y=True)
            else:
                vis_n = 5
                r_h = 80
                r_gap = 10
                start_ry = 80
                scroll_off = max(0, self.lobby_cursor - vis_n + 1) if self.lobby_cursor >= vis_n else 0
                disp_slice = self.lobby_rooms[scroll_off : scroll_off + vis_n]
                my_np_port = get_my_hosted_room_port()

                for rel_i, rm in enumerate(disp_slice):
                    if not isinstance(rm, dict):
                        continue
                    real_i = scroll_off + rel_i
                    ry = start_ry + rel_i * (r_h + r_gap)
                    rx = 32
                    rw = mw - 64
                    is_r_sel = (real_i == self.lobby_cursor)
                    rm_port = str(rm.get("port", ""))
                    is_my_rm = bool(my_np_port and rm_port == my_np_port)

                    engine.fill_rect(rx, ry, rw, r_h, 28 if is_r_sel else 18, 52 if is_r_sel else 25, 82 if is_r_sel else 42, 255)
                    engine.draw_rect(rx, ry, rw, r_h, 0 if is_r_sel else 35, 246 if is_r_sel else 48, 246 if is_r_sel else 75, 255, thickness=2 if is_r_sel else 1)

                    txt_title = f"[{rm.get('sys_code','')}] {str(rm.get('game_title',''))[:42]}"
                    engine.draw_text(txt_title, engine.font_item, rx + 22, ry + 16, 255, 255, 255)
                    txt_sub = f"Host: {rm.get('player_nick','Host')}  •  Core: {rm.get('core','Auto')}"
                    if is_my_rm:
                        txt_sub += "  [PHÒNG CỦA BẠN - BẤM X ĐỂ ĐÓNG]"
                    engine.draw_text(txt_sub, engine.font_sub, rx + 22, ry + 48, 0, 230, 255)

            fx = 32
            fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Vào chơi", (0, 230, 150))
            fx = engine.draw_footer_btn(fx, fy, foot_h, "Y", "Làm mới", (255, 200, 0))
            engine.draw_footer_btn(mw - 165, fy, foot_h, "B", "Quay lại", (255, 70, 70), is_dark_btn=False)

        elif self.mode == "numpad":
            header_str = "NHẬP MÃ PHÒNG (P2)" if state.current_lang == "VI" else "ENTER ROOM CODE"
            engine.draw_text(header_str, engine.font_title, 28, head_h // 2, 0, 246, 246, center_y=True)

            # Code display box
            bx = (mw - 400) // 2
            by = 90
            bw = 400
            bh = 60
            engine.fill_rect(bx, by, bw, bh, 20, 28, 48, 255)
            engine.draw_rect(bx, by, bw, bh, 0, 230, 255, 255, thickness=2)
            disp_c = self.numpad_code if self.numpad_code else "_____"
            engine.draw_text(disp_c, engine.font_huge, bx + bw // 2, by + bh // 2, 255, 215, 0, center_x=True, center_y=True)

            # 3x4 Numpad keys
            keys = ["1","2","3","4","5","6","7","8","9","CLEAR","0","JOIN"]
            kw = 120
            kh = 52
            kgap = 14
            grid_w = kw * 3 + kgap * 2
            gx = (mw - grid_w) // 2
            gy = by + bh + 24

            for i, k in enumerate(keys):
                r = i // 3
                c = i % 3
                kx = gx + c * (kw + kgap)
                ky = gy + r * (kh + kgap)
                is_sel = (i == self.numpad_cursor)

                engine.fill_rect(kx, ky, kw, kh, 0 if is_sel else 24, 230 if is_sel else 34, 255 if is_sel else 56, 255)
                engine.draw_rect(kx, ky, kw, kh, 255 if is_sel else 45, 255 if is_sel else 65, 255 if is_sel else 100, 255, thickness=2 if is_sel else 1)
                t_col = (0, 20, 40) if is_sel else (255, 255, 255)
                engine.draw_text(k, engine.font_item, kx + kw // 2, ky + kh // 2, t_col[0], t_col[1], t_col[2], center_x=True, center_y=True)

            fx = 32
            fx = engine.draw_footer_btn(fx, fy, foot_h, "A", "Chọn số", (0, 230, 150))
            engine.draw_footer_btn(mw - 165, fy, foot_h, "B", "Quay lại", (255, 70, 70), is_dark_btn=False)
