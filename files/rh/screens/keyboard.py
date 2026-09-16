# -*- coding: utf-8 -*-
"""On-Screen Virtual Keyboard for Text Search."""

import time
from .. import state
from ..i18n import tr
from .base import BaseScreen


class VirtualKeyboardScreen(BaseScreen):
    """Virtual QWERTY keyboard screen for text entry."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.kb_rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", "-"],
            ["Z", "X", "C", "V", "B", "N", "M", ".", "_", "/"],
            ["SPACE", "DEL", "CLEAR", "SEARCH"]
        ]
        self.kb_cursor = [1, 0]  # [row, col]
        self.input_text = ""
        self.title_prompt = ""
        self.on_search_cb = None

    def on_enter(self, params=None):
        params = params or {}
        self.input_text = params.get("initial_text", "")
        self.title_prompt = params.get("prompt", tr("search_prompt"))
        self.on_search_cb = params.get("on_search")
        self.kb_cursor = [1, 0]

    def get_header_title(self):
        return tr("search_title")

    def get_footer_actions(self):
        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
            ("X", tr("footer_search"), (0, 210, 255), (220, 225, 235), True),
            ("Y", "Xóa ký tự", (255, 200, 0), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_y = inputs.get("btn_y")

        r, c = self.kb_cursor

        if btn_b:
            self.engine.pop_screen()
            return True

        if btn_x:
            # Quick Search
            self.submit_search()
            return True

        if btn_y:
            # Quick Delete
            if self.input_text:
                self.input_text = self.input_text[:-1]
            return True

        if btn_up:
            if r > 0:
                self.kb_cursor[0] -= 1
                row_len = len(self.kb_rows[self.kb_cursor[0]])
                if self.kb_cursor[1] >= row_len:
                    self.kb_cursor[1] = row_len - 1
            return True
        elif btn_down:
            if r < len(self.kb_rows) - 1:
                self.kb_cursor[0] += 1
                row_len = len(self.kb_rows[self.kb_cursor[0]])
                if self.kb_cursor[1] >= row_len:
                    self.kb_cursor[1] = row_len - 1
            return True
        elif btn_left:
            if c > 0:
                self.kb_cursor[1] -= 1
            return True
        elif btn_right:
            if c < len(self.kb_rows[r]) - 1:
                self.kb_cursor[1] += 1
            return True

        if btn_a:
            key_str = self.kb_rows[r][c]
            if key_str == "SPACE":
                self.input_text += " "
            elif key_str == "DEL":
                if self.input_text:
                    self.input_text = self.input_text[:-1]
            elif key_str == "CLEAR":
                self.input_text = ""
            elif key_str == "SEARCH":
                self.submit_search()
            else:
                self.input_text += key_str
            return True

        return False

    def submit_search(self):
        cb = self.on_search_cb
        q = self.input_text.strip()
        self.engine.pop_screen()
        if cb:
            cb(q)

    def render(self, engine):
        # 1. Text Input Bar
        box_x = 40
        box_y = 108
        box_w = state.SCREEN_W - 80
        box_h = 58
        engine.fill_rect(box_x, box_y, box_w, box_h, 20, 28, 48, 255)
        engine.draw_rect(box_x, box_y, box_w, box_h, 0, 230, 255, 255, thickness=2)

        cursor_str = "_" if int(time.time() * 2) % 2 == 0 else ""
        disp_query = self.input_text + cursor_str if self.input_text else self.title_prompt + cursor_str
        q_col = (255, 255, 255) if self.input_text else (120, 140, 170)
        engine.draw_text(disp_query, engine.font_item, box_x + 20, box_y + box_h // 2, q_col[0], q_col[1], q_col[2], center_y=True)

        # 2. Virtual Keys
        kb_start_y = box_y + box_h + 16
        k_row_gap = 12
        k_col_gap = 10
        k_h = 56

        for r_idx, row in enumerate(self.kb_rows):
            num_k = len(row)
            total_w = state.SCREEN_W - 80
            k_w = (total_w - (num_k - 1) * k_col_gap) // num_k
            ky = kb_start_y + r_idx * (k_h + k_row_gap)

            for c_idx, key_str in enumerate(row):
                kx = 40 + c_idx * (k_w + k_col_gap)
                is_k_sel = (self.kb_cursor[0] == r_idx and self.kb_cursor[1] == c_idx)

                if is_k_sel:
                    engine.fill_rect(kx, ky, k_w, k_h, 0, 230, 255, 255)
                    engine.draw_rect(kx, ky, k_w, k_h, 255, 255, 255, 255, thickness=2)
                    engine.draw_text(key_str, engine.font_kb, kx + k_w // 2, ky + k_h // 2, 0, 20, 40, center_x=True, center_y=True)
                else:
                    engine.fill_rect(kx, ky, k_w, k_h, 24, 34, 56, 255)
                    engine.draw_rect(kx, ky, k_w, k_h, 45, 65, 100, 255, thickness=1)
                    engine.draw_text(key_str, engine.font_kb, kx + k_w // 2, ky + k_h // 2, 220, 230, 245, center_x=True, center_y=True)
