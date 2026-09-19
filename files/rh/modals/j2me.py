# -*- coding: utf-8 -*-
"""J2ME Java Emulator Status, Settings & Installation Modal."""

import os
import threading
from .. import state
from ..paths import SDCARD_PATH
from ..i18n import tr
from ..j2me import (
    is_j2me_runtime_ready,
    j2me_missing_parts,
    runtime_is_stale,
    install_j2me_emulator,
    RENDER_MODES,
    DEFAULT_RENDER_MODE,
    load_render_mode,
    save_render_mode,
    PHONE_MODES,
    DEFAULT_PHONE_MODE,
    load_default_phone_mode,
    save_default_phone_mode,
)
from ..catalog import scan_all_downloaded_games
from .base import BaseModal


RENDER_LABELS = {
    "VI": {
        "hq": "HQ (Nét cao)",
        "smooth": "Smooth (Mịn)",
        "pixel": "Pixel (1:1)",
    },
    "EN": {
        "hq": "HQ (Default)",
        "smooth": "Smooth",
        "pixel": "Pixel (1:1)",
    }
}

RENDER_HINTS = {
    "VI": {
        "hq": "HQ: Cân bằng sắc nét & tỷ lệ chuẩn của game Java.",
        "smooth": "Smooth: Lấp đầy màn hình, khử răng cưa mượt mà.",
        "pixel": "Pixel: Tỷ lệ gốc 1:1, viền đen sắc nét từng điểm ảnh.",
    },
    "EN": {
        "hq": "HQ: Sharp rendering with balanced aspect ratio.",
        "smooth": "Smooth: Fullscreen stretch with anti-aliasing.",
        "pixel": "Pixel: 1:1 pixel-perfect native scale with borders.",
    }
}

PHONE_LABELS = {
    "VI": {
        "N": "Nokia N (Chuẩn game)",
        "P": "Phím số (2/4/6/8)",
        "E": "Sony Ericsson",
        "S": "Siemens",
        "M": "Motorola",
    },
    "EN": {
        "N": "Nokia N (GameAction)",
        "P": "Numeric (2/4/6/8)",
        "E": "Sony Ericsson",
        "S": "Siemens",
        "M": "Motorola",
    }
}

PHONE_HINTS = {
    "VI": {
        "N": "Nokia N: Chuẩn cho game Java (D-pad di chuyển, nút bấm hành động).",
        "P": "Phím số P: D-pad gán 2/4/6/8, nút A gán 5 (game bàn phím số cổ).",
        "E": "Sony Ericsson: Tương thích bản phát hành cho dòng máy Sony Ericsson.",
        "S": "Siemens: Tương thích bản phát hành cho dòng máy Siemens.",
        "M": "Motorola: Tương thích bản phát hành cho dòng máy Motorola.",
    },
    "EN": {
        "N": "Nokia N: Standard for Java games (D-pad + Action keys).",
        "P": "Numeric P: D-pad mapped to 2/4/6/8, A mapped to 5.",
        "E": "Sony Ericsson: Profile for Sony Ericsson releases.",
        "S": "Siemens: Profile for Siemens keypad devices.",
        "M": "Motorola: Profile for Motorola phone models.",
    }
}


