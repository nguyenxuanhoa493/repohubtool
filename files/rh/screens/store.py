# -*- coding: utf-8 -*-
"""Online ROM Store & Catalog Browser with Instant Search, Download Queue & Unified Game Action Details."""

import os
import threading
import time
from .. import state
from .. import catalog as catalog_mod
from ..paths import SDCARD_PATH, resolve_rom_dir
from ..i18n import tr
from ..catalog import (get_source_systems_list, get_games_for_view, get_java_category_display_name,
                      get_java_category_list, get_system_display_name,
                      scan_all_downloaded_games, alpha_index, clean_game_title,
                      search_catalog_games)
from ..ui.boxart import resolve_game_img_path
from ..emulators import resolve as resolve_emulator
from ..downloader import (dl_state, download_state_for)
from ..installed import (find as find_installed, companions as installed_companions,
                         invalidate as invalidate_installed)
from ..modals.alphabet import AlphabetModal
from ..modals.game_action import GameActionModal
from ..modals.common import ResolutionModal
from .base import BaseScreen


def _installed_indexes():
    """{(he, ten file): entry} va {(he, base): entry} tu mot lan quet thu muc."""
    by_name, by_base = {}, {}
    for g in scan_all_downloaded_games():
        sc_up = g.get("sys_code", "").upper()
        name = g.get("filename", "")
        by_name[(sc_up, name.lower())] = g
        by_base.setdefault((sc_up, os.path.splitext(name)[0].lower()), g)
    return by_name, by_base

