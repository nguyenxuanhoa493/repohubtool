# -*- coding: utf-8 -*-
"""YouTube playback queue manager.

Shows the current session queue, lets the user play from an item, remove items,
clear the queue, and toggle repeat/shuffle. All edits persist to the session
file so the runner picks them up.
"""

from .. import playback, state
from ..i18n import tr
from ..player import launch_session
from .base import BaseScreen

_REPEAT_CYCLE = ("off", "all", "one")


class QueueScreen(BaseScreen):
    def __init__(self, engine=None):
        super().__init__(engine)
        self.queue = []
        self.sel = 0
        self.scroll = 0
        self.repeat = "off"
        self.shuffle = False

    # ------------------------------------------------------------------
    def on_enter(self, params=None):
        sess = playback.load_session()
        self.queue = list(sess.queue) if sess else []
        self.repeat = sess.repeat if sess else "off"
        self.shuffle = bool(sess.shuffle) if sess else False
        self.sel = sess.index if sess and 0 <= sess.index < len(self.queue) else 0
        self.scroll = 0

    def get_header_title(self):
        return "YouTube - %s (%d)" % (tr("yt_queue_title"), len(self.queue))

    def get_footer_actions(self):
        return [
            ("A", tr("yt_watch_play"), (0, 230, 150), (220, 225, 235), True),
            ("X", tr("yt_queue_remove"), (255, 150, 60), (220, 225, 235), True),
            ("Y", tr("yt_queue_clear"), (255, 75, 75), (220, 225, 235), False),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    # ------------------------------------------------------------------
    def _persist(self):
        sess = playback.load_session()
        if not sess:
            sess = playback.PlaybackSession(queue=[], mode="queue")
        sess.queue = list(self.queue)
        sess.repeat = self.repeat
        sess.shuffle = self.shuffle
        if self.queue:
            sess.index = max(0, min(self.sel, len(self.queue) - 1))
        else:
            sess.index = 0
        playback.save_session(sess)

    def _play(self):
        if not self.queue:
            self.engine.toast(tr("yt_queue_empty"))
            return
        sess = playback.load_session()
        if not sess:
            sess = playback.PlaybackSession(queue=[], mode="queue")
        sess.queue = list(self.queue)
        sess.index = self.sel
        sess.repeat = self.repeat
        sess.shuffle = self.shuffle
        launch_session(self.engine, sess)

    def _remove(self):
        if not self.queue:
            return
        self.queue.pop(self.sel)
        if self.sel >= len(self.queue):
            self.sel = max(0, len(self.queue) - 1)
        self._persist()
        self.engine.toast(tr("yt_queue_removed"))

    def _clear(self):
        self.queue = []
        self.sel = 0
        self._persist()
        self.engine.toast(tr("yt_queue_cleared"))

    def _cycle_repeat(self):
        idx = (_REPEAT_CYCLE.index(self.repeat) + 1) % len(_REPEAT_CYCLE) if self.repeat in _REPEAT_CYCLE else 0
        self.repeat = _REPEAT_CYCLE[idx]
        self._persist()
        self.engine.toast("%s: %s" % (tr("yt_repeat"), self.repeat.upper()))

    def _toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self._persist()
        self.engine.toast("%s: %s" % (tr("yt_shuffle"), tr("yt_on") if self.shuffle else tr("yt_off")))

    # ------------------------------------------------------------------
    def handle_input(self, inputs):
        if inputs.get("btn_b"):
            self.engine.pop_screen()
            return True
        if inputs.get("btn_l1"):
            self._cycle_repeat()
            return True
        if inputs.get("btn_r1"):
            self._toggle_shuffle()
            return True
        if inputs.get("btn_x"):
            self._remove()
            return True
        if inputs.get("btn_y"):
            self._clear()
            return True

        total = len(self.queue)
        if total:
            if inputs.get("btn_up"):
                self.sel = (self.sel - 1) % total
            elif inputs.get("btn_down"):
                self.sel = (self.sel + 1) % total
            elif inputs.get("btn_a"):
                self._play()
                return True

        visible = self._visible_rows()
        if self.sel < self.scroll:
            self.scroll = self.sel
        elif self.sel >= self.scroll + visible:
            self.scroll = self.sel - visible + 1
        return False

    def _visible_rows(self):
        return max(1, (state.SCREEN_H - 56 - 122) // 60)

    # ------------------------------------------------------------------
    def render(self, engine):
        pad = 24
        info_y = 74
        engine.draw_text("%s: %s    %s: %s" % (
            tr("yt_repeat"), self.repeat.upper(),
            tr("yt_shuffle"), tr("yt_on") if self.shuffle else tr("yt_off"),
        ), engine.font_footer, pad, info_y, 150, 175, 205)

        if not self.queue:
            engine.draw_text(tr("yt_queue_empty"), engine.font_item, state.SCREEN_W // 2,
                             state.SCREEN_H // 2, 140, 160, 190, center_x=True, center_y=True)
            return

        list_top = info_y + 40
        row_h = 60
        visible = self._visible_rows()
        rows = self.queue[self.scroll:self.scroll + visible]
        for i, v in enumerate(rows):
            real = self.scroll + i
            ry = list_top + i * row_h
            sel = (real == self.sel)
            if sel:
                engine.fill_rect(pad, ry, state.SCREEN_W - pad * 2, row_h - 10, 28, 44, 75, 255)
                engine.draw_rect(pad, ry, state.SCREEN_W - pad * 2, row_h - 10, 230, 33, 23, 255, thickness=3)
            else:
                engine.fill_rect(pad, ry, state.SCREEN_W - pad * 2, row_h - 10, 19, 26, 42, 255)
                engine.draw_rect(pad, ry, state.SCREEN_W - pad * 2, row_h - 10, 40, 54, 85, 255, thickness=1)
            engine.draw_text(f"{real + 1}.", engine.font_badge, pad + 14, ry + 16, 0, 220, 245)
            title = v.get("disp_title") or v.get("title", "")
            engine.draw_text(title, engine.font_grid_title, pad + 64, ry + 16, 225, 235, 250)
            dur = v.get("duration", "")
            if dur:
                engine.draw_text(dur, engine.font_footer, state.SCREEN_W - pad - 14, ry + 18,
                                 180, 195, 220, right_align=True)
