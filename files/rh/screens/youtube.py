# -*- coding: utf-8 -*-
"""YouTube Stream Player & Video Grid Screen."""

import os
import time
import threading
from .. import state, yt
from ..paths import YT_CACHE_DIR
from ..i18n import tr
from ..yt_player import play_video
from .base import BaseScreen


class YoutubeScreen(BaseScreen):
    """YouTube 3x2 Grid Browser with background thumbnail caching and stream player handoff."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.mode = "trending"  # trending, search, favorites
        self.videos = []
        self.selected_idx = 0
        self.scroll_row = 0
        self.search_query = ""
        self.recent_queries = []
        self.active_query_idx = 0
        self.loading = False
        self.launching = False

    def build_tabs(self, select_tab: str = None):
        """Build tab list dynamically: puts '★ Yêu thích' first if favorites exist."""
        favs = yt.load_favorites()
        tabs = []
        if favs:
            tabs.append("★ Yêu thích")
        tabs.append("Trending")
        history = yt.load_search_history() or ["Nhạc Trẻ Remix", "Game Retro", "Hoạt Hình"]
        for q in history:
            if q not in ("Trending", "★ Yêu thích", "Yêu thích") and q not in tabs:
                tabs.append(q)
        self.recent_queries = tabs

        if select_tab and select_tab in self.recent_queries:
            self.active_query_idx = self.recent_queries.index(select_tab)
        elif self.active_query_idx >= len(self.recent_queries):
            self.active_query_idx = 0

    def on_enter(self, params=None):
        self.build_tabs()
        self.load_current_tab()

    def load_current_tab(self):
        if not self.recent_queries or self.active_query_idx >= len(self.recent_queries):
            self.active_query_idx = 0
        cur_q = self.recent_queries[self.active_query_idx]
        self.loading = True
        self.videos = []
        self.selected_idx = 0
        self.scroll_row = 0

        def _bg_fetch():
            try:
                if cur_q in ("★ Yêu thích", "Yêu thích"):
                    self.videos = yt.load_favorites() or []
                elif cur_q == "Trending":
                    self.videos = yt.get_trending() or []
                else:
                    cached, _ = yt.load_feed_cache(cur_q)
                    if cached:
                        self.videos = cached
                    else:
                        self.videos = yt.search_youtube(cur_q) or []
            except Exception as e:
                self.engine.toast(f"Lỗi tải YouTube: {e}")
            self.loading = False

            # Background download thumbnails
            def _bg_thumbs():
                for v in self.videos[:18]:
                    v_id = v.get("id")
                    if v_id:
                        yt.fetch_thumbnail(v.get("thumb", ""), YT_CACHE_DIR, v_id)
            threading.Thread(target=_bg_thumbs, daemon=True).start()

        threading.Thread(target=_bg_fetch, daemon=True).start()

    def get_header_title(self):
        cur_q = self.recent_queries[self.active_query_idx] if self.recent_queries else "YouTube"
        return f"YouTube - {cur_q} ({len(self.videos)})"

    def get_footer_actions(self):
        return [
            ("A", "Xem video", (0, 230, 150), (220, 225, 235), True),
            ("X", "Tìm kiếm", (0, 210, 255), (220, 225, 235), True),
            ("Y", "Yêu thích", (255, 200, 0), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_l1 = inputs.get("btn_l1")
        btn_r1 = inputs.get("btn_r1")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")
        btn_y = inputs.get("btn_y")

        if btn_b:
            self.engine.pop_screen()
            return True

        if btn_l1:
            if self.active_query_idx > 0:
                self.active_query_idx -= 1
            else:
                self.active_query_idx = len(self.recent_queries) - 1
            self.load_current_tab()
            return True

        if btn_r1:
            if self.active_query_idx < len(self.recent_queries) - 1:
                self.active_query_idx += 1
            else:
                self.active_query_idx = 0
            self.load_current_tab()
            return True

        # [X] Search Keyboard
        if btn_x:
            def _on_search(query):
                if query:
                    clean_q = yt.clean_yt_text(query.strip())
                    if clean_q:
                        history = yt.load_search_history()
                        if clean_q in history:
                            history.remove(clean_q)
                        history.insert(0, clean_q)
                        yt.save_search_history(history)
                        self.build_tabs(select_tab=clean_q)
                        self.load_current_tab()

            self.engine.push_screen("keyboard", {
                "initial_text": "",
                "prompt": "Nhập từ khóa tìm kiếm...",
                "on_search": _on_search
            })
            return True

        # [Y] Favorite Toggle
        if btn_y:
            if 0 <= self.selected_idx < len(self.videos):
                v = self.videos[self.selected_idx]
                favs = yt.load_favorites()
                new_favs, is_added = yt.toggle_favorite(v, favs)
                action_str = "Đã lưu vào Yêu thích" if is_added else "Đã xóa khỏi Yêu thích"
                clean_t = yt.clean_yt_text(v.get("title", "Video"))
                self.engine.toast(f"{action_str}: {clean_t[:24]}")

                cur_tab = self.recent_queries[self.active_query_idx] if self.active_query_idx < len(self.recent_queries) else "Trending"
                if cur_tab in ("★ Yêu thích", "Yêu thích"):
                    self.videos = new_favs
                    if not new_favs:
                        self.build_tabs()
                        self.active_query_idx = 0
                        self.load_current_tab()
                    else:
                        if self.selected_idx >= len(self.videos):
                            self.selected_idx = max(0, len(self.videos) - 1)
                else:
                    self.build_tabs(select_tab=cur_tab)
            return True

        if self.launching:
            return True

        total_v = len(self.videos)
        if total_v == 0:
            return False

        cols = 3
        rows = 2
        if btn_up:
            if self.selected_idx >= cols:
                self.selected_idx -= cols
            else:
                target = self.selected_idx + ((total_v - 1 - self.selected_idx) // cols) * cols
                if target >= total_v:
                    target -= cols
                self.selected_idx = max(0, target)
            cur_row = self.selected_idx // cols
            if cur_row < self.scroll_row:
                self.scroll_row = cur_row
            elif cur_row >= self.scroll_row + rows:
                self.scroll_row = cur_row - rows + 1
            return True
        elif btn_down:
            if self.selected_idx + cols < total_v:
                self.selected_idx += cols
            else:
                self.selected_idx = self.selected_idx % cols
            cur_row = self.selected_idx // cols
            if cur_row < self.scroll_row:
                self.scroll_row = cur_row
            elif cur_row >= self.scroll_row + rows:
                self.scroll_row = cur_row - rows + 1
            return True
        elif btn_left:
            if self.selected_idx > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = total_v - 1
            cur_row = self.selected_idx // cols
            if cur_row < self.scroll_row:
                self.scroll_row = cur_row
            elif cur_row >= self.scroll_row + rows:
                self.scroll_row = cur_row - rows + 1
            return True
        elif btn_right:
            if self.selected_idx < total_v - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
            cur_row = self.selected_idx // cols
            if cur_row < self.scroll_row:
                self.scroll_row = cur_row
            elif cur_row >= self.scroll_row + rows:
                self.scroll_row = cur_row - rows + 1
            return True

        if btn_a and 0 <= self.selected_idx < total_v:
            v = self.videos[self.selected_idx]
            v_id = v.get("id")
            if v_id:
                from ..modals.common import StreamLoadingModal
                self.engine.open_modal(StreamLoadingModal(self.engine), {
                    "video_data": v
                })
            return True

        return False

    def render(self, engine):
        # 1. Top Bar: Recent queries & Tabs
        tab_h = 38
        tab_y = 64
        engine.fill_rect(0, tab_y, state.SCREEN_W, tab_h, 17, 24, 40, 245)
        engine.fill_rect(0, tab_y + tab_h - 1, state.SCREEN_W, 1, 35, 48, 72, 255)

        engine.draw_text("< L1", engine.font_footer, 20, tab_y + tab_h // 2, 0, 220, 245, center_y=True)
        r1_txt = "R1 >"
        r1_w = engine.measure_text(r1_txt, engine.font_footer)
        engine.draw_text(r1_txt, engine.font_footer, state.SCREEN_W - 20 - r1_w, tab_y + tab_h // 2, 0, 220, 245, center_y=True)

        chip_start_x = 75
        chip_avail_w = state.SCREEN_W - 150
        num_tabs = len(self.recent_queries)
        max_vis_tabs = 6
        tab_scroll = max(0, min(self.active_query_idx - max_vis_tabs // 2, num_tabs - max_vis_tabs)) if num_tabs > max_vis_tabs else 0

        vis_tabs = self.recent_queries[tab_scroll : tab_scroll + max_vis_tabs]
        chip_w = (chip_avail_w - (len(vis_tabs) - 1) * 8) // max(1, len(vis_tabs))

        for i, q_name in enumerate(vis_tabs):
            real_idx = tab_scroll + i
            tx = chip_start_x + i * (chip_w + 8)
            is_tab_sel = (real_idx == self.active_query_idx)
            is_fav_tab = (q_name in ("★ Yêu thích", "Yêu thích"))

            if is_fav_tab:
                if is_tab_sel:
                    engine.fill_rect(tx, tab_y + 4, chip_w, tab_h - 8, 220, 150, 0, 255)
                    engine.draw_text(q_name[:14], engine.font_badge, tx + chip_w // 2, tab_y + tab_h // 2, 255, 255, 255, center_x=True, center_y=True)
                else:
                    engine.fill_rect(tx, tab_y + 5, chip_w, tab_h - 10, 48, 38, 20, 255)
                    engine.draw_text(q_name[:14], engine.font_badge, tx + chip_w // 2, tab_y + tab_h // 2, 255, 215, 0, center_x=True, center_y=True)
            elif is_tab_sel:
                engine.fill_rect(tx, tab_y + 4, chip_w, tab_h - 8, 230, 33, 23, 255)
                engine.draw_text(q_name[:14], engine.font_badge, tx + chip_w // 2, tab_y + tab_h // 2, 255, 255, 255, center_x=True, center_y=True)
            else:
                engine.fill_rect(tx, tab_y + 5, chip_w, tab_h - 10, 25, 35, 55, 255)
                engine.draw_text(q_name[:14], engine.font_badge, tx + chip_w // 2, tab_y + tab_h // 2, 170, 185, 210, center_x=True, center_y=True)

        # 2. Videos Grid Area
        content_y = tab_y + tab_h + 6
        content_h = state.SCREEN_H - content_y - 56

        if self.loading:
            engine.draw_text("ĐANG TẢI DANH SÁCH VIDEO...", engine.font_item, state.SCREEN_W // 2, content_y + content_h // 2, 255, 215, 0, center_x=True, center_y=True)
            return

        if not self.videos:
            cur_tab = self.recent_queries[self.active_query_idx] if self.active_query_idx < len(self.recent_queries) else ""
            msg = "CHƯA CÓ VIDEO YÊU THÍCH (BẤM [Y] ĐỂ THÊM)" if cur_tab in ("★ Yêu thích", "Yêu thích") else "KHÔNG CÓ VIDEO NÀO"
            engine.draw_text(msg, engine.font_item, state.SCREEN_W // 2, content_y + content_h // 2, 140, 160, 190, center_x=True, center_y=True)
            return

        cols = 3
        rows = 2
        pad_x = 24
        gap_x = 12
        gap_y = 10

        card_w = (state.SCREEN_W - pad_x * 2 - (cols - 1) * gap_x) // cols
        card_h = (content_h - (rows - 1) * gap_y) // rows

        cur_row = self.selected_idx // cols
        if cur_row < self.scroll_row:
            self.scroll_row = cur_row
        elif cur_row >= self.scroll_row + rows:
            self.scroll_row = cur_row - rows + 1

        start_idx = self.scroll_row * cols
        vis_v = self.videos[start_idx : start_idx + cols * rows]

        for i, v in enumerate(vis_v):
            real_idx = start_idx + i
            r = i // cols
            c = i % cols
            bx = pad_x + c * (card_w + gap_x)
            by = content_y + r * (card_h + gap_y)
            is_sel = (real_idx == self.selected_idx)

            if is_sel:
                engine.fill_rect(bx, by, card_w, card_h, 28, 44, 75, 255)
                engine.draw_rect(bx, by, card_w, card_h, 230, 33, 23, 255, thickness=3)
                engine.fill_rect(bx + 4, by + 4, card_w - 8, 3, 230, 33, 23, 255)
            else:
                engine.fill_rect(bx, by, card_w, card_h, 18, 25, 42, 255)
                engine.draw_rect(bx, by, card_w, card_h, 38, 52, 80, 255, thickness=1)

            # Thumb image (Exact 16:9 proportional fit with compact 4px padding)
            v_id = v.get("id", "")
            thumb_path = os.path.join(YT_CACHE_DIR, f"{v_id}.jpg")
            img_pad_x = 4
            img_pad_y = 4
            img_w = card_w - img_pad_x * 2
            # 16:9 aspect ratio with balanced space for 2-line title
            max_img_h = card_h - 70
            img_h = min(int(img_w * 9 / 16), max_img_h)
            ix = bx + img_pad_x
            iy = by + img_pad_y

            drawn = False
            if os.path.exists(thumb_path):
                drawn = engine.draw_proportional_boxart(thumb_path, ix, iy, img_w, img_h)
            if not drawn:
                engine.fill_rect(ix, iy, img_w, img_h, 25, 35, 55, 255)
                engine.draw_text("YouTube", engine.font_badge, ix + img_w // 2, iy + img_h // 2, 230, 33, 23, center_x=True, center_y=True)

            # Star badge if video is in favorites
            if yt.is_favorite(v_id):
                engine.fill_rect(ix + img_w - 28, iy + 4, 24, 20, 20, 25, 40, 220)
                engine.draw_text("★", engine.font_badge, ix + img_w - 16, iy + 14, 255, 215, 0, center_x=True, center_y=True)

            # Duration badge
            dur = v.get("duration", "")
            if dur:
                dur_w = engine.measure_text(dur, engine.font_footer) + 8
                engine.fill_rect(ix + img_w - dur_w - 4, iy + img_h - 22, dur_w, 18, 0, 0, 0, 200)
                engine.draw_text(dur, engine.font_footer, ix + img_w - dur_w // 2 - 4, iy + img_h - 13, 255, 255, 255, center_x=True, center_y=True)

            # Title (Cleaned & Left-aligned with comfortable 30px line spacing)
            raw_title = v.get("disp_title") or v.get("title", "")
            clean_title = f"{real_idx + 1}. {yt.clean_yt_text(raw_title)}"
            t_lines = engine.wrap_text_to_width(clean_title, engine.font_grid_title, card_w - 16, max_lines=2)
            ty = iy + img_h + 6
            for tl in t_lines:
                t_col = (255, 255, 255) if is_sel else (200, 215, 235)
                engine.draw_text(tl, engine.font_grid_title, bx + 8, ty, t_col[0], t_col[1], t_col[2])
                ty += 30
