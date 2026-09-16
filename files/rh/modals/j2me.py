# -*- coding: utf-8 -*-
"""J2ME Java Emulator Status & Installation Modal."""

import threading
from .. import state
from ..paths import SDCARD_PATH
from ..i18n import tr
from ..j2me import (is_j2me_runtime_ready, j2me_missing_parts, runtime_is_stale,
                   install_j2me_emulator)
from ..catalog import scan_all_downloaded_games
from .base import BaseModal


class J2meModal(BaseModal):
    """Status and installer modal for J2ME Java emulator runtime."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.busy = False
        self.pending = False
        self.selected_btn = 0

    def handle_input(self, inputs):
        if not self.active or self.busy:
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
                # Install / Reinstall
                self.busy = True
                self.engine.toast("Đang cài đặt giả lập Java..." if state.current_lang == "VI" else "Installing Java emulator...")
                def _bg_install():
                    ok, msg = install_j2me_emulator()
                    self.busy = False
                    self.engine.toast(msg if msg else ("Cài đặt thành công!" if state.current_lang == "VI" else "Installation complete!"))
                threading.Thread(target=_bg_install, daemon=True).start()
                return True
            else:
                self.close()
                return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

        jw = 780
        jh_ = 420
        jx = (state.SCREEN_W - jw) // 2
        jy = (state.SCREEN_H - jh_) // 2
        engine.fill_rect(jx, jy, jw, jh_, 16, 22, 38, 255)
        engine.draw_rect(jx, jy, jw, jh_, 0, 246, 246, 255, thickness=3)
        engine.fill_rect(jx + 3, jy + 3, jw - 6, 54, 24, 34, 58, 255)
        engine.draw_text(tr("j2me_info_title"), engine.font_item, jx + jw // 2, jy + 30,
                         0, 246, 246, center_x=True, center_y=True)

        missing = j2me_missing_parts()
        if self.busy:
            st_txt, st_col = tr("j2me_st_installing"), (255, 200, 0)
        elif missing:
            st_txt, st_col = f"{tr('j2me_st_missing')} {', '.join(missing)}", (255, 90, 90)
        elif runtime_is_stale():
            st_txt, st_col = tr("j2me_st_stale"), (255, 200, 0)
        else:
            st_txt, st_col = tr("j2me_st_ready"), (0, 255, 160)

        sy = jy + 78
        engine.fill_rect(jx + 22, sy - 6, jw - 44, 40, 22, 30, 48, 255)
        engine.draw_rect(jx + 22, sy - 6, jw - 44, 40, st_col[0], st_col[1], st_col[2], 200, thickness=2)
        engine.draw_text(st_txt, engine.font_sub, jx + 40, sy + 14, st_col[0], st_col[1], st_col[2], center_y=True)

        downloaded_games_list = scan_all_downloaded_games()
        n_java = len([g for g in downloaded_games_list if g.get("sys_code") == "JAVA"])
        for r_i, (lbl, val) in enumerate((
                (tr("j2me_row_games"), str(n_java)),
                (tr("j2me_row_emu"), f"{SDCARD_PATH}/Emus/JAVA/"),
                (tr("j2me_row_rom"), f"{SDCARD_PATH}/Roms/JAVA/"))):
            ry_j = jy + 150 + r_i * 42
            engine.draw_text(lbl, engine.font_sub, jx + 44, ry_j, 150, 165, 195)
            engine.draw_text(val, engine.font_sub, jx + 290, ry_j, 225, 235, 250)

        ay = jy + jh_ - 74
        bh = 52
        gap = 20
        bw = (jw - 44 - gap) // 2
        for b_i, (b_txt, b_col, b_on) in enumerate((
                (tr("j2me_do_install"), (255, 200, 0), not self.busy),
                (tr("j2me_do_close"), (180, 200, 230), not self.busy))):
            bx_j = jx + 22 + b_i * (bw + gap)
            is_sel = (b_i == self.selected_btn)
            col = b_col if b_on else (110, 120, 140)
            engine.fill_rect(bx_j, ay, bw, bh, 24, 34, 58, 255)
            engine.draw_rect(bx_j, ay, bw, bh, 0 if is_sel else col[0], 246 if is_sel else col[1], 246 if is_sel else col[2], 255, thickness=3 if is_sel else 1)
            engine.draw_text(b_txt, engine.font_sub, bx_j + bw // 2, ay + bh // 2,
                             col[0], col[1], col[2], center_x=True, center_y=True)
