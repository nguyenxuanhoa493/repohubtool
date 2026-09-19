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
    """Exit confirmation dialog with background service management."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.selected_idx = 0
        self.services = []
        self.btn_selected = 0  # 0: Thoát, 1: Hủy

    def open(self, data=None):
        super().open(data)
        from ..sysinfo import is_ssh_running, is_sftpgo_running, is_gameweb_running, is_streamer_running
        self.services = []
        vi = state.current_lang == "VI"
        
        if is_ssh_running():
            self.services.append({
                "id": "ssh",
                "title": "SSH Server (Cổng 22)" if vi else "SSH Server (Port 22)",
                "stop": True
            })
        if is_sftpgo_running():
            self.services.append({
                "id": "sftp",
                "title": "SFTPGo (Web: 8080 / Port: 2022)" if vi else "SFTPGo (Web 8080 / Port 2022)",
                "stop": True
            })
        if is_gameweb_running():
            self.services.append({
                "id": "web",
                "title": "RetroHub AI / Web (Cổng 8888)" if vi else "RetroHub AI / Web (Port 8888)",
                "stop": True
            })
        if is_streamer_running():
            self.services.append({
                "id": "stream",
                "title": "Stream màn hình (Cổng 8088)" if vi else "Screen Streamer (Port 8088)",
                "stop": True
            })

        self.selected_idx = 0
        self.btn_selected = 0

    def _apply_services_and_exit(self):
        from ..services import stop_ssh, stop_sftpgo, stop_gameweb, stop_streamer
        for svc in self.services:
            if svc.get("stop"):
                s_id = svc.get("id")
                if s_id == "ssh":
                    stop_ssh()
                elif s_id == "sftp":
                    stop_sftpgo()
                elif s_id == "web":
                    stop_gameweb()
                elif s_id == "stream":
                    stop_streamer()
        # Dong qua engine de active_modal duoc xoa, khong de modal cu nam lai;
        # roi moi dat co thoat de vong lap ket thuc ngay, khong ve them khung nao.
        self._dismiss()
        if self.engine:
            self.engine.running = False

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        num_services = len(self.services)

        if btn_b:
            self._dismiss()
            return True

        if btn_a:
            self._apply_services_and_exit()
            return True

        num_services = len(self.services)
        if num_services > 0:
            if btn_up:
                self.selected_idx = (self.selected_idx - 1) % num_services
                return True
            if btn_down:
                self.selected_idx = (self.selected_idx + 1) % num_services
                return True
            if btn_x or btn_left or btn_right:
                svc = self.services[self.selected_idx]
                svc["stop"] = not svc.get("stop", True)
                return True

        return True

    def _dismiss(self):
        """Close through the engine so active_modal is cleared, not left stale."""
        if self.engine:
            self.engine.close_modal()
        else:
            self.close()

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        vi = state.current_lang == "VI"
        num_services = len(self.services)

        if num_services > 0:
            mw = 840
            mh = min(600, 200 + num_services * 74)
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            # Container
            engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

            # Header
            head_h = 54
            engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 2, 22, 32, 54, 255)
            engine.fill_rect(mx + 2, my + head_h, mw - 4, 2, 0, 246, 246, 255)
            title = "THOÁT ỨNG DỤNG & QUẢN LÝ DỊCH VỤ" if vi else "EXIT & SERVICES MANAGEMENT"
            engine.draw_text(title, engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

            # Sub-desc with breathing room
            sub_msg = "Bấm (X) để Bật (ON) / Tắt (OFF) dịch vụ chạy nền khi thoát:" if vi else "Press (X) to toggle background services ON / OFF on exit:"
            engine.draw_text(sub_msg, engine.font_sub, mx + 28, my + head_h + 22, 195, 215, 235)

            # Services List with increased top margin, row height and gap
            sy = my + head_h + 70
            row_h = 58
            row_gap = 14

            for idx, svc in enumerate(self.services):
                ry = sy + idx * (row_h + row_gap)
                is_row_sel = (self.selected_idx == idx)
                is_stop = svc.get("stop", True)

                # Row Background
                if is_row_sel:
                    engine.fill_rect(mx + 24, ry, mw - 48, row_h, 30, 48, 80, 255)
                    engine.draw_rect(mx + 24, ry, mw - 48, row_h, 0, 246, 246, 255, thickness=2)
                    engine.fill_rect(mx + 26, ry + 4, 6, row_h - 8, 0, 246, 246, 255)
                else:
                    engine.fill_rect(mx + 24, ry, mw - 48, row_h, 20, 28, 48, 255)
                    engine.draw_rect(mx + 24, ry, mw - 48, row_h, 45, 60, 95, 255, thickness=1)

                # Service Title
                engine.draw_text(svc["title"], engine.font_item, mx + 46, ry + row_h // 2, 255, 255, 255, center_y=True)

                # Compact Badge Toggle: OFF (Red) vs ON (Cyan/Green)
                bw = 80
                bh = 34
                bx = mx + mw - 24 - bw - 16
                by = ry + (row_h - bh) // 2

                if is_stop:
                    # OFF badge (Stop on exit)
                    engine.fill_rect(bx, by, bw, bh, 56, 20, 24, 255)
                    engine.draw_rect(bx, by, bw, bh, 255, 75, 75, 255, thickness=1)
                    engine.draw_text("OFF", engine.font_badge, bx + bw // 2, by + bh // 2, 255, 120, 120, center_x=True, center_y=True)
                else:
                    # ON badge (Keep running in background)
                    engine.fill_rect(bx, by, bw, bh, 14, 48, 38, 255)
                    engine.draw_rect(bx, by, bw, bh, 0, 230, 150, 255, thickness=1)
                    engine.draw_text("ON", engine.font_badge, bx + bw // 2, by + bh // 2, 0, 255, 160, center_x=True, center_y=True)

            # Bottom Action Bar (Clear key mapping guidance)
            foot_y = my + mh - 64
            engine.fill_rect(mx + 2, foot_y, mw - 4, 62, 14, 20, 34, 255)
            engine.fill_rect(mx + 2, foot_y, mw - 4, 1, 40, 56, 88, 255)

            btn_w = 236
            btn_h = 44
            by = foot_y + 9

            # Action: [A] Thoát ứng dụng
            bx0 = mx + 24
            engine.fill_rect(bx0, by, btn_w, btn_h, 56, 20, 24, 255)
            engine.draw_rect(bx0, by, btn_w, btn_h, 255, 75, 75, 255, thickness=1)
            btn0_txt = "[A] Thoát ứng dụng" if vi else "[A] Exit RetroHub"
            engine.draw_text(btn0_txt, engine.font_badge, bx0 + btn_w // 2, by + btn_h // 2, 255, 220, 220, center_x=True, center_y=True)

            # Action: [X] Bật/Tắt (ON/OFF)
            bx_mid = mx + (mw - btn_w) // 2
            engine.fill_rect(bx_mid, by, btn_w, btn_h, 20, 40, 65, 255)
            engine.draw_rect(bx_mid, by, btn_w, btn_h, 0, 246, 246, 255, thickness=1)
            btn_x_txt = "[X] Đổi ON / OFF" if vi else "[X] Toggle ON / OFF"
            engine.draw_text(btn_x_txt, engine.font_badge, bx_mid + btn_w // 2, by + btn_h // 2, 0, 246, 246, center_x=True, center_y=True)

            # Action: [B] Hủy / Ở lại
            bx1 = mx + mw - 24 - btn_w
            engine.fill_rect(bx1, by, btn_w, btn_h, 24, 32, 48, 255)
            engine.draw_rect(bx1, by, btn_w, btn_h, 80, 110, 150, 255, thickness=1)
            btn1_txt = "[B] Hủy / Ở lại" if vi else "[B] Cancel / Stay"
            engine.draw_text(btn1_txt, engine.font_badge, bx1 + btn_w // 2, by + btn_h // 2, 200, 215, 235, center_x=True, center_y=True)

        else:
            # Simple confirmation when no services are running
            mw = 620
            mh = 240
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

            title = "THOÁT RETROHUB?" if vi else "EXIT RETROHUB?"
            engine.draw_text(title, engine.font_title, mx + mw // 2, my + 42, 255, 215, 0, center_x=True, center_y=True)

            msg = "Bạn có chắc chắn muốn quay về giao diện chính?" if vi else "Are you sure you want to return to system menu?"
            engine.draw_text(msg, engine.font_sub, mx + mw // 2, my + 92, 200, 215, 235, center_x=True, center_y=True)

            btn_w = 210
            btn_h = 44
            by = my + mh - 66

            # Button 0: Thoát
            bx0 = mx + 60
            engine.fill_rect(bx0, by, btn_w, btn_h, 56, 20, 24, 255)
            engine.draw_rect(bx0, by, btn_w, btn_h, 255, 75, 75, 255, thickness=1)
            btn0_txt = "[A] Thoát" if vi else "[A] Exit"
            engine.draw_text(btn0_txt, engine.font_badge, bx0 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)

            # Button 1: Hủy
            bx1 = mx + mw - 60 - btn_w
            engine.fill_rect(bx1, by, btn_w, btn_h, 24, 32, 48, 255)
            engine.draw_rect(bx1, by, btn_w, btn_h, 80, 110, 150, 255, thickness=1)
            btn1_txt = "[B] Hủy / Ở lại" if vi else "[B] Cancel"
            engine.draw_text(btn1_txt, engine.font_badge, bx1 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)


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
    """Modern card-based two-column / guide information dialog with auto-height and scroll."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.title = ""
        self.rows = []
        self.style = "normal"
        self.scroll_top = 0
        self.selected_idx = 0

    def open(self, data=None):
        super().open(data)
        self.title = (self.data.get("title") or "THÔNG TIN HƯỚNG DẪN").upper()
        self.rows = self.data.get("rows", [])
        self.style = self.data.get("style", "normal")
        self.scroll_top = 0
        self.selected_idx = 0

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")

        if btn_b or btn_a:
            self.close()
            return True

        num_rows = len(self.rows)
        vis_limit = 4 if state.SCREEN_H >= 600 else 3
        if btn_up:
            if self.selected_idx > 0:
                self.selected_idx -= 1
                if self.selected_idx < self.scroll_top:
                    self.scroll_top = self.selected_idx
                return True
        elif btn_down:
            if self.selected_idx < num_rows - 1:
                self.selected_idx += 1
                if self.selected_idx >= self.scroll_top + vis_limit:
                    self.scroll_top = self.selected_idx - vis_limit + 1
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        # Dim backdrop
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        head_h = 58
        foot_h = 48
        card_h = 82
        card_gap = 10
        num_rows = len(self.rows)
        vis_limit = 4 if state.SCREEN_H >= 600 else 3
        vis_rows = max(1, min(num_rows, vis_limit))

        # Responsive Dimensions
        mw = min(state.SCREEN_W - 64, 940)
        content_h = vis_rows * (card_h + card_gap) - card_gap
        mh = head_h + foot_h + 28 + content_h

        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 14, 20, 34, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text(self.title, engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        # Rows Container
        disp_slice = self.rows[self.scroll_top : self.scroll_top + vis_rows]
        start_y = my + head_h + 14
        cx = mx + 24
        cw = mw - 48

        for rel_i, row in enumerate(disp_slice):
            real_i = self.scroll_top + rel_i
            cy = start_y + rel_i * (card_h + card_gap)
            is_sel = (real_i == self.selected_idx) and (num_rows > vis_limit)

            # Card background & border
            engine.fill_rect(cx, cy, cw, card_h, 24 if is_sel else 18, 36 if is_sel else 26, 56 if is_sel else 44, 255)
            engine.draw_rect(cx, cy, cw, card_h, 0 if is_sel else 40, 246 if is_sel else 56, 246 if is_sel else 88, 255, thickness=2 if is_sel else 1)
            # Left accent stripe
            engine.fill_rect(cx + 2, cy + 2, 4, card_h - 4, 0 if is_sel else 255, 246 if is_sel else 215, 246 if is_sel else 0, 255)

            if isinstance(row, (tuple, list)) and len(row) == 2:
                lbl, val = str(row[0]), str(row[1])

                # Label text
                engine.draw_text(lbl, engine.font_badge, cx + 18, cy + 20, 185, 210, 245, center_y=True)

                # Hero Value Box
                bx = cx + 18
                by = cy + 38
                bw = cw - 36
                bh = 34
                engine.fill_rect(bx, by, bw, bh, 10, 15, 26, 255)
                engine.draw_rect(bx, by, bw, bh, 255 if is_sel else 55, 215 if is_sel else 75, 0 if is_sel else 115, 255, thickness=1)

                # Format Value Color
                val_col = (255, 220, 0) if ("http" in val or "ssh " in val or "IP:" in val) else (255, 255, 255)
                # Trim if exceptionally long
                disp_val = val
                if len(disp_val) > 70:
                    disp_val = disp_val[:67] + "..."
                engine.draw_text(disp_val, engine.font_sub, bx + 14, by + bh // 2, val_col[0], val_col[1], val_col[2], center_y=True)

            elif isinstance(row, str):
                engine.draw_text(row, engine.font_sub, cx + 18, cy + card_h // 2, 230, 240, 255, center_y=True)

        # Scrollbar if overflow
        if num_rows > vis_limit:
            sb_x = mx + mw - 14
            sb_y = start_y
            sb_h = content_h
            engine.fill_rect(sb_x, sb_y, 4, sb_h, 25, 35, 55, 255)
            thumb_h = max(20, int(sb_h * (vis_limit / num_rows)))
            thumb_y = sb_y + int((sb_h - thumb_h) * (self.scroll_top / (num_rows - vis_limit)))
            engine.fill_rect(sb_x, thumb_y, 4, thumb_h, 0, 246, 246, 255)

        # Footer Bar
        fy = my + mh - foot_h
        engine.fill_rect(mx + 2, fy, mw - 4, foot_h - 2, 16, 22, 36, 255)
        engine.fill_rect(mx + 2, fy, mw - 4, 1, 38, 52, 80, 255)

        fx = mx + 24
        if num_rows > vis_limit:
            fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "▲▼", "Cuộn xem" if state.current_lang == "VI" else "Scroll", (70, 95, 140), is_dark_btn=False)
        engine.draw_footer_btn(mx + mw - 165, fy, foot_h - 2, "B", "Đóng" if state.current_lang == "VI" else "Close", (255, 75, 75), is_dark_btn=False)


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


class RetroHubWebModal(BaseModal):
    """Modal to manage and view RetroHub Web status."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.ip = "127.0.0.1"
        self.is_running = False

    def open(self, data=None):
        super().open(data)
        from ..services import is_gameweb_running, toggle_gameweb, get_ip
        self.ip = get_ip()
        self.is_running = is_gameweb_running()
        if not self.is_running:
            toggle_gameweb()
            self.is_running = is_gameweb_running()

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

        if btn_b:
            self.close()
            return True

        if btn_a:
            from ..services import toggle_gameweb, is_gameweb_running
            msg = toggle_gameweb()
            self.is_running = is_gameweb_running()
            if self.engine:
                self.engine.toast(msg)
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        # Dim backdrop
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        vi = state.current_lang == "VI"
        
        head_h = 58
        foot_h = 48
        
        mw = min(state.SCREEN_W - 64, 820)
        mh = 320 # Compact height

        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 14, 20, 34, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text("RETROHUB AI", engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        # Content Area
        cx = mx + 24
        cw = mw - 48
        
        # 1. Row: Just the HUGE IP Address
        cy = my + head_h + 16
        card1_h = 80
        engine.fill_rect(cx, cy, cw, card1_h, 18, 26, 44, 255)
        engine.draw_rect(cx, cy, cw, card1_h, 40, 56, 88, 255, thickness=1)
        
        # Accent stripe
        stripe_col = (0, 230, 150) if self.is_running else (255, 75, 75)
        engine.fill_rect(cx + 2, cy + 2, 4, card1_h - 4, stripe_col[0], stripe_col[1], stripe_col[2], 255)

        ip_url = f"http://{self.ip}:8888" if self.is_running else ("Dịch vụ đang tắt" if vi else "Service is stopped")
        ip_col = (255, 220, 0) if self.is_running else (150, 150, 150)
        
        # IP text huge! Centered perfectly inside card
        font_ip = engine.font_huge if self.is_running else engine.font_item
        engine.draw_text(ip_url, font_ip, cx + cw // 2, cy + card1_h // 2, ip_col[0], ip_col[1], ip_col[2], center_x=True, center_y=True)

        # 2. Row: Connect Info Compact
        cy += card1_h + 12
        card2_h = 80
        engine.fill_rect(cx, cy, cw, card2_h, 18, 26, 44, 255)
        engine.draw_rect(cx, cy, cw, card2_h, 40, 56, 88, 255, thickness=1)
        
        lbl_conn = "Cách kết nối:" if vi else "How to Connect:"
        val_conn_1 = "Mở trình duyệt trên máy tính," if vi else "Open a browser on PC or phone"
        val_conn_2 = "hoặc điện thoại chung mạng Wi-Fi" if vi else "connected to the same Wi-Fi"
        
        engine.draw_text(lbl_conn, engine.font_badge, cx + 18, cy + card2_h // 2, 185, 210, 245, center_y=True)
        engine.draw_text(val_conn_1, engine.font_sub, cx + 185, cy + 28, 255, 255, 255, center_y=True)
        engine.draw_text(val_conn_2, engine.font_sub, cx + 185, cy + 56, 255, 255, 255, center_y=True)

        # Footer Bar
        fy = my + mh - foot_h
        engine.fill_rect(mx + 2, fy, mw - 4, foot_h - 2, 16, 22, 36, 255)
        engine.fill_rect(mx + 2, fy, mw - 4, 1, 38, 52, 80, 255)

        fx = mx + 24
        toggle_label = "Tắt dịch vụ" if self.is_running else "Bật dịch vụ"
        if not vi:
            toggle_label = "Stop Web" if self.is_running else "Start Web"
        btn_col = (255, 75, 75) if self.is_running else (0, 230, 150)
        
        fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "A", toggle_label, btn_col, is_dark_btn=False)

        # Close button B (Yellow)
        engine.draw_footer_btn(mx + mw - 145, fy, foot_h - 2, "B", "Đóng" if vi else "Close", btn_color=(255, 220, 0), text_color=(255, 255, 255), is_dark_btn=True)


class BoxartScraperModal(BaseModal):
    """High-speed Boxart scraper progress and live status dialog."""

    def __init__(self, engine=None):
        super().__init__(engine)

    def open(self, data=None):
        super().open(data)
        from ..boxart_scraper import scraper_runner, scan_missing_boxarts
        if not scraper_runner.is_running():
            missing = scan_missing_boxarts()
            if missing:
                scraper_runner.start(missing)
            else:
                scraper_runner.status_msg = tr("scrape_no_missing")
                scraper_runner.done = True

    def handle_input(self, inputs):
        if not self.active:
            return False

        from ..boxart_scraper import scraper_runner
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")

        if scraper_runner.is_running():
            if btn_b or btn_x:
                scraper_runner.request_stop()
                if self.engine:
                    self.engine.toast("Đang dừng cào ảnh..." if state.current_lang == "VI" else "Stopping scrape...")
                return True
        else:
            if btn_a or btn_b or btn_x:
                self.close()
                if self.engine:
                    self.engine.toast(tr("scrape_done_toast"))
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        from ..boxart_scraper import scraper_runner
        # Dim backdrop
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        mw = min(880, state.SCREEN_W - 60)
        mh = 380
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        head_h = 58
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text(tr("scrape_modal_title"), engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        tot = scraper_runner.total
        comp = scraper_runner.completed
        succ = scraper_runner.success_count
        pct = scraper_runner.progress_pct

        vi = state.current_lang == "VI"
        if tot == 0 and not scraper_runner.is_running():
            info_line = tr("scrape_no_missing")
        elif vi:
            info_line = f"Tiến độ: [{comp}/{tot}]   |   Thành công: {succ} ảnh   |   4 luồng song song"
        else:
            info_line = f"Progress: [{comp}/{tot}]   |   Success: {succ} arts   |   4 concurrent workers"

        engine.draw_text(info_line, engine.font_sub, mx + 36, my + head_h + 24, 255, 215, 0)

        # Progress bar track
        pb_x = mx + 36
        pb_y = my + head_h + 60
        pb_w = mw - 72
        pb_h = 36
        engine.fill_rect(pb_x, pb_y, pb_w, pb_h, 24, 34, 56, 255)
        engine.draw_rect(pb_x, pb_y, pb_w, pb_h, 60, 85, 130, 255, thickness=1)

        fill_w = int(pb_w * (pct / 100.0))
        if fill_w > 0:
            engine.fill_rect(pb_x + 2, pb_y + 2, fill_w - 4, pb_h - 4, 0, 230, 150, 255)

        engine.draw_text(f"{pct}%", engine.font_badge, pb_x + pb_w // 2, pb_y + pb_h // 2, 255, 255, 255, center_x=True, center_y=True)

        # Current status text
        cur_t = scraper_runner.current_title
        cur_s = scraper_runner.current_sys
        if scraper_runner.is_running() and cur_t:
            status_txt = f"Đang cào: [{cur_s}] {cur_t}" if vi else f"Scraping: [{cur_s}] {cur_t}"
        else:
            status_txt = scraper_runner.status_msg or (tr("scrape_no_missing") if tot == 0 else "Hoàn tất")

        lines = engine.wrap_text_to_width(status_txt, engine.font_sub, mw - 72, max_lines=2)
        line_y = my + head_h + 116
        for l in lines:
            engine.draw_text(l, engine.font_sub, mx + 36, line_y, 220, 230, 245)
            line_y += 30

        # Footer Button
        foot_h = 52
        fy = my + mh - foot_h - 14
        btn_w = 260
        btn_h = 46
        bx = mx + (mw - btn_w) // 2

        if scraper_runner.is_running():
            engine.fill_rect(bx, fy, btn_w, btn_h, 160, 45, 45, 255)
            engine.draw_rect(bx, fy, btn_w, btn_h, 255, 80, 80, 255, thickness=2)
            btn_lbl = f"[B] {tr('scrape_btn_stop')}"
            engine.draw_text(btn_lbl, engine.font_badge, bx + btn_w // 2, fy + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)
        else:
            engine.fill_rect(bx, fy, btn_w, btn_h, 0, 180, 110, 255)
            engine.draw_rect(bx, fy, btn_w, btn_h, 0, 255, 160, 255, thickness=2)
            btn_lbl = f"[A] {tr('scrape_btn_close')}"
            engine.draw_text(btn_lbl, engine.font_badge, bx + btn_w // 2, fy + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)


class CheatModal(BaseModal):
    """Download and manage Libretro Cheat Codes dialog."""

    def __init__(self, engine=None):
        super().__init__(engine)

    def open(self, data=None):
        super().open(data)
        from ..cheat_manager import cheat_runner
        if not cheat_runner.is_running():
            cheat_runner.start()

    def handle_input(self, inputs):
        if not self.active:
            return False

        from ..cheat_manager import cheat_runner
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")

        if cheat_runner.is_running():
            if btn_b or btn_x:
                cheat_runner.request_stop()
                if self.engine:
                    self.engine.toast("Đang dừng tải Cheat Code..." if state.current_lang == "VI" else "Stopping cheat download...")
                return True
        else:
            if btn_a or btn_b or btn_x:
                self.close()
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        from ..cheat_manager import cheat_runner, count_cheats
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        mw = min(880, state.SCREEN_W - 60)
        mh = 400
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        head_h = 58
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text(tr("cheat_modal_title"), engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        c_st = cheat_runner.get_state()
        pct = c_st.get("progress_pct", 0)

        vi = state.current_lang == "VI"
        cnt = count_cheats()
        info_line = f"Tổng số Cheat hiện có trong máy: {cnt} file .cht" if vi else f"Total Cheats installed on device: {cnt} .cht files"
        engine.draw_text(info_line, engine.font_sub, mx + 36, my + head_h + 20, 255, 215, 0)

        # Progress bar track
        pb_x = mx + 36
        pb_y = my + head_h + 54
        pb_w = mw - 72
        pb_h = 36
        engine.fill_rect(pb_x, pb_y, pb_w, pb_h, 24, 34, 56, 255)
        engine.draw_rect(pb_x, pb_y, pb_w, pb_h, 60, 85, 130, 255, thickness=1)

        fill_w = int(pb_w * (pct / 100.0))
        if fill_w > 0:
            engine.fill_rect(pb_x + 2, pb_y + 2, fill_w - 4, pb_h - 4, 0, 230, 150, 255)

        engine.draw_text(f"{pct}%", engine.font_badge, pb_x + pb_w // 2, pb_y + pb_h // 2, 255, 255, 255, center_x=True, center_y=True)

        # Status and guide text
        status_txt = c_st.get("status_msg") or ("Sẵn sàng" if vi else "Ready")
        engine.draw_text(status_txt, engine.font_sub, mx + 36, my + head_h + 104, 0, 246, 246)

        engine.draw_text(tr("cheat_guide_line1"), engine.font_sub, mx + 36, my + head_h + 138, 210, 220, 240)
        engine.draw_text(tr("cheat_guide_line2"), engine.font_sub, mx + 36, my + head_h + 168, 170, 190, 220)

        # Footer Button
        foot_h = 52
        fy = my + mh - foot_h - 14
        btn_w = 260
        btn_h = 46
        bx = mx + (mw - btn_w) // 2

        if cheat_runner.is_running():
            engine.fill_rect(bx, fy, btn_w, btn_h, 160, 45, 45, 255)
            engine.draw_rect(bx, fy, btn_w, btn_h, 255, 80, 80, 255, thickness=2)
            btn_lbl = f"[B] {tr('cheat_btn_stop')}"
            engine.draw_text(btn_lbl, engine.font_badge, bx + btn_w // 2, fy + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)
        else:
            engine.fill_rect(bx, fy, btn_w, btn_h, 0, 180, 110, 255)
            engine.draw_rect(bx, fy, btn_w, btn_h, 0, 255, 160, 255, thickness=2)
            btn_lbl = f"[A] {tr('cheat_btn_close')}"
            engine.draw_text(btn_lbl, engine.font_badge, bx + btn_w // 2, fy + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)


class SaveManagerModal(BaseModal):
    """Save Game backup and restore manager dialog."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.mode = "menu"  # "menu" or "list"
        self.selected_idx = 0
        self.scroll_top = 0
        self.backups = []

    def open(self, data=None):
        super().open(data)
        self.mode = "menu"
        self.selected_idx = 0
        self.scroll_top = 0
        self.backups = []

    def handle_input(self, inputs):
        if not self.active:
            return False

        from ..save_manager import (get_saves_stats, create_save_backup,
                                   list_save_backups, restore_save_backup,
                                   delete_save_backup)

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")

        if self.mode == "menu":
            if btn_b:
                self.close()
                return True

            if btn_up:
                self.selected_idx = (self.selected_idx - 1) % 2
                return True
            elif btn_down:
                self.selected_idx = (self.selected_idx + 1) % 2
                return True

            if btn_a:
                if self.selected_idx == 0:
                    # Tạo bản sao lưu mới
                    ok, zip_p, st = create_save_backup()
                    if ok:
                        cnt = st.get("total_files", 0)
                        if self.engine:
                            self.engine.toast(f"Đã sao lưu thành công {cnt} file save!" if state.current_lang == "VI" else f"Successfully backed up {cnt} saves!")
                    else:
                        if self.engine:
                            self.engine.toast(str(zip_p))
                elif self.selected_idx == 1:
                    # Xem danh sách bản sao lưu
                    bks = list_save_backups()
                    if not bks:
                        if self.engine:
                            self.engine.toast(tr("save_no_backups"))
                    else:
                        self.backups = bks
                        self.mode = "list"
                        self.selected_idx = 0
                        self.scroll_top = 0
                return True

        elif self.mode == "list":
            if btn_b:
                self.mode = "menu"
                self.selected_idx = 1
                return True

            num_b = len(self.backups)
            if num_b == 0:
                self.mode = "menu"
                return True

            max_vis = 3
            if btn_up:
                if self.selected_idx > 0:
                    self.selected_idx -= 1
                else:
                    self.selected_idx = num_b - 1
                    self.scroll_top = max(0, num_b - max_vis)
                if self.selected_idx < self.scroll_top:
                    self.scroll_top = self.selected_idx
                return True
            elif btn_down:
                if self.selected_idx < num_b - 1:
                    self.selected_idx += 1
                else:
                    self.selected_idx = 0
                    self.scroll_top = 0
                if self.selected_idx >= self.scroll_top + max_vis:
                    self.scroll_top = self.selected_idx - max_vis + 1
                return True

            if btn_a and 0 <= self.selected_idx < num_b:
                sel_bk = self.backups[self.selected_idx]
                ok, restored_cnt, err = restore_save_backup(sel_bk["filepath"])
                if ok:
                    if self.engine:
                        self.engine.toast(f"Đã khôi phục {restored_cnt} file save thành công!" if state.current_lang == "VI" else f"Restored {restored_cnt} save files successfully!")
                    self.close()
                else:
                    if self.engine:
                        self.engine.toast(err or "Lỗi khôi phục save!")
                return True

            if btn_x and 0 <= self.selected_idx < num_b:
                sel_bk = self.backups[self.selected_idx]
                ok, msg = delete_save_backup(sel_bk["filepath"])
                if self.engine:
                    self.engine.toast(msg)
                self.backups = list_save_backups()
                if not self.backups:
                    self.mode = "menu"
                    self.selected_idx = 0
                else:
                    self.selected_idx = min(self.selected_idx, len(self.backups) - 1)
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        from ..save_manager import get_saves_stats

        # Dim backdrop
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        mw = min(920, state.SCREEN_W - 60)
        mh = 450
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        head_h = 58
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text(tr("save_menu_title"), engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        vi = state.current_lang == "VI"

        # ----------------------------------------------------------------------
        # MODE: MENU
        # ----------------------------------------------------------------------
        if self.mode == "menu":
            save_st = get_saves_stats()
            tot_f = save_st.get("total_files", 0)
            tot_mb = save_st.get("total_bytes", 0) / (1024 * 1024)
            sub_info = f"Tìm thấy {tot_f} file save ({tot_mb:.2f} MB) trên thẻ nhớ" if vi else f"Found {tot_f} save files ({tot_mb:.2f} MB) on SD card"
            engine.draw_text(sub_info, engine.font_sub, mx + 36, my + head_h + 20, 255, 215, 0)

            opts = [
                (tr("save_item_backup_now"), "Nén toàn bộ save (.srm, .sav, .state) thành 1 file ZIP an toàn" if vi else "Compress all saves & states into a safe timestamped ZIP"),
                (tr("save_item_list"), "Xem lại các bản sao lưu đã tạo, ngày giờ & khôi phục" if vi else "View existing backup archives, dates & restore")
            ]

            opt_y = my + head_h + 54
            card_w = mw - 72
            card_h = 92
            gap = 14

            for idx, (title_t, desc_t) in enumerate(opts):
                is_sel = (self.selected_idx == idx)
                cy = opt_y + idx * (card_h + gap)

                if is_sel:
                    engine.fill_rect(mx + 36, cy, card_w, card_h, 30, 48, 80, 255)
                    engine.draw_rect(mx + 36, cy, card_w, card_h, 0, 246, 246, 255, thickness=2)
                    engine.fill_rect(mx + 38, cy + 4, 6, card_h - 8, 0, 246, 246, 255)
                    engine.draw_text(title_t, engine.font_item, mx + 58, cy + 28, 255, 255, 255, center_y=True)
                else:
                    engine.fill_rect(mx + 36, cy, card_w, card_h, 20, 28, 48, 255)
                    engine.draw_rect(mx + 36, cy, card_w, card_h, 45, 60, 95, 255, thickness=1)
                    engine.draw_text(title_t, engine.font_item, mx + 58, cy + 28, 210, 225, 245, center_y=True)

                engine.draw_text(desc_t, engine.font_sub, mx + 58, cy + 64, 160, 180, 210, center_y=True)

            # Footer Action Bar
            foot_h = 52
            fy = my + mh - foot_h
            engine.fill_rect(mx + 2, fy, mw - 4, foot_h - 2, 14, 20, 34, 255)
            engine.fill_rect(mx + 2, fy, mw - 4, 1, 40, 56, 88, 255)

            fx = mx + 32
            fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "A", tr("footer_select"), (0, 230, 150), (220, 225, 235), is_dark_btn=True)
            engine.draw_footer_btn(mx + mw - 165, fy, foot_h - 2, "B", "Đóng" if vi else "Close", (255, 75, 75), (220, 225, 235), is_dark_btn=False)

        # ----------------------------------------------------------------------
        # MODE: LIST
        # ----------------------------------------------------------------------
        elif self.mode == "list":
            sub_info = f"Danh sách bản sao lưu ({len(self.backups)} bản):" if vi else f"Backup archives list ({len(self.backups)} files):"
            engine.draw_text(sub_info, engine.font_sub, mx + 36, my + head_h + 18, 255, 215, 0)

            list_y = my + head_h + 46
            card_w = mw - 72
            card_h = 80
            gap = 10
            max_vis = 3

            vis_slice = self.backups[self.scroll_top : self.scroll_top + max_vis]
            for i, b in enumerate(vis_slice):
                actual_idx = self.scroll_top + i
                cy = list_y + i * (card_h + gap)
                is_sel = (self.selected_idx == actual_idx)

                mb_size = b.get("size", 0) / (1024 * 1024)
                size_txt = f"{mb_size:.2f} MB" if mb_size >= 1.0 else f"{b.get('size', 0)/1024:.1f} KB"

                if is_sel:
                    engine.fill_rect(mx + 36, cy, card_w, card_h, 30, 48, 80, 255)
                    engine.draw_rect(mx + 36, cy, card_w, card_h, 0, 246, 246, 255, thickness=2)
                    engine.fill_rect(mx + 38, cy + 4, 6, card_h - 8, 0, 246, 246, 255)
                    engine.draw_text(f"📁 {b['filename']}", engine.font_badge, mx + 56, cy + 24, 0, 246, 246, center_y=True)
                else:
                    engine.fill_rect(mx + 36, cy, card_w, card_h, 20, 28, 48, 255)
                    engine.draw_rect(mx + 36, cy, card_w, card_h, 45, 60, 95, 255, thickness=1)
                    engine.draw_text(f"📁 {b['filename']}", engine.font_badge, mx + 56, cy + 24, 210, 225, 245, center_y=True)

                info_t = f"{b.get('date_str', '')}   |   {b.get('file_count', 0)} files   |   {size_txt}"
                engine.draw_text(info_t, engine.font_sub, mx + 56, cy + 56, 160, 180, 210, center_y=True)

            # Footer Action Bar
            foot_h = 52
            fy = my + mh - foot_h
            engine.fill_rect(mx + 2, fy, mw - 4, foot_h - 2, 14, 20, 34, 255)
            engine.fill_rect(mx + 2, fy, mw - 4, 1, 40, 56, 88, 255)

            fx = mx + 32
            fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "A", "Khôi phục" if vi else "Restore", (0, 230, 150), (220, 225, 235), is_dark_btn=True)
            fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "X", "Xóa bản này" if vi else "Delete", (255, 140, 0), (220, 225, 235), is_dark_btn=True)
            engine.draw_footer_btn(mx + mw - 165, fy, foot_h - 2, "B", "Quay lại" if vi else "Back", (255, 75, 75), (220, 225, 235), is_dark_btn=False)


