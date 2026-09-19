# -*- coding: utf-8 -*-
"""Modal doi core gia lap cho tung he (mo tu man Tien ich).

corepicker.list_systems() liet ke cac he co tu 2 cach chay tro len, kem core dang
dung. Modal nay chi hien thi va goi corepicker.set_core() - dung ham ma MainUI
cua may ghi khi chon tay, nen ket qua giong het cach chon core ngoai launcher."""

from .. import corepicker, state
from ..i18n import tr
from .base import BaseModal

ROW_H = 62


class CorePickerModal(BaseModal):
    """Danh sach he may + core, doi bang trai/phai va ap dung bang A."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.rows = []
        self.idx = 0
        self.scroll = 0
        self.opt_idx = {}

    def open(self, data=None):
        super().open(data)
        self._reload()

    def _reload(self):
        self.rows = corepicker.list_systems()
        if self.idx >= len(self.rows):
            self.idx = 0
        self.scroll = 0
        self.opt_idx = {r["code"]: self._current_option_index(r) for r in self.rows}

    @staticmethod
    def _current_option_index(row):
        for i, opt in enumerate(row.get("options") or []):
            if opt.get("launch") == row.get("current_launch"):
                return i
        return 0

    def _visible_rows(self):
        return max(1, (state.SCREEN_H - 260) // ROW_H)

    def handle_input(self, inputs):
        if not self.active:
            return False
        if inputs.get("btn_b"):
            self.close()
            return True
        if not self.rows:
            return True

        row = self.rows[self.idx]
        opts = row.get("options") or []

        if inputs.get("btn_up"):
            self.idx = (self.idx - 1) % len(self.rows)
        elif inputs.get("btn_down"):
            self.idx = (self.idx + 1) % len(self.rows)
        elif inputs.get("btn_left") or inputs.get("btn_l1"):
            if opts:
                self.opt_idx[row["code"]] = (self.opt_idx.get(row["code"], 0) - 1) % len(opts)
        elif inputs.get("btn_right") or inputs.get("btn_r1"):
            if opts:
                self.opt_idx[row["code"]] = (self.opt_idx.get(row["code"], 0) + 1) % len(opts)
        elif inputs.get("btn_a"):
            if opts:
                opt = opts[self.opt_idx.get(row["code"], 0)]
                ok = corepicker.set_core(row["code"], opt["launch"])
                if self.engine:
                    self.engine.toast(tr("core_set_ok").format(name=opt.get("name") or opt["launch"])
                                      if ok else tr("core_set_fail"))
                if ok:
                    self._reload()
            return True

        vis = self._visible_rows()
        if self.idx < self.scroll:
            self.scroll = self.idx
        elif self.idx >= self.scroll + vis:
            self.scroll = self.idx - vis + 1
        return True

    def render(self, engine):
        if not self.active:
            return
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        pad = 40
        w = state.SCREEN_W - pad * 2
        h = state.SCREEN_H - 120
        x, y = pad, 60
        engine.fill_rect(x, y, w, h, 16, 22, 36, 255)
        engine.draw_rect(x, y, w, h, 45, 60, 95, 255, thickness=2)

        engine.draw_text(tr("core_picker_title"), engine.font_title, x + 28, y + 34, 0, 246, 246)
        engine.draw_text(tr("core_picker_hint"), engine.font_footer, x + w - 28, y + 34,
                         150, 175, 205, right_align=True)

        list_y = y + 70
        if not self.rows:
            engine.draw_text(tr("core_picker_empty"), engine.font_sub, x + 28, list_y + 20, 200, 150, 150)
            return

        vis = self._visible_rows()
        for i, row in enumerate(self.rows[self.scroll:self.scroll + vis]):
            real = self.scroll + i
            ry = list_y + i * ROW_H
            sel = (real == self.idx)
            if sel:
                engine.fill_rect(x + 16, ry, w - 32, ROW_H - 8, 28, 44, 75, 255)
                engine.draw_rect(x + 16, ry, w - 32, ROW_H - 8, 0, 246, 246, 255, thickness=2)
            engine.draw_text(row.get("label") or row["code"], engine.font_item, x + 34, ry + 12, 235, 240, 250)
            opts = row.get("options") or []
            if sel and opts:
                cur = opts[self.opt_idx.get(row["code"], 0)]
                engine.draw_text("< %s >" % (cur.get("name") or cur.get("launch")),
                                 engine.font_badge, x + w - 34, ry + 16, 255, 215, 0, right_align=True)
            else:
                engine.draw_text(row.get("current", ""), engine.font_footer,
                                 x + w - 34, ry + 16, 170, 195, 225, right_align=True)

        engine.draw_text(tr("core_picker_footer"), engine.font_footer,
                         x + w // 2, y + h - 26, 170, 195, 225, center_x=True, center_y=True)
