# -*- coding: utf-8 -*-
"""YouTube Watch page: video details, actions and related videos.

Shown before playback instead of handing straight to the player. Play builds a
playback session (see rh.playback) and hands off to the yt_player runner, so
the whole queue keeps playing without returning to the app between videos.
"""

import os
import threading

from .. import playback, state, yt
from ..i18n import tr
from ..paths import YT_CACHE_DIR
from ..player import launch_session
from .base import BaseScreen


class WatchScreen(BaseScreen):
    """Detail page for one video: metadata, actions, related list."""

    ACTIONS = 4  # play, save, add-to-queue, audio-only

    def __init__(self, engine=None):
        super().__init__(engine)
        self.video = {}
        self.video_id = ""
        self.video_title = ""
        self.queue = []
        self.index = 0
        self.context = ""
        self.meta = None
        self.loading = False
        self.related = []
        self.focus = 0
        self.scroll = 0
        self.resume_pos = 0.0
        self.audio_only = False
        self.saved = False            # da luu vao yeu thich (de to vang nut Save)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_enter(self, params=None):
        params = params or {}
        self.video = params.get("video") or {}
        self.video_id = self.video.get("id", "")
        self.video_title = yt.clean_yt_text(self.video.get("title", "YouTube"))
        self.queue = params.get("queue") or [self.video]
        self.index = params.get("index", 0)
        self.context = params.get("context", "")
        self.meta = None
        self.related = []
        self.focus = 0
        self.scroll = 0
        self.audio_only = bool(params.get("audio_only", False))
        self.saved = yt.is_favorite(self.video_id) if self.video_id else False
        dur = playback.duration_seconds(self.video.get("duration", ""))
        self.resume_pos = playback.resume_position(self.video_id, dur)
        self.loading = bool(self.video_id)
        if self.video_id:
            threading.Thread(target=self._bg_fetch, daemon=True).start()

    def _bg_fetch(self):
        try:
            self.meta = yt.fetch_watch_metadata(self.video_id)
        except Exception:
            self.meta = None
        self.related = (self.meta or {}).get("related", []) if self.meta else []
        self.loading = False

    def get_header_title(self):
        return "YouTube - " + (self.video_title[:44] or "Video")

    def get_footer_actions(self):
        return [
            ("A", tr("yt_watch_play"), (0, 230, 150), (220, 225, 235), True),
            ("L/R", tr("yt_nav_buttons"), (70, 95, 140), (220, 225, 235), False),
            ("X", tr("yt_queue_title"), (0, 210, 255), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _start_playback(self):
        queue = self.queue or [self.video]
        sess = playback.PlaybackSession(
            queue=queue,
            index=self.index,
            mode="queue" if len(queue) > 1 else "single",
            context=self.context,
            audio_only=self.audio_only,
        )
        launch_session(self.engine, sess)

    def _toggle_favorite(self):
        favs = yt.load_favorites()
        _, added = yt.toggle_favorite(self.video, favs)
        self.saved = bool(added)
        self.engine.toast(tr("yt_watch_saved") if added else tr("yt_watch_unsaved"))

    def _add_to_queue(self):
        sess = playback.load_session()
        if not sess:
            sess = playback.PlaybackSession(queue=[], mode="queue")
        sess.add(self.video)
        playback.save_session(sess)
        self.engine.toast(tr("yt_watch_queued"))

    def _toggle_audio_only(self):
        self.audio_only = not self.audio_only
        label = tr("yt_on") if self.audio_only else tr("yt_off")
        self.engine.toast(f"{tr('yt_audio_only')}: {label}")

    def _open_related(self, idx):
        if 0 <= idx < len(self.related):
            self.engine.push_screen("watch", {
                "video": self.related[idx],
                "queue": self.related,
                "index": idx,
                "context": self.context,
                "audio_only": self.audio_only,
            })

    def _activate(self):
        if self.focus == 0:
            self._start_playback()
        elif self.focus == 1:
            self._toggle_favorite()
        elif self.focus == 2:
            self._add_to_queue()
        elif self.focus == 3:
            self._toggle_audio_only()
        else:
            self._open_related(self.focus - self.ACTIONS)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_input(self, inputs):
        if inputs.get("btn_b"):
            self.engine.pop_screen()
            return True
        if inputs.get("btn_x"):
            self.engine.push_screen("queue")
            return True

        # L/R di giua cac nut thao tac; len/xuong di trong danh sach video lien quan.
        if inputs.get("btn_r1"):
            self.focus = (self.focus + 1) % max(1, self.ACTIONS)
            return True
        if inputs.get("btn_l1"):
            self.focus = (self.focus - 1) % max(1, self.ACTIONS)
            return True

        total = self.ACTIONS + len(self.related)
        if inputs.get("btn_up"):
            self.focus = self._move_related(-1)
        elif inputs.get("btn_down"):
            self.focus = self._move_related(1)
        elif inputs.get("btn_a"):
            self._activate()
            return True

        visible = self._visible_rows()
        rel = self.focus - self.ACTIONS
        if rel < 0:
            self.scroll = 0
        elif rel < self.scroll:
            self.scroll = rel
        elif rel >= self.scroll + visible:
            self.scroll = rel - visible + 1
        return False

    def _move_related(self, step):
        """Len/xuong trong danh sach video lien quan; tu nut thao tac thi vao dau danh sach."""
        n = len(self.related)
        if not n:
            return self.focus
        rel = self.focus - self.ACTIONS
        if rel < 0:
            return self.ACTIONS
        return self.ACTIONS + max(0, min(n - 1, rel + step))

    def _visible_rows(self):
        return max(1, (state.SCREEN_H - 56 - 456) // 50)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def render(self, engine):
        meta = self.meta or {}
        pad = 24

        # Thumbnail (16:9)
        thumb_w = 456
        thumb_h = 256
        tx, ty = pad, 78
        engine.fill_rect(tx, ty, thumb_w, thumb_h, 18, 25, 42, 255)
        thumb_path = os.path.join(YT_CACHE_DIR, f"{self.video_id}.jpg")
        drawn = False
        if self.video_id and os.path.exists(thumb_path):
            drawn = engine.draw_proportional_boxart(thumb_path, tx, ty, thumb_w, thumb_h)
        if not drawn:
            engine.draw_text("YouTube", engine.font_sub, tx + thumb_w // 2, ty + thumb_h // 2,
                             230, 33, 23, center_x=True, center_y=True)
        dur = self.video.get("duration", "")
        if dur:
            dw = engine.measure_text(dur, engine.font_footer) + 10
            engine.fill_rect(tx + thumb_w - dw - 6, ty + thumb_h - 26, dw, 20, 0, 0, 0, 210)
            engine.draw_text(dur, engine.font_footer, tx + thumb_w - dw // 2 - 6,
                             ty + thumb_h - 16, 255, 255, 255, center_x=True, center_y=True)

        # Metadata column
        mx = tx + thumb_w + 16
        mw = state.SCREEN_W - mx - pad
        my = ty
        title = meta.get("title") or self.video.get("title", "YouTube")
        for line in engine.wrap_text_to_width(title, engine.font_item, mw, max_lines=3):
            engine.draw_text(line, engine.font_item, mx, my, 255, 255, 255)
            my += 30
        channel = meta.get("channel") or self.video.get("channel", "")
        if channel:
            engine.draw_text(channel, engine.font_badge, mx, my + 4, 0, 220, 245)
            my += 32
        views = meta.get("views", "")
        published = meta.get("published", "")
        info_bits = [b for b in (views, published) if b]
        if info_bits:
            engine.draw_text(" • ".join(info_bits), engine.font_footer, mx, my + 4, 150, 170, 200)
            my += 28
        if self.resume_pos > 0:
            watched = f"{tr('yt_watch_watched')} {playback.format_seconds(self.resume_pos)}"
            engine.draw_text(watched, engine.font_footer, mx, my + 4, 255, 200, 90)
            my += 28
        desc = meta.get("description", "")
        if desc:
            engine.draw_text(tr("yt_watch_desc"), engine.font_footer, mx, my + 6, 120, 145, 180)
            my += 26
            for line in engine.wrap_text_to_width(desc, engine.font_footer, mw, max_lines=4):
                engine.draw_text(line, engine.font_footer, mx, my, 160, 180, 205)
                my += 24
        elif self.loading:
            engine.draw_text(tr("yt_watch_loading"), engine.font_footer, mx, my + 6, 140, 160, 190)
        elif self.meta is None:
            engine.draw_text(tr("yt_watch_err"), engine.font_footer, mx, my + 6, 200, 120, 120)

        # Action buttons
        btn_y = ty + thumb_h + 18
        audio_state = tr("yt_on") if self.audio_only else tr("yt_off")
        btn_labels = [
            tr("yt_watch_play"),
            tr("yt_watch_saved_btn") if self.saved else tr("yt_watch_save"),
            tr("yt_watch_queue_add"),
            f"{tr('yt_audio_only')}: {audio_state}",
        ]
        btn_w = 224
        btn_h = 52
        gap = 12
        bx = pad
        for i, label in enumerate(btn_labels):
            sel = (self.focus == i)
            if sel:
                engine.fill_rect(bx, btn_y, btn_w, btn_h, 30, 46, 78, 255)
                engine.draw_rect(bx, btn_y, btn_w, btn_h, 230, 33, 23, 255, thickness=3)
            else:
                engine.fill_rect(bx, btn_y, btn_w, btn_h, 19, 26, 42, 255)
                engine.draw_rect(bx, btn_y, btn_w, btn_h, 40, 54, 85, 255, thickness=1)
            lbl_col = (255, 215, 0) if (i == 1 and self.saved) else (255, 255, 255)
            engine.draw_text(label, engine.font_badge, bx + btn_w // 2, btn_y + btn_h // 2,
                             lbl_col[0], lbl_col[1], lbl_col[2], center_x=True, center_y=True)
            bx += btn_w + gap

        # Related list
        engine.draw_text(tr("yt_watch_related"), engine.font_badge, pad, btn_y + btn_h + 14,
                         0, 220, 245)
        list_top = btn_y + btn_h + 40
        row_h = 50
        visible = self._visible_rows()
        rel = self.related[self.scroll:self.scroll + visible]
        if not rel and self.loading:
            engine.draw_text(tr("yt_watch_loading"), engine.font_footer, pad, list_top + 8, 140, 160, 190)
        for i, rv in enumerate(rel):
            real = self.scroll + i
            ry = list_top + i * row_h
            sel = (self.focus == self.ACTIONS + real)
            if sel:
                engine.fill_rect(pad, ry, state.SCREEN_W - pad * 2, row_h - 8, 28, 44, 75, 255)
                engine.draw_rect(pad, ry, state.SCREEN_W - pad * 2, row_h - 8, 230, 33, 23, 255, thickness=2)
            rt = f"{real + 1}. {rv.get('disp_title') or rv.get('title', '')}"
            engine.draw_text(rt, engine.font_grid_title, pad + 14, ry + 14, 225, 235, 250)
            rd = rv.get("duration", "")
            if rd:
                engine.draw_text(rd, engine.font_footer, state.SCREEN_W - pad - 14, ry + 14,
                                 180, 195, 220, right_align=True)
