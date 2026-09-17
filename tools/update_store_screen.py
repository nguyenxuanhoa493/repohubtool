with open("files/rh/screens/store.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's inspect the entire new store.py code
new_store_code = '''# -*- coding: utf-8 -*-
"""Online ROM Store & Catalog Browser with Instant Search, Download Queue & Game Action Details."""

import os
import time
from .. import state
from ..paths import SDCARD_PATH, resolve_rom_dir
from ..i18n import tr
from ..catalog import (get_source_systems_list, get_games_for_view,
                      get_java_category_list, get_system_display_name,
                      scan_all_downloaded_games, alpha_index, clean_game_title)
from ..storage import human_bytes
from ..ui.boxart import resolve_game_img_path
from ..emulators import resolve as resolve_emulator
from ..downloader import (enqueue_download, start_next_queued, dl_state,
                         download_state_for, is_download_running, cancel_active_download)
from ..modals.alphabet import AlphabetModal
from ..modals.game_action import GameActionModal
from ..modals.common import ResolutionModal
from .base import BaseScreen


class StoreScreen(BaseScreen):
    """Store Screen: Browse curated games, system catalogs, online search, and download queue."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.view_level = "menu"       # "menu" | "systems" | "games" | "search_results" | "java_cats"
        self.current_source = "ALL"
        self.current_sys_code = "ALL"
        self.current_java_cat = "ALL"
        self.search_query = ""

        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0

        self.pre_dl_modal = False
        self.pre_dl_game = None

        self.show_menu()

    def get_title(self):
        if self.view_level == "menu":
            return tr("store_menu_title")
        if self.view_level == "systems":
            src_names = {
                "VIET": "GAME VIỆT HÓA",
                "HACK": "GAME HACK / MOD",
                "HITS": "TOP LƯỢT TẢI",
                "ALL": "KHO TỔNG HỢP"
            }
            return f"{src_names.get(self.current_source, self.current_source)} - CHỌN HỆ MÁY"
        if self.view_level == "java_cats":
            return "GAME JAVA - CHỦ ĐỀ TUYỂN CHỌN"
        if self.view_level == "search_results":
            return f"TÌM KIẾM: '{self.search_query}'"
        
        sys_name = get_system_display_name(self.current_sys_code)
        if self.current_java_cat != "ALL":
            return f"JAVA - {self.current_java_cat.upper()}"
        return sys_name.upper()

    def get_footer_actions(self):
        if self.pre_dl_modal:
            is_dling = self._is_current_pre_dl_downloading()
            if is_dling:
                return [
                    ("B", "Chạy ngầm", (70, 95, 140), (220, 225, 235), False),
                    ("X", "Hủy tải", (255, 75, 75), (255, 255, 255), True),
                ]
            else:
                return [
                    ("A", "Tải game", (0, 230, 150), (220, 225, 235), True),
                    ("B", "Đóng", (255, 75, 75), (220, 225, 235), False),
                ]

        actions = [("▲▼", tr("nav_select"), (70, 95, 140), (220, 225, 235), False)]
        if self.view_level in ("games", "search_results"):
            actions.append(("A", "Chi tiết / Tải", (0, 230, 150), (220, 225, 235), True))
            actions.append(("X", tr("nav_jump_alpha"), (0, 210, 255), (220, 225, 235), True))
        else:
            actions.append(("A", tr("nav_open"), (0, 230, 150), (220, 225, 235), True))

        actions.append(("B", tr("nav_back"), (255, 75, 75), (220, 225, 235), False))
        return actions

    def show_menu(self):
        self.view_level = "menu"
        self.selected_idx = 0
        self.scroll_top = 0
        self.items = [
            {"id": "nav_search", "title": tr("menu_search_title"), "sub_title": tr("menu_search_sub"), "label": tr("search")},
            {"id": "cat_viet", "source": "VIET", "title": tr("menu_viet_title"), "sub_title": tr("menu_viet_sub"), "label": tr("view")},
            {"id": "cat_hack", "source": "HACK", "title": tr("menu_hack_title"), "sub_title": tr("menu_hack_sub"), "label": tr("view")},
            {"id": "cat_hits", "source": "HITS", "title": tr("menu_hits_title"), "sub_title": tr("menu_hits_sub"), "label": tr("view")},
            {"id": "cat_java", "source": "JAVA", "title": tr("menu_java_title"), "sub_title": tr("menu_java_sub"), "label": tr("view")},
            {"id": "cat_all", "source": "ALL", "title": tr("menu_all_title"), "sub_title": tr("menu_all_sub"), "label": tr("view")},
            {"id": "back", "title": tr("back_home"), "sub_title": ""}
        ]

    def show_systems(self, source_type):
        self.view_level = "systems"
        self.current_source = source_type
        self.selected_idx = 0
        self.scroll_top = 0
        systems = get_source_systems_list(source_type)
        self.items = []
        for sys_code, cnt in systems:
            sys_name = get_system_display_name(sys_code)
            lbl = f"{sys_name} ({cnt})"
            self.items.append({
                "id": f"sys_{sys_code}",
                "sys_code": sys_code,
                "title": lbl,
                "sub_title": f"Kho game {sys_name}",
                "label": tr("view")
            })
        self.items.append({"id": "back", "title": tr("back_home"), "sub_title": ""})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def show_games(self, source_type, sys_code, java_cat="ALL"):
        self.view_level = "games"
        self.current_source = source_type
        self.current_sys_code = sys_code
        self.current_java_cat = java_cat
        self.selected_idx = 0
        self.scroll_top = 0

        installed_games = scan_all_downloaded_games()
        installed_set = {(g.get("sys_code", "").upper(), g.get("filename", "").lower()) for g in installed_games}
        installed_bases = {(g.get("sys_code", "").upper(), os.path.splitext(g.get("filename", ""))[0].lower()) for g in installed_games}

        games = get_games_for_view(source_type, sys_code, java_cat=java_cat)
        self.items = []
        for g in games:
            fn = g.get("filename", "")
            sc = g.get("sys_code", sys_code)
            sc_up = sc.upper()
            fn_base = os.path.splitext(fn)[0].lower()
            is_dl = (sc_up, fn.lower()) in installed_set or (sc_up, fn_base) in installed_bases
            self.items.append({
                "id": f"game_{g.get('id', fn)}",
                "game_info": g,
                "sys_code": sc,
                "title": clean_game_title(g.get("title", "Unknown")),
                "downloaded": is_dl
            })
        self.items.append({"id": "back", "title": tr("back_home")})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

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

    def _is_current_pre_dl_downloading(self):
        if not self.pre_dl_game:
            return False
        g, sc = self.pre_dl_game
        return download_state_for(g) in ("downloading", "queued") or (is_download_running() and dl_state.get("active"))

    def open_pre_dl_modal(self, game_info, sys_code):
        self.pre_dl_modal = True
        self.pre_dl_game = (game_info, sys_code)

    def open_game_action_modal(self, item):
        g = item.get("game_info", {})
        sc = item.get("sys_code", self.current_sys_code)
        fn = g.get("filename", "")
        rp = os.path.join(SDCARD_PATH, "Roms", sc, fn)
        ip = resolve_game_img_path(sc, fn)

        def _on_launch(sys_code, game_info, with_cheat=False, netplay_param=None):
            self.launch_game(sys_code, game_info, with_cheat=with_cheat, netplay_param=netplay_param)

        def _on_delete(sys_code, game_info):
            self.delete_game(sys_code, game_info)
            item["downloaded"] = False

        def _on_netplay(sys_code, game_info):
            from ..modals.netplay import NetplayModal
            self.engine.open_modal(NetplayModal(self.engine), {
                "sys_code": sys_code,
                "game_info": game_info,
                "rom_path": rp,
                "on_launch": _on_launch
            })

        def _on_res(sys_code, game_info, rom_path):
            self.engine.open_modal(ResolutionModal(self.engine), {
                "sys_code": sys_code,
                "game_info": game_info,
                "rom_path": rom_path
            })

        self.engine.open_modal(GameActionModal(self.engine), {
            "sys_code": sc,
            "game_info": g,
            "rom_path": rp,
            "img_path": ip,
            "on_launch": _on_launch,
            "on_delete": _on_delete,
            "on_netplay": _on_netplay,
            "on_res": _on_res
        })

    def launch_game(self, sys_code, game_info, with_cheat=False, netplay_param=None):
        """Launch emulator for target game with arguments."""
        rom_p = game_info.get("path") or game_info.get("rom_path") or ""
        fn = game_info.get("filename", "")
        if not rom_p or not os.path.exists(rom_p):
            candidates = [
                os.path.join(SDCARD_PATH, "Roms", sys_code, fn),
                os.path.join(SDCARD_PATH, "Roms", f"({sys_code})", fn),
            ]
            for c in candidates:
                if fn and os.path.exists(c):
                    rom_p = c
                    break

        if not rom_p or not os.path.exists(rom_p):
            self.engine.toast("Không tìm thấy file ROM trên thẻ nhớ!")
            return

        emu_dir, script_path = resolve_emulator(sys_code)
        if not script_path or not os.path.exists(script_path):
            self.engine.toast(f"Không tìm thấy giả lập cho hệ {sys_code}!")
            return

        title_display = clean_game_title(game_info.get("title", "Game"))
        self.engine.toast(f"Đang khởi động {title_display}...")

        handoff_script = f"""#!/bin/sh
cd "{emu_dir or os.path.dirname(script_path)}"
"{script_path}" "{rom_p}" {" " + str(netplay_param) if netplay_param else ""}
"""
        try:
            with open("/tmp/launch_game.sh", "w", encoding="utf-8") as f:
                f.write(handoff_script)
            os.chmod("/tmp/launch_game.sh", 0o755)
            with open("/tmp/rh_last_screen.txt", "w", encoding="utf-8") as f:
                f.write("store")
            self.engine.running = False
        except Exception as e:
            self.engine.toast(f"Lỗi khởi động: {e}")

    def delete_game(self, sys_code, game_info):
        """Delete local ROM file and associated assets."""
        rom_p = game_info.get("path") or game_info.get("rom_path") or ""
        fn = game_info.get("filename", "")
        if not rom_p or not os.path.exists(rom_p):
            candidates = [
                os.path.join(SDCARD_PATH, "Roms", sys_code, fn),
                os.path.join(SDCARD_PATH, "Roms", f"({sys_code})", fn),
            ]
            for c in candidates:
                if fn and os.path.exists(c):
                    rom_p = c
                    break

        if rom_p and os.path.exists(rom_p):
            try:
                os.remove(rom_p)
            except Exception as e:
                self.engine.toast(f"Lỗi xóa ROM: {e}")
                return

        # Delete image if exists
        img_p = resolve_game_img_path(sys_code, fn)
        if img_p and os.path.exists(img_p):
            try:
                os.remove(img_p)
            except Exception:
                pass

        self.engine.toast(f"Đã xóa {game_info.get('title', 'Game')}")

    def handle_pre_dl_input(self, inputs):
        is_dling = self._is_current_pre_dl_downloading()

        if inputs.get("btn_b"):
            self.pre_dl_modal = False
            self.pre_dl_game = None
            return True

        if inputs.get("btn_x") and is_dling:
            cancel_active_download()
            self.engine.toast("Đã hủy tải game!")
            return True

        if inputs.get("btn_a"):
            if self.pre_dl_game and not is_dling:
                g, sc = self.pre_dl_game
                msg = enqueue_download(sc, g)
                start_next_queued(background=False)
                if msg:
                    self.engine.toast(msg)
                # Keep modal open to show the live download progress!
            return True

        return True

    def handle_input(self, inputs):
        if self.pre_dl_modal:
            return self.handle_pre_dl_input(inputs)

        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_x = inputs.get("btn_x")

        num_items = len(self.items)
        max_visible = 6

        if btn_b:
            if self.view_level == "games":
                self.show_systems(self.current_source)
            elif self.view_level == "systems":
                self.show_menu()
            elif self.view_level == "java_cats":
                self.show_menu()
            elif self.view_level == "search_results":
                self.show_menu()
            else:
                self.engine.pop_screen()
            return True

        if btn_up:
            self.selected_idx = max(0, self.selected_idx - 1)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            return True

        if btn_down:
            self.selected_idx = min(num_items - 1, self.selected_idx + 1)
            if self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            return True

        if btn_left:
            self.selected_idx = max(0, self.selected_idx - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            return True

        if btn_right:
            self.selected_idx = min(num_items - 1, self.selected_idx + max_visible)
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
                    if item.get("downloaded"):
                        self.open_game_action_modal(item)
                    else:
                        self.open_pre_dl_modal(g_info, item.get("sys_code", self.current_sys_code))

            return True

        return False

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

        # Check real-time download completion to update items
        if dl_state.get("active") and dl_state.get("status") == "success":
            for it in self.items:
                gi = it.get("game_info")
                if gi and gi.get("title") == dl_state.get("title"):
                    it["downloaded"] = True

        for i, item in enumerate(visible_items):
            actual_idx = self.scroll_top + i
            cy = start_y + i * (card_h + gap)
            is_sel = (actual_idx == self.selected_idx)

            badge_text = None
            badge_bg = (16, 48, 36)
            badge_border = (0, 230, 140)
            badge_fg = (0, 255, 160)

            # Check download status & real-time file existence
            if item.get("game_info"):
                gi = item["game_info"]
                fn = gi.get("filename", "")
                sc = item.get("sys_code", self.current_sys_code)

                # Dynamically mark downloaded if file exists on disk
                if not item.get("downloaded") and fn and sc:
                    r_dir = resolve_rom_dir(sc)
                    if r_dir and os.path.exists(os.path.join(r_dir, fn)):
                        item["downloaded"] = True

                _dst = download_state_for(gi)
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

        # Pre-Download / Download Progress Modal Overlay
        if self.pre_dl_modal and self.pre_dl_game:
            g, sc = self.pre_dl_game
            engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

            mw = 760
            mh = 380
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            is_dling = self._is_current_pre_dl_downloading()

            # Modal Box
            engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            # Header
            header_title = "TIẾN ĐỘ TẢI GAME" if is_dling else "XÁC NHẬN TẢI GAME"
            engine.fill_rect(mx + 3, my + 3, mw - 6, 52, 22, 32, 54, 255)
            engine.draw_text(header_title, engine.font_item, mx + mw // 2, my + 28, 0, 246, 246, center_x=True, center_y=True)

            # Left Card: Boxart Preview Avatar
            card_pad = 20
            box_x = mx + card_pad + 6
            box_y = my + 68
            box_w = 190
            box_h = mh - 130

            engine.fill_rect(box_x, box_y, box_w, box_h, 12, 17, 30, 255)
            engine.draw_rect(box_x, box_y, box_w, box_h, 45, 60, 95, 255, thickness=2)

            g_clean_name = clean_game_title(g.get("title", "Unknown"))
            fn = g.get("filename", "")
            img_p = resolve_game_img_path(sc, fn)

            drawn_img = False
            if img_p and os.path.exists(img_p):
                drawn_img = engine.draw_proportional_boxart(img_p, box_x + 8, box_y + 8, box_w - 16, box_h - 16)
            if not drawn_img:
                engine.draw_default_boxart_avatar(box_x + 8, box_y + 8, box_w - 16, box_h - 16, sc, g_clean_name)

            # Right Details Card
            rx = box_x + box_w + 22
            rw = mw - (rx - mx) - card_pad

            engine.draw_text(f"• Tên game: {g_clean_name[:36]}", engine.font_sub, rx, my + 80, 255, 255, 255)
            engine.draw_text(f"• Hệ máy: {sc} ({get_system_display_name(sc)})", engine.font_sub, rx, my + 115, 0, 230, 255)
            engine.draw_text(f"• Tệp tin: {fn[:36]}", engine.font_sub, rx, my + 150, 200, 215, 235)
            engine.draw_text(f"• Dung lượng: {g.get('file_size_str', '--')}", engine.font_sub, rx, my + 185, 255, 215, 0)

            # Live Progress Bar if Downloading
            if is_dling:
                bar_y = my + 225
                bar_w = rw - 10
                bar_h = 16
                pct = max(0, min(100, dl_state.get("progress_pct", 0)))

                engine.fill_rect(rx, bar_y, bar_w, bar_h, 24, 34, 58, 255)
                engine.draw_rect(rx, bar_y, bar_w, bar_h, 45, 65, 105, 255, thickness=1)

                fill_w = int((bar_w - 4) * (pct / 100.0))
                if fill_w > 0:
                    engine.fill_rect(rx + 2, bar_y + 2, fill_w, bar_h - 4, 0, 230, 150, 255)

                speed_str = dl_state.get("speed_str", "0 KB/s")
                down_str = dl_state.get("downloaded_str", "")
                status_msg = dl_state.get("msg", "Đang tải...")

                engine.draw_text(f"{pct}%  ({speed_str})", engine.font_badge, rx + bar_w, bar_y - 12, 0, 255, 160, center_y=True)
                engine.draw_text(status_msg[:42], engine.font_sub, rx, bar_y + 30, 180, 205, 235)

                engine.draw_footer_btn(rx, my + mh - 55, 42, "B", "Chạy ngầm", btn_color=(70, 95, 140), is_dark_btn=False)
                engine.draw_footer_btn(rx + rw - 140, my + mh - 55, 42, "X", "Hủy tải", btn_color=(255, 75, 75), is_dark_btn=True)
            else:
                engine.draw_footer_btn(rx, my + mh - 55, 42, "A", "Tải game ngay", btn_color=(0, 230, 150), is_dark_btn=True)
                engine.draw_footer_btn(rx + rw - 140, my + mh - 55, 42, "B", "Hủy bỏ", btn_color=(255, 75, 75), is_dark_btn=False)
'''

with open("files/rh/screens/store.py", "w", encoding="utf-8") as f:
    f.write(new_store_code)

print("Updated StoreScreen completely!")
