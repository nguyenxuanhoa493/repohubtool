# -*- coding: utf-8 -*-
"""Popup bao dang chuan bi phat YouTube (dung chung cho man chi tiet va hang cho).

Viec trich stream URL chay trong tien trinh yt_player sau khi app da thoat, nen
popup nay la thu duy nhat cho nguoi dung biet dang cho gi thay vi man hinh tat.
"""

from .base import BaseModal
from ..i18n import tr
from .. import state

class YtLoadingModal(BaseModal):
    """Popup bao dang chuan bi phat - khung hinh cuoi truoc khi app thoat.
    Viec trich stream URL chay trong tien trinh yt_player sau khi app da thoat, nen
    khong co popup nay nguoi dung chi thay man hinh tat roi doi vai giay ma khong
    biet app con chay hay da treo.
    """
    def __init__(self, engine=None):
        super().__init__(engine)
        self.video = {}
        self.pos = ""
    def open(self, data=None):
        super().open(data)
        data = data or {}
        self.video = data.get("video") or {}
        pos, total = data.get("position") or 0, data.get("total") or 1
        self.pos = ("%d/%d" % (pos, total)) if pos else ""
    def render(self, engine):
        if not self.active:
            return
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)
        w = min(780, state.SCREEN_W - 80)
        h = 200
        x = (state.SCREEN_W - w) // 2
        y = (state.SCREEN_H - h) // 2
        engine.fill_rect(x, y, w, h, 18, 25, 42, 255)
        engine.draw_rect(x, y, w, h, 0, 246, 246, 255, thickness=2)
        engine.draw_text(tr("yt_play_preparing"), engine.font_title, x + 28, y + 52, 0, 246, 246)
        if self.pos:
            engine.draw_text("%s %s" % (tr("yt_queue_title"), self.pos),
                             engine.font_sub, x + 28, y + 104, 255, 215, 0)
        title = self.video.get("title", "")
        if title:
            engine.draw_text(title[:70], engine.font_footer, x + 28, y + 146, 190, 210, 235)
