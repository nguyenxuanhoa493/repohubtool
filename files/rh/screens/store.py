# -*- coding: utf-8 -*-
"""Online ROM Store & Multi-Source Catalogue Browser Screen."""

import os
import threading
from .. import state
from ..i18n import tr
from ..catalog import (get_source_systems_list, get_games_for_view,
                      get_java_category_list, get_system_display_name,
                      scan_all_downloaded_games, alpha_index, clean_game_title)
from ..storage import human_bytes
from ..downloader import (enqueue_download, start_next_queued, dl_state,
                         download_state_for)
from ..modals.alphabet import AlphabetModal
from .base import BaseScreen


class StoreScreen(BaseScreen):
    """Multi-level ROM store catalogue screen."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.view_level = "menu"  # menu, systems, games, java_cats, search_results
        self.current_source = "VIET"
        self.current_sys_code = "ALL"
        self.current_java_cat = "ALL"
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0
        self.search_query = ""
        self.pre_dl_modal = False
        self.pre_dl_game = None

    def on_enter(self, params=None):
        params = params or {}
        level = params.get("level", "menu")
        if level == "menu":
            self.show_menu()
        elif level == "systems":
            self.show_systems(params.get("source", "VIET"))
        elif level == "games":
            self.show_games(params.get("source", "VIET"), params.get("sys_code", "ALL"))

    def show_menu(self):
        self.view_level = "menu"
        self.selected_idx = 0
        self.scroll_top = 0
        self.items = [
            {"id": "nav_search", "title": tr("rom_src_search"), "sub_title": "Tìm kiếm game theo từ khóa" if state.current_lang == "VI" else "Search catalog by keyword"},
            {"id": "src_VIET", "source": "VIET", "title": tr("rom_src_viet"), "sub_title": "Game Việt hóa & Bản địa" if state.current_lang == "VI" else "Vietnamese localized titles"},
            {"id": "src_HITS", "source": "HITS", "title": tr("rom_src_hits"), "sub_title": "Top 100 game kinh điển đỉnh cao" if state.current_lang == "VI" else "Top 100 curated classic hits"},
            {"id": "src_JAVA", "source": "JAVA", "title": tr("rom_src_java"), "sub_title": "Game Java J2ME điện thoại cổ" if state.current_lang == "VI" else "Java J2ME feature phone retro games"},
            {"id": "src_HACK", "source": "HACK", "title": tr("rom_src_hack"), "sub_title": "Bản mod, Pokemon Hack & Custom" if state.current_lang == "VI" else "Romhacks & fan translations"},
            {"id": "src_RETROSTIC", "source": "RETROSTIC", "title": tr("rom_src_retrostic"), "sub_title": "Kho tổng hợp đa hệ máy" if state.current_lang == "VI" else "Large multi-system archive"},
            {"id": "src_ARCHIVE", "source": "ARCHIVE", "title": tr("rom_src_archive"), "sub_title": "Kho lưu trữ Archive.org" if state.current_lang == "VI" else "Archive.org preservation sets"},
            {"id": "back", "title": tr("back_home"), "sub_title": ""}
        ]
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def show_systems(self, source):
        self.view_level = "systems"
        self.current_source = source
        self.selected_idx = 0
        self.scroll_top = 0
        sys_rows = get_source_systems_list(source)
        self.items = []
        for sc, cnt in sys_rows:
            s_name = get_system_display_name(sc)
            self.items.append({
                "id": f"sys_{sc}",
                "sys_code": sc,
                "title": f"{s_name} ({cnt})",
                "sub_title": f"Hệ máy: {sc}" if state.current_lang == "VI" else f"Platform: {sc}",
                "label": tr("view")
            })
        self.items.append({"id": "back", "title": tr("back_home"), "sub_title": ""})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def show_games(self, source, sys_code, java_cat="ALL"):
        self.view_level = "games"
        self.current_source = source
        self.current_sys_code = sys_code
        self.current_java_cat = java_cat
        self.selected_idx = 0
        self.scroll_top = 0

        # Scan local downloaded games index for fast O(1) membership check
        installed_games = scan_all_downloaded_games()
        installed_set = {(g.get("sys_code", "").upper(), g.get("filename", "").lower()) for g in installed_games}
        installed_bases = {(g.get("sys_code", "").upper(), os.path.splitext(g.get("filename", ""))[0].lower()) for g in installed_games}

        g_list = get_games_for_view(source, sys_code, category=java_cat)
        self.items = []
        for g in g_list:
            g_title = g.get("title", "Unknown")
            fn = g.get("filename", "")
            sc = g.get("sys_code", sys_code).upper()
            fn_base = os.path.splitext(fn)[0].lower()
            is_dl = (sc, fn.lower()) in installed_set or (sc, fn_base) in installed_bases

            self.items.append({
                "id": f"game_{fn}",
                "game_info": g,
                "sys_code": sc,
                "title": clean_game_title(g_title),
                "downloaded": is_dl
            })
        self.items.append({"id": "back", "title": tr("back_home")})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def get_header_title(self):
        if self.view_level == "menu":
            return tr("rom_menu_title")
        elif self.view_level == "systems":
            return f"{tr('rom_src_title')} - {self.current_source}"
        elif self.view_level == "games":
            return f"{self.current_source} • {self.current_sys_code} ({len(self.items) - 1})"
        elif self.view_level == "search_results":
            return f"Tìm kiếm: '{self.search_query}' ({len(self.items) - 1})"
        return tr("rom_menu_title")

    def get_footer_actions(self):
        if self.view_level in ("games", "search_results"):
            return [
                ("A", tr("footer_download"), (0, 230, 150), (220, 225, 235), True),
                ("X", tr("footer_alpha"), (0, 210, 255), (220, 225, 235), True),
                ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
            ]
        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        if self.pre_dl_modal:
            return self.handle_pre_dl_input(inputs)

        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")

        num_items = len(self.items)

        if btn_b:
            if self.view_level == "games":
                if self.current_source == "JAVA" and self.current_java_cat != "ALL":
                    self.show_java_cats()
                else:
                    self.show_systems(self.current_source)
            elif self.view_level in ("systems", "search_results"):
                self.show_menu()
            else:
                self.engine.pop_screen()
            return True

        max_visible = 6
        if btn_up:
            if self.selected_idx > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = num_items - 1
                self.scroll_top = max(0, num_items - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            return True
        elif btn_down:
            if self.selected_idx < num_items - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
                self.scroll_top = 0
            if self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            return True

        if btn_x and self.view_level in ("games", "search_results"):
            games_list = [it.get("game_info") for it in self.items if it.get("game_info")]
            avail, counts = alpha_index(games_list)

            def _on_jump(letter):
                if letter in avail:
                    self.selected_idx = avail[letter]
                    if self.selected_idx < self.scroll_top:
                        self.scroll_top = self.selected_idx
                    elif self.selected_idx >= self.scroll_top + max_visible:
                        self.scroll_top = self.selected_idx - max_visible + 1

            self.engine.open_modal(AlphabetModal(self.engine), {
                "available_map": avail,
                "counts_map": counts,
                "on_select": _on_jump
            })
            return True

        if btn_a and 0 <= self.selected_idx < num_items:
            item = self.items[self.selected_idx]
            it_id = item.get("id")

            if it_id == "back":
                if self.view_level == "games":
                    self.show_systems(self.current_source)
                elif self.view_level == "systems":
                    self.show_menu()
                else:
                    self.engine.pop_screen()
                return True

            if self.view_level == "menu":
                if it_id == "nav_search":
                    self.open_search_keyboard()
                elif item.get("source"):
                    src = item["source"]
                    if src == "JAVA":
                        self.show_java_cats()
                    else:
                        self.show_systems(src)

            elif self.view_level == "systems":
                sc = item.get("sys_code", "ALL")
                self.show_games(self.current_source, sc)

            elif self.view_level == "java_cats":
                cat_id = item.get("cat_id", "ALL")
                self.show_games("JAVA", "JAVA", java_cat=cat_id)

            elif self.view_level in ("games", "search_results"):
                g_info = item.get("game_info")
                if g_info:
                    self.open_pre_dl_modal(g_info, item.get("sys_code", self.current_sys_code))

            return True

        return False

    def show_java_cats(self):
        self.view_level = "java_cats"
        self.current_source = "JAVA"
        self.selected_idx = 0
        self.scroll_top = 0
        cats = get_java_category_list()
        self.items = []
        for cat_id, cnt in cats:
            lbl = f"Nhóm: {cat_id} ({cnt})"
            self.items.append({
                "id": f"jcat_{cat_id}",
                "cat_id": cat_id,
                "title": lbl,
                "sub_title": "Tuyển tập game Java theo chủ đề",
                "label": tr("view")
            })
        self.items.append({"id": "back", "title": tr("back_home"), "sub_title": ""})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def open_search_keyboard(self):
        def _on_search(query):
            self.search_query = query
            if not query:
                return
            self.view_level = "search_results"
            self.selected_idx = 0
            self.scroll_top = 0
            # Pre-indexed search in state.catalogs
            q_lower = query.lower()
            results = []
            for sc, sdata in state.catalogs.items():
                for g in sdata.get("games", []):
                    if q_lower in g.get("_s_idx", ""):
                        results.append((sc, g))
                        if len(results) >= 200:
                            break

            installed_games = scan_all_downloaded_games()
            installed_set = {(g.get("sys_code", "").upper(), g.get("filename", "").lower()) for g in installed_games}
            installed_bases = {(g.get("sys_code", "").upper(), os.path.splitext(g.get("filename", ""))[0].lower()) for g in installed_games}

            self.items = []
            for sc, g in results:
                fn = g.get("filename", "")
                sc_up = sc.upper()
                fn_base = os.path.splitext(fn)[0].lower()
                is_dl = (sc_up, fn.lower()) in installed_set or (sc_up, fn_base) in installed_bases
                self.items.append({
                    "id": f"sgame_{fn}",
                    "game_info": g,
                    "sys_code": sc,
                    "title": clean_game_title(g.get("title", "Unknown")),
                    "downloaded": is_dl
                })
            self.items.append({"id": "back", "title": tr("back_home")})
            for idx, it in enumerate(self.items):
                it["title"] = f"{idx + 1}. {it['title']}"

        self.engine.push_screen("keyboard", {
            "initial_text": self.search_query,
            "prompt": tr("search_prompt"),
            "on_search": _on_search
        })

    def open_pre_dl_modal(self, game_info, sys_code):
        self.pre_dl_modal = True
        self.pre_dl_game = (game_info, sys_code)

    def handle_pre_dl_input(self, inputs):
        if inputs.get("btn_b"):
            self.pre_dl_modal = False
            self.pre_dl_game = None
            return True

        if inputs.get("btn_a"):
            if self.pre_dl_game:
                g, sc = self.pre_dl_game
                enqueue_download(sc, g)
                start_next_queued()
                self.engine.toast(tr("dl_queue_next"))
            self.pre_dl_modal = False
            self.pre_dl_game = None
            return True

        return True

    def render(self, engine):
        num_items = len(self.items)
        panel_margin = 40
        panel_x = panel_margin
        panel_w = state.SCREEN_W - (panel_margin * 2)

        card_h = 76
        gap = 10
        start_y = 64 + 14
        max_visible = 6

        max_scroll = max(0, num_items - max_visible)
        if self.selected_idx < self.scroll_top:
            self.scroll_top = self.selected_idx
        elif self.selected_idx >= self.scroll_top + max_visible:
            self.scroll_top = self.selected_idx - max_visible + 1
        self.scroll_top = max(0, min(max_scroll, self.scroll_top))

        visible_items = self.items[self.scroll_top : self.scroll_top + max_visible]

        for i, item in enumerate(visible_items):
            actual_idx = self.scroll_top + i
            cy = start_y + i * (card_h + gap)
            is_sel = (actual_idx == self.selected_idx)

            badge_text = None
            badge_bg = (16, 48, 36)
            badge_border = (0, 230, 140)
            badge_fg = (0, 255, 160)

            # Check download status
            if item.get("game_info"):
                _dst = download_state_for(item["game_info"])
                if _dst == "downloading":
                    badge_text = tr("dling_badge")
                    badge_bg = (16, 40, 56)
                    badge_border = (0, 210, 255)
                    badge_fg = (0, 240, 255)
                elif _dst == "queued":
                    badge_text = tr("dl_queue_badge")
                    badge_bg = (48, 40, 16)
                    badge_border = (255, 200, 0)
                    badge_fg = (255, 215, 0)
                elif item.get("downloaded"):
                    badge_text = tr("downloaded_badge")
                    badge_bg = (16, 48, 36)
                    badge_border = (0, 230, 140)
                    badge_fg = (0, 255, 160)
            elif item.get("label"):
                badge_text = item["label"]
                badge_bg = (30, 42, 68)
                badge_border = (65, 90, 135)
                badge_fg = (0, 230, 255)

            if is_sel:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 28, 44, 75, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                text_r, text_g, text_b = 255, 255, 255
            else:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 19, 26, 42, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 40, 54, 85, 255, thickness=1)
                text_r, text_g, text_b = 200, 210, 225

            item_title = item.get("title", "")
            engine.draw_text(item_title, engine.font_item, panel_x + 28, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

            if badge_text:
                badge_w = 120
                badge_h = 42
                badge_x = panel_x + panel_w - badge_w - 24
                badge_y = cy + (card_h - badge_h) // 2

                engine.fill_rect(badge_x, badge_y, badge_w, badge_h, badge_bg[0], badge_bg[1], badge_bg[2], 255)
                engine.draw_rect(badge_x, badge_y, badge_w, badge_h, badge_border[0], badge_border[1], badge_border[2], 255, thickness=1)
                engine.draw_text(badge_text, engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, badge_fg[0], badge_fg[1], badge_fg[2], center_x=True, center_y=True)

        # Pre-Download Modal Overlay
        if self.pre_dl_modal and self.pre_dl_game:
            g, sc = self.pre_dl_game
            engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 200)

            mw = 680
            mh = 320
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            engine.fill_rect(mx, my, mw, mh, 18, 25, 42, 255)
            engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            engine.fill_rect(mx + 3, my + 3, mw - 6, 56, 24, 34, 58, 255)
            engine.draw_text("XÁC NHẬN TẢI GAME", engine.font_item, mx + mw // 2, my + 31, 0, 246, 246, center_x=True, center_y=True)

            g_clean_name = clean_game_title(g.get('title','Unknown'))
            engine.draw_text(f"• Tên game: {g_clean_name[:42]}", engine.font_sub, mx + 40, my + 90, 255, 255, 255)
            engine.draw_text(f"• Hệ máy: {sc}", engine.font_sub, mx + 40, my + 130, 0, 230, 255)
            engine.draw_text(f"• Tệp tin: {g.get('filename','')[:42]}", engine.font_sub, mx + 40, my + 170, 200, 215, 235)

            engine.draw_footer_btn(mx + 40, my + mh - 60, 48, "A", "Tải vào hàng đợi", btn_color=(0, 230, 150), is_dark_btn=True)
            engine.draw_footer_btn(mx + mw - 180, my + mh - 60, 48, "B", "Hủy bỏ", btn_color=(255, 75, 75), is_dark_btn=False)