def _installed_entry(by_name, by_base, sys_code, filename):
    """Ban cai tren the khop voi mot dong catalogue, hoac None."""
    if not filename:
        return None
    sc_up = str(sys_code or "").upper()
    return (by_name.get((sc_up, filename.lower()))
            or by_base.get((sc_up, os.path.splitext(filename)[0].lower())))

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
        # Chi hoi server mot lan moi phien khi may chua co kho game (xem
        # _ensure_catalog): mo ra vao lai nhieu lan khong duoc spam modal.
        self._catalog_checked = False

        self.show_menu()

    def get_title(self):
        if self.view_level == "menu":
            return tr("store_menu_title")
        if self.view_level == "systems":
            src_names = {
                "HITS": tr("store_src_hits"),
                "JAVA": "GAME JAVA J2ME",
                "HACK": "GAME HACK / MOD",
                "RETROSTIC": tr("store_src_retrostic"),
                "GDRIVE": tr("store_src_gdrive"),
                "ARCHIVE": tr("store_src_archive"),
                "ALL": tr("store_src_all")
            }
            name = src_names.get(self.current_source, self.current_source)
            return f"{name} - {tr('store_choose_system')}"
        if self.view_level == "java_cats":
            return tr("store_java_topics")
        if self.view_level == "search_results":
            return tr("store_search_results").format(q=self.search_query)
        
        sys_name = get_system_display_name(self.current_sys_code)
        if self.current_java_cat != "ALL":
            name, _ = get_java_category_display_name(self.current_java_cat)
            return f"JAVA - {name.upper()}"
        return sys_name.upper()

    def get_footer_actions(self):
        actions = [("▲▼", tr("nav_select"), (70, 95, 140), (220, 225, 235), False)]
        if self.view_level in ("games", "search_results"):
            actions.append(("A", tr("store_footer_detail"), (0, 230, 150), (220, 225, 235), True))
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
            {"id": "cat_hits", "source": "HITS", "title": tr("menu_hits_title"), "sub_title": tr("menu_hits_sub"), "label": tr("view")},
            {"id": "cat_java", "source": "JAVA", "title": tr("menu_java_title"), "sub_title": tr("menu_java_sub"), "label": tr("view")},
            {"id": "cat_hack", "source": "HACK", "title": tr("menu_hack_title"), "sub_title": tr("menu_hack_sub"), "label": tr("view")},
            {"id": "cat_retrostic", "source": "RETROSTIC", "title": tr("menu_retrostic_title"), "sub_title": tr("menu_retrostic_sub"), "label": tr("view")},
            {"id": "cat_gdrive", "source": "GDRIVE", "title": tr("menu_gdrive_title"), "sub_title": tr("menu_gdrive_sub"), "label": tr("view")},
            {"id": "cat_archive", "source": "ARCHIVE", "title": tr("menu_archive_title"), "sub_title": tr("menu_archive_sub"), "label": tr("view")},
            {"id": "back", "title": tr("back_home"), "sub_title": ""}
        ]
        for idx, it in enumerate(self.items):
            if it.get("id") != "back":
                it["title"] = f"{idx + 1}. {it['title']}"

    def _ensure_catalog(self):
        """Lay kho game khi may chua co.

        May cai tu file zip khong di qua OTA, va catalogue chi den duoc bang
        duong cap nhat; khong co buoc nay thi ROMs Store mo ra la danh sach
        rong va khong co gi bao nguoi dung phai lam gi. Mot lan moi phien."""
        if self._catalog_checked:
            return False
        self._catalog_checked = True
        try:
            handle = getattr(catalog_mod, "db", None)
            if handle and os.path.exists(handle.DB_PATH):
                return False
        except Exception:
            pass
        if not self.engine:
            return False

        def _bg():
            try:
                from ..updater import check_for_update
                found = check_for_update(force=True)
            except Exception as e:
                print("Catalog bootstrap error: %s" % e)
                found = None
            engine = self.engine
            if not engine or not getattr(engine, "running", True):
                return
            if found:
                manifest, files = found
                try:
                    engine.open_modal(engine.update_modal, {"manifest": manifest, "files": files})
                except Exception as e:
                    print("Catalog modal error: %s" % e)
            else:
                try:
                    engine.toast(tr("store_no_catalog"), text_color=(255, 180, 0))
                except Exception:
                    pass

        try:
            self.engine.toast(tr("store_catalog_fetching"))
        except Exception:
            pass
        threading.Thread(target=_bg, daemon=True).start()
        return True

    def show_systems(self, source_type):
        self._ensure_catalog()
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
        self._ensure_catalog()
        self.view_level = "games"
        self.current_source = source_type
        self.current_sys_code = sys_code
        self.current_java_cat = java_cat
        self.selected_idx = 0
        self.scroll_top = 0

        by_name, by_base = _installed_indexes()
        games = get_games_for_view(source_type, sys_code, java_cat=java_cat)
        self.items = []
        for g in games:
            fn = g.get("filename", "")
            sc = g.get("sys_code", sys_code)
            entry = _installed_entry(by_name, by_base, sc, fn)
            self.items.append({
                "id": f"game_{g.get('id', fn)}",
                "game_info": g,
                "sys_code": sc,
                "title": clean_game_title(g.get("title", "Unknown")),
                "downloaded": entry is not None,
                "installed": entry
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
            name, desc = get_java_category_display_name(cat_id)
            lbl = f"{name} ({cnt})"
            self.items.append({
                "id": f"jcat_{cat_id}",
                "cat_id": cat_id,
                "title": lbl,
                "sub_title": desc,
                "label": tr("view")
            })
        self.items.append({"id": "back", "title": tr("back_home"), "sub_title": ""})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def open_search_keyboard(self):
        def _on_search(query):
            self.search_query = query
            if not query or not query.strip():
                return
            self.view_level = "search_results"
            self.selected_idx = 0
            self.scroll_top = 0

            results = search_catalog_games(query.strip(), limit=200)

            by_name, by_base = _installed_indexes()
            self.items = []
            for g in results:
                sc = g.get("sys_code", "")
                fn = g.get("filename", "")
                entry = _installed_entry(by_name, by_base, sc, fn)
                clean_title = clean_game_title(g.get("title", "Unknown"))
                display_title = f"[{sc}] {clean_title}" if sc else clean_title
                self.items.append({
                    "id": f"sgame_{g.get('id', fn)}",
                    "game_info": g,
                    "sys_code": sc,
                    "title": display_title,
                    "downloaded": entry is not None,
                    "installed": entry
                })
            self.items.append({"id": "back", "title": tr("back_home")})
            for idx, it in enumerate(self.items):
                it["title"] = f"{idx + 1}. {it['title']}"

        self.engine.push_screen("keyboard", {
            "initial_text": self.search_query,
            "prompt": tr("search_prompt"),
            "on_search": _on_search
        })

    def open_game_action_modal(self, item):
        g = item.get("game_info", {})
        sc = item.get("sys_code", self.current_sys_code)
        fn = g.get("filename", "")
        entry = item.get("installed")
        if entry is None:
            entry = find_installed(sc, fn)
        r_dir = resolve_rom_dir(sc)
        rp = ""
        if r_dir and fn:
            cand = os.path.join(r_dir, fn)
            if os.path.exists(cand):
                rp = cand
        if not rp and entry:
            # Ten goi tai ve khac ten ROM da bung: duong dan that nam trong entry.
            rp = entry.get("path", "")
        if rp and os.path.exists(rp):
            g["path"] = rp
            g["rom_path"] = rp
        ip = resolve_game_img_path(sc, entry.get("filename") if entry else fn)

        def _on_launch(s_code, g_info, with_cheat=False, netplay_param=None):
            self.launch_game(s_code, g_info, with_cheat=with_cheat, netplay_param=netplay_param)

        def _on_delete(s_code, g_info):
            self.delete_game(s_code, g_info)
            item["downloaded"] = False
            item["installed"] = None

        def _on_netplay(s_code, g_info):
            from ..modals.netplay import NetplayModal
            self.engine.open_modal(NetplayModal(self.engine), {
                "sys_code": s_code,
                "game_info": g_info,
                "rom_path": rp,
                "on_launch": _on_launch
            })

        def _on_res(s_code, g_info, rom_path):
            self.engine.open_modal(ResolutionModal(self.engine), {
                "sys_code": s_code,
                "game_info": g_info,
                "rom_path": rom_path
            })

        def _on_download_success(s_code, g_info):
            invalidate_installed()
            inst_entry = find_installed(s_code, g_info.get("filename", ""))
            item["installed"] = inst_entry
            item["downloaded"] = True
            if inst_entry and inst_entry.get("path"):
                g_info["path"] = inst_entry["path"]
                g_info["rom_path"] = inst_entry["path"]

        self.engine.open_modal(GameActionModal(self.engine), {
            "sys_code": sc,
            "game_info": g,
            "rom_path": rp,
            "img_path": ip,
            "on_launch": _on_launch,
            "on_delete": _on_delete,
            "on_netplay": _on_netplay,
            "on_res": _on_res,
            "on_download_success": _on_download_success
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
            entry = find_installed(sys_code, fn)
            if entry and entry.get("path") and os.path.exists(entry["path"]):
                rom_p = entry["path"]

        if not rom_p or not os.path.exists(rom_p):
            self.engine.toast(tr("store_err_no_rom"))
            return

        emu_dir, script_path = resolve_emulator(sys_code)
        if not script_path or not os.path.exists(script_path):
            self.engine.toast(tr("store_err_no_emulator").format(sys=sys_code))
            return

        title_display = clean_game_title(game_info.get("title", "Game"))
        self.engine.toast(tr("store_launching").format(title=title_display))

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
            self.engine.toast(tr("store_err_launch").format(err=e))

    def delete_game(self, sys_code, game_info):
        """Delete the installed ROM, its companion files and the boxart.

        Kho ghi ten goi tai ve (.zip) con thu muc Roms giu ten ROM da bung, nen
        xoa theo ten catalogue truoc day khong xoa duoc gi ma van bao "Da xoa"."""
        rom_p = game_info.get("path") or game_info.get("rom_path") or ""
        fn = game_info.get("filename", "")
        if not rom_p or not os.path.exists(rom_p):
            entry = find_installed(sys_code, fn)
            rom_p = entry["path"] if entry else ""

        removed = 0
        if rom_p and os.path.exists(rom_p):
            # Cue/bin di theo cap: xoa ROM chinh ma de lai .bin la bo rac tren the.
            for p in [rom_p] + installed_companions(rom_p):
                try:
                    os.remove(p)
                    removed += 1
                except OSError as e:
                    self.engine.toast(tr("store_err_delete").format(err=e))
                    return

        img_p = resolve_game_img_path(sys_code, fn)
        if img_p and os.path.exists(img_p):
            try:
                os.remove(img_p)
            except OSError:
                pass

        invalidate_installed()
        if removed:
            self.engine.toast(tr("store_deleted").format(title=game_info.get("title", "Game")))
        else:
            self.engine.toast(tr("dl_nothing_to_delete"))

    def handle_input(self, inputs):
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
                elif self.view_level in ("systems", "java_cats", "search_results"):
                    self.show_menu()
                else:
                    self.engine.pop_screen()
                return True

            if self.view_level == "menu":
                if it_id == "nav_search":
                    self.open_search_keyboard()
                elif it_id == "cat_java":
                    self.show_java_cats()
                elif "source" in item:
                    self.show_systems(item["source"])

            elif self.view_level == "systems":
                if "sys_code" in item:
                    self.show_games(self.current_source, item["sys_code"])

            elif self.view_level == "java_cats":
                if "cat_id" in item:
                    self.show_games("JAVA", "JAVA", java_cat=item["cat_id"])

            elif self.view_level in ("games", "search_results"):
                g_info = item.get("game_info")
                if g_info:
                    self.open_game_action_modal(item)

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
                    badge_text = tr("store_badge_downloaded")
                    badge_bg = (16, 48, 36)
                    badge_border = (0, 230, 140)
                    badge_fg = (0, 255, 160)

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
