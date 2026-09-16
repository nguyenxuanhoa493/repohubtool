# -*- coding: utf-8 -*-
"""Alphabet Quick-Jump Modal (0-9, A-Z)."""

from .. import state
from ..i18n import tr
from .base import BaseModal


class AlphabetModal(BaseModal):
    """Grid modal for quick-jumping to games starting with a specific letter."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.letters = ["0-9"] + [chr(c) for c in range(ord('A'), ord('Z') + 1)]
        self.selected_idx = 0
        self.available_map = set()
        self.counts_map = {}
        self.on_select_cb = None

    def open(self, data=None):
        super().open(data)
        self.selected_idx = 0
        self.available_map = self.data.get("available_map", set())
        self.counts_map = self.data.get("counts_map", {})
        self.on_select_cb = self.data.get("on_select")

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        cols = 9
        total = len(self.letters)

        if btn_b:
            self.close()
            return True

        if btn_up:
            if self.selected_idx >= cols:
                self.selected_idx -= cols
            else:
                target = self.selected_idx + ((total - 1 - self.selected_idx) // cols) * cols
                if target >= total:
                    target -= cols
                self.selected_idx = max(0, target)
            return True
        elif btn_down:
            if self.selected_idx + cols < total:
                self.selected_idx += cols
            else:
                self.selected_idx = self.selected_idx % cols
            return True
        elif btn_left:
            if self.selected_idx > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = total - 1
            return True
        elif btn_right:
            if self.selected_idx < total - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
            return True

        if btn_a:
            let = self.letters[self.selected_idx]
            self.close()
            if self.on_select_cb:
                self.on_select_cb(let)
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

        mw = min(920, state.SCREEN_W - 40)
        mh = 420
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

        # Header Bar
        engine.fill_rect(mx + 3, my + 3, mw - 6, 68, 24, 34, 58, 255)
        engine.draw_text(tr("alpha_title"), engine.font_item, mx + mw // 2, my + 36, 0, 246, 246, center_x=True, center_y=True)

        # Subtitle guide
        engine.draw_text(tr("alpha_sub"), engine.font_sub, mx + mw // 2, my + 95, 170, 185, 210, center_x=True, center_y=True)

        # 3 Rows x 9 Columns Letter Grid
        cols = 9
        gap = 8
        grid_pad_x = 30
        cw = (mw - grid_pad_x * 2 - (cols - 1) * gap) // cols
        ch = 62
        grid_y = my + 120

        for idx, let in enumerate(self.letters):
            r = idx // cols
            c = idx % cols
            bx = mx + grid_pad_x + c * (cw + gap)
            by = grid_y + r * (ch + gap)

            is_sel = (idx == self.selected_idx)
            has_games = (let in self.available_map)
            cnt = self.counts_map.get(let, 0)

            if is_sel:
                engine.fill_rect(bx, by, cw, ch, 255, 180, 0, 255)
                engine.draw_rect(bx, by, cw, ch, 255, 255, 255, 255, thickness=3)
                engine.draw_text(let, engine.font_item, bx + cw // 2, by + ch // 2 - 10, 0, 0, 0, center_x=True, center_y=True)
                engine.draw_text(f"{cnt}", engine.font_badge, bx + cw // 2, by + ch // 2 + 14, 0, 0, 0, center_x=True, center_y=True)
            elif has_games:
                engine.fill_rect(bx, by, cw, ch, 24, 38, 62, 255)
                engine.draw_rect(bx, by, cw, ch, 0, 210, 245, 255, thickness=1)
                engine.draw_text(let, engine.font_item, bx + cw // 2, by + ch // 2 - 10, 0, 246, 246, center_x=True, center_y=True)
                engine.draw_text(f"{cnt}", engine.font_badge, bx + cw // 2, by + ch // 2 + 14, 180, 220, 255, center_x=True, center_y=True)
            else:
                engine.fill_rect(bx, by, cw, ch, 18, 24, 36, 180)
                engine.draw_rect(bx, by, cw, ch, 40, 50, 70, 255, thickness=1)
                engine.draw_text(let, engine.font_item, bx + cw // 2, by + ch // 2, 80, 95, 115, center_x=True, center_y=True)

        # Bottom summary line
        sel_let = self.letters[self.selected_idx]
        sel_cnt = self.counts_map.get(sel_let, 0)
        engine.fill_rect(mx + 30, my + mh - 54, mw - 60, 36, 20, 28, 48, 255)
        engine.draw_rect(mx + 30, my + mh - 54, mw - 60, 36, 60, 85, 130, 255)
        if sel_cnt > 0:
            sum_txt = f"Chữ '{sel_let}': {sel_cnt} game trong hệ máy" if state.current_lang == "VI" else f"Letter '{sel_let}': {sel_cnt} games in system"
            engine.draw_text(sum_txt, engine.font_sub, mx + mw // 2, my + mh - 36, 255, 215, 0, center_x=True, center_y=True)
        else:
            sum_txt = f"Chữ '{sel_let}': Không có game nào" if state.current_lang == "VI" else f"Letter '{sel_let}': No games available"
            engine.draw_text(sum_txt, engine.font_sub, mx + mw // 2, my + mh - 36, 140, 155, 175, center_x=True, center_y=True)