class J2meModal(BaseModal):
    """Status, settings and installer modal for J2ME Java emulator runtime."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.busy = False
        self.selected_row = 0   # 0: render_mode, 1: phone_mode, 2: bottom buttons
        self.selected_btn = 0   # 0: Reinstall, 1: Close
        self.render_mode = DEFAULT_RENDER_MODE
        self.phone_mode = DEFAULT_PHONE_MODE

    def on_open(self, params=None):
        self.render_mode = load_render_mode()
        self.phone_mode = load_default_phone_mode()
        self.selected_row = 0 if is_j2me_runtime_ready() else 2
        self.selected_btn = 0
        self.busy = False

    def _do_install(self):
        if self.busy:
            return
        self.busy = True
        vi = (state.current_lang == "VI")
        if self.engine:
            self.engine.toast("Đang cài đặt giả lập Java..." if vi else "Installing Java emulator...")

        def _bg_install():
            ok, msg = install_j2me_emulator(force=True)
            self.busy = False
            if self.engine:
                default_done = "Cài đặt thành công!" if vi else "Installation complete!"
                self.engine.toast(msg if msg else default_done)

        threading.Thread(target=_bg_install, daemon=True).start()

    def handle_input(self, inputs):
        if not self.active or self.busy:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        if btn_b:
            self.close()
            return True

        if btn_x:
            self._do_install()
            return True

        is_inst = is_j2me_runtime_ready()
        vi = (state.current_lang == "VI")

        if is_inst:
            if btn_up:
                self.selected_row = max(0, self.selected_row - 1)
                return True
            elif btn_down:
                self.selected_row = min(2, self.selected_row + 1)
                return True

            if self.selected_row == 0:
                # Render Mode row
                if btn_left or btn_right or btn_a:
                    step = -1 if btn_left else 1
                    try:
                        cur_i = RENDER_MODES.index(self.render_mode)
                    except ValueError:
                        cur_i = 0
                    self.render_mode = RENDER_MODES[(cur_i + step) % len(RENDER_MODES)]
                    save_render_mode(self.render_mode)
                    if self.engine:
                        self.engine.toast(tr("j2me_render_saved"))
                    return True

            elif self.selected_row == 1:
                # Phone Profile row
                if btn_left or btn_right or btn_a:
                    step = -1 if btn_left else 1
                    try:
                        cur_i = PHONE_MODES.index(self.phone_mode)
                    except ValueError:
                        cur_i = 0
                    self.phone_mode = PHONE_MODES[(cur_i + step) % len(PHONE_MODES)]
                    save_default_phone_mode(self.phone_mode)
                    if self.engine:
                        self.engine.toast("Đã lưu chế độ máy" if vi else "Saved phone profile")
                    return True

            elif self.selected_row == 2:
                # Bottom Buttons row
                if btn_left or btn_right:
                    self.selected_btn = 1 - self.selected_btn
                    return True
                if btn_a:
                    if self.selected_btn == 0:
                        self._do_install()
                    else:
                        self.close()
                    return True

        else:
            # Not ready/installed: focus bottom buttons directly
            if btn_left or btn_right:
                self.selected_btn = 1 - self.selected_btn
                return True
            if btn_a:
                if self.selected_btn == 0:
                    self._do_install()
                else:
                    self.close()
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

        jw = 780
        jh_ = 450
        jx = (state.SCREEN_W - jw) // 2
        jy = (state.SCREEN_H - jh_) // 2

        # Dialog Box
        engine.fill_rect(jx, jy, jw, jh_, 16, 22, 38, 255)
        engine.draw_rect(jx, jy, jw, jh_, 0, 246, 246, 255, thickness=3)

        # Title Bar
        engine.fill_rect(jx + 3, jy + 3, jw - 6, 52, 24, 34, 58, 255)
        vi = (state.current_lang == "VI")
        title_txt = "CÀI ĐẶT GIẢ LẬP JAVA" if vi else "JAVA EMULATOR SETTINGS"
        engine.draw_text(title_txt, engine.font_item, jx + jw // 2, jy + 29,
                         0, 246, 246, center_x=True, center_y=True)

        # Status Banner
        missing = j2me_missing_parts()
        if self.busy:
            st_txt, st_col = tr("j2me_st_installing"), (255, 200, 0)
        elif missing:
            st_txt, st_col = f"{tr('j2me_st_missing')} {', '.join(missing)}", (255, 90, 90)
        elif runtime_is_stale():
            st_txt, st_col = tr("j2me_st_stale"), (255, 200, 0)
        else:
            st_txt, st_col = ("✓ Giả lập Java đã sẵn sàng hoạt động" if vi
                              else "✓ Java emulator is ready to play"), (0, 255, 160)

        sy = jy + 68
        engine.fill_rect(jx + 22, sy - 6, jw - 44, 38, 22, 30, 48, 255)
        engine.draw_rect(jx + 22, sy - 6, jw - 44, 38, st_col[0], st_col[1], st_col[2], 200, thickness=1)
        engine.draw_text(st_txt, engine.font_sub, jx + 36, sy + 13, st_col[0], st_col[1], st_col[2], center_y=True)

        lang_key = "VI" if vi else "EN"
        is_inst = is_j2me_runtime_ready()

        # Settings Options / Information Rows
        row_w = jw - 44
        row_h = 44
        row_x = jx + 22

        # 1. Render Mode row
        r0_y = jy + 114
        row_h = 42
        is_sel_0 = (self.selected_row == 0 and is_inst)
        if is_sel_0:
            engine.fill_rect(row_x, r0_y, row_w, row_h, 30, 48, 80, 255)
            engine.draw_rect(row_x, r0_y, row_w, row_h, 0, 246, 246, 255, thickness=2)
        else:
            engine.fill_rect(row_x, r0_y, row_w, row_h, 20, 28, 48, 255)
            engine.draw_rect(row_x, r0_y, row_w, row_h, 45, 60, 90, 255, thickness=1)

        r_label = RENDER_LABELS[lang_key].get(self.render_mode, self.render_mode)
        lbl_render = "Kiểu hiển thị:" if vi else "Display Mode:"
        engine.draw_text(lbl_render, engine.font_sub, row_x + 16, r0_y + row_h // 2,
                         190, 210, 235, center_y=True, max_w=280)
        engine.draw_text(f"◀  {r_label}  ▶",
                         engine.font_sub, row_x + row_w - 18, r0_y + row_h // 2,
                         0, 246, 246 if is_sel_0 else 200, right_align=True, center_y=True, max_w=380)

        # 2. Phone Profile row
        r1_y = r0_y + row_h + 8
        is_sel_1 = (self.selected_row == 1 and is_inst)
        if is_sel_1:
            engine.fill_rect(row_x, r1_y, row_w, row_h, 30, 48, 80, 255)
            engine.draw_rect(row_x, r1_y, row_w, row_h, 0, 246, 246, 255, thickness=2)
        else:
            engine.fill_rect(row_x, r1_y, row_w, row_h, 20, 28, 48, 255)
            engine.draw_rect(row_x, r1_y, row_w, row_h, 45, 60, 90, 255, thickness=1)

        p_label = PHONE_LABELS[lang_key].get(self.phone_mode, self.phone_mode)
        lbl_phone = "Bàn phím mặc định:" if vi else "Default Keypad:"
        engine.draw_text(lbl_phone, engine.font_sub, row_x + 16, r1_y + row_h // 2,
                         190, 210, 235, center_y=True, max_w=280)
        engine.draw_text(f"◀  {p_label}  ▶",
                         engine.font_sub, row_x + row_w - 18, r1_y + row_h // 2,
                         0, 246, 246 if is_sel_1 else 200, right_align=True, center_y=True, max_w=380)

        # Contextual Description Hint Box
        hint_y = r1_y + row_h + 8
        if is_sel_0:
            cur_hint = RENDER_HINTS[lang_key].get(self.render_mode, "")
            hint_col = (0, 246, 246)
        elif is_sel_1:
            cur_hint = PHONE_HINTS[lang_key].get(self.phone_mode, "")
            hint_col = (0, 246, 246)
        else:
            cur_hint = ("Mẹo: Dùng D-pad Trái/Phải để đổi nhanh thiết lập." if vi
                        else "Tip: Use D-pad Left/Right to quickly switch settings.")
            hint_col = (150, 175, 205)

        engine.fill_rect(row_x, hint_y, row_w, 30, 14, 20, 34, 230)
        engine.draw_rect(row_x, hint_y, row_w, 30, 40, 55, 80, 200, thickness=1)
        engine.draw_text(cur_hint, engine.font_badge, row_x + 12, hint_y + 15,
                         hint_col[0], hint_col[1], hint_col[2], center_y=True, max_w=row_w - 24)

        # 3. Informational Rows (ROMs & Shortcuts)
        downloaded_games_list = scan_all_downloaded_games()
        n_java = len([g for g in downloaded_games_list if g.get("sys_code") == "JAVA"])

        info_y = hint_y + 38
        engine.draw_text(f"• Thư mục ROM: {SDCARD_PATH}/Roms/JAVA/ ({n_java} trò chơi)" if vi
                         else f"• ROMs Directory: {SDCARD_PATH}/Roms/JAVA/ ({n_java} games)",
                         engine.font_badge, row_x + 8, info_y, 140, 160, 190, max_w=row_w - 16)

        engine.draw_text("• Phím tắt khi chơi: START+SELECT (Đổi nút) • START+R3 (Kiểu hiển thị)" if vi
                         else "• In-game shortcuts: START+SELECT (Profile) • START+R3 (Display)",
                         engine.font_badge, row_x + 8, info_y + 22, 120, 145, 175, max_w=row_w - 16)

        # 4. Bottom Action Buttons
        ay = jy + jh_ - 70
        bh = 50
        gap = 20
        bw = (jw - 44 - gap) // 2

        btn_install_txt = tr("j2me_do_install") if missing else ("Cài lại (X)" if vi else "Reinstall (X)")
        btn_close_txt = tr("j2me_do_close")

        btn_specs = [
            (btn_install_txt, (255, 200, 0), not self.busy),
            (btn_close_txt, (180, 200, 230), not self.busy),
        ]

        for b_i, (b_txt, b_col, b_on) in enumerate(btn_specs):
            bx_j = jx + 22 + b_i * (bw + gap)
            is_sel = (self.selected_row == 2 and b_i == self.selected_btn)
            col = b_col if b_on else (110, 120, 140)

            if is_sel:
                engine.fill_rect(bx_j, ay, bw, bh, 34, 52, 88, 255)
                engine.draw_rect(bx_j, ay, bw, bh, 0, 246, 246, 255, thickness=3)
            else:
                engine.fill_rect(bx_j, ay, bw, bh, 24, 34, 58, 255)
                engine.draw_rect(bx_j, ay, bw, bh, col[0], col[1], col[2], 180, thickness=1)

            engine.draw_text(b_txt, engine.font_sub, bx_j + bw // 2, ay + bh // 2,
                             col[0], col[1], col[2], center_x=True, center_y=True)