class SendSshConfirmModal(BaseModal):
    """Confirmation modal before sending SSH connection info via Telegram."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.ip = "127.0.0.1"

    def open(self, data=None):
        super().open(data)
        from ..sysinfo import get_ip
        self.ip = get_ip()

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

        if btn_b:
            self.close()
            return True

        if btn_a:
            self.close()
            if self.engine:
                self.engine.toast("Đang gửi thông tin SSH sang Telegram..." if state.current_lang == "VI" else "Sending SSH info to Telegram...")
            
            from ..services import send_ssh_info_to_telegram
            import threading
            def _bg_send():
                res = send_ssh_info_to_telegram()
                msg = res[1] if isinstance(res, tuple) else res
                if self.engine:
                    self.engine.toast(msg)
            threading.Thread(target=_bg_send, daemon=True).start()
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        vi = state.current_lang == "VI"
        mw = min(state.SCREEN_W - 64, 780)
        mh = 350
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        head_h = 58
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        title = "XÁC NHẬN GỬI SSH QUA TELEGRAM" if vi else "CONFIRM SEND SSH TO TELEGRAM"
        engine.draw_text(title, engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        # Content Card
        cx = mx + 24
        cw = mw - 48
        cy = my + head_h + 16
        card_h = 160

        engine.fill_rect(cx, cy, cw, card_h, 20, 28, 46, 255)
        engine.draw_rect(cx, cy, cw, card_h, 45, 60, 95, 255, thickness=1)
        engine.fill_rect(cx + 2, cy + 2, 4, card_h - 4, 0, 230, 255, 255)

        line1 = "Bạn có chắc chắn muốn gửi thông tin kết nối SSH của máy?" if vi else "Are you sure you want to send SSH connection info to Telegram?"
        engine.draw_text(line1, engine.font_item, cx + 20, cy + 28, 255, 255, 255, center_y=True)

        line2 = f"• Địa chỉ IP: {self.ip}   |   Cổng: 22   |   User: root"
        engine.draw_text(line2, engine.font_badge, cx + 20, cy + 74, 255, 215, 0, center_y=True)

        line3 = "Dữ liệu sẽ được gửi trực tiếp tới Telegram của tác giả để hỗ trợ kết nối từ xa." if vi else "Data will be sent to Telegram for remote debugging assistance."
        engine.draw_text(line3, engine.font_sub, cx + 20, cy + 120, 170, 190, 220, center_y=True)

        # Footer Action Bar
        foot_h = 52
        fy = my + mh - foot_h
        engine.fill_rect(mx + 2, fy, mw - 4, foot_h - 2, 14, 20, 34, 255)
        engine.fill_rect(mx + 2, fy, mw - 4, 1, 40, 56, 88, 255)

        fx = mx + 32
        fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "A", "Xác nhận gửi" if vi else "Confirm Send", (0, 230, 150), (220, 225, 235), is_dark_btn=True)
        engine.draw_footer_btn(mx + mw - 165, fy, foot_h - 2, "B", "Hủy bỏ" if vi else "Cancel", (255, 75, 75), (220, 225, 235), is_dark_btn=False)



