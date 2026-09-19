#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest for Retro Store, Game Store sources (GDRIVE, RETROSTIC, etc.), and menu reorganizations."""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_DIR = os.path.join(ROOT_DIR, "files")
sys.path.insert(0, FILES_DIR)

from unittest.mock import MagicMock
for m in ["sdl2", "sdl2.sdlttf", "sdl2.sdlimage", "sdl2.ext"]:
    sys.modules[m] = MagicMock()

import db
from rh import state
from rh.screens.home import HomeScreen
from rh.screens.utilities import UtilitiesScreen
from rh.screens.store import StoreScreen
from rh.screens.retro_store import RetroStoreScreen


class FakeEngine:
    def __init__(self):
        self.screen_stack = []
        self.modal_stack = []

    def push_screen(self, name, params=None):
        self.screen_stack.append(name)

    def pop_screen(self):
        if self.screen_stack:
            return self.screen_stack.pop()
        return None

    def open_modal(self, modal, params=None):
        self.modal_stack.append((modal, params))


class TestRetroStoreAndSources(unittest.TestCase):

    def setUp(self):
        state.current_lang = "VI"
        self.engine = FakeEngine()

    def test_gdrive_source_in_db(self):
        """Kiem tra DB co nguon GDRIVE voi day du he may va game."""
        counts = db.get_source_systems_counts("GDRIVE")
        self.assertTrue(len(counts) > 0, "Nguon GDRIVE phai co danh sach he may")
        sys_dict = dict(counts)
        self.assertIn("ALL", sys_dict)
        self.assertGreaterEqual(sys_dict["ALL"], 1000, "GDRIVE phai co tren 1000 game")
        # Kiem tra mot so he may quen thuoc trong Google Drive
        for sc in ["MD", "GBA", "PCE", "NDS", "PS", "PSP", "ATARI2600"]:
            self.assertIn(sc, sys_dict, f"He may {sc} phai co trong kho GDRIVE")

        # Kiem tra lay trang game GDRIVE
        games = db.get_games_page("GDRIVE", "ALL", limit=10)
        self.assertGreaterEqual(len(games), 1)
        for g in games:
            self.assertEqual(g.get("source_name"), "GDRIVE", "Game lay ra phai co source_name GDRIVE")
            self.assertTrue(g.get("rom_url", "").startswith("https://drive.google.com/"), "Link rom phai tro den Google Drive")

    def test_game_store_menu_items(self):
        """Kiem tra menu Game Store: khong con Game Viet Hoa, co du GDRIVE, RETROSTIC, ARCHIVE."""
        store = StoreScreen(self.engine)
        store.show_menu()
        item_ids = [it["id"] for it in store.items]
        
        # Bỏ game Việt Hóa
        self.assertNotIn("cat_viet", item_ids, "Game Store khong duoc chua cat_viet")

        # Phải có: Tìm kiếm, Top 100, JAVA, Hack, Retrostic, GDrive, Archive, Back
        expected_ids = ["nav_search", "cat_hits", "cat_java", "cat_hack", "cat_retrostic", "cat_gdrive", "cat_archive", "back"]
        self.assertEqual(item_ids, expected_ids, "Danh sach menu Game Store phai dung thu tu yeu cau")

    def test_retro_store_grid_navigation(self):
        """Kiem tra man hinh Retro Store 3x2 Grid va dieu huong D-pad."""
        rs = RetroStoreScreen(self.engine)
        rs.on_enter()
        self.assertEqual(len(rs.items), 6, "Retro Store phai co dung 6 o (Grid 3x2)")
        
        # O 1: Game Store
        self.assertEqual(rs.items[0]["id"], "item_games")
        # O 2: Theme Store
        self.assertEqual(rs.items[1]["id"], "item_themes")
        # O 3: Icon Store
        self.assertEqual(rs.items[2]["id"], "item_icons")
        # O 4: Emus Store
        self.assertEqual(rs.items[3]["id"], "item_emus")
        # O 5: Cheat Code
        self.assertEqual(rs.items[4]["id"], "item_cheats")
        # O 6: Cao Boxart (thay cho Quan ly Save)
        self.assertEqual(rs.items[5]["id"], "item_boxart")

        # Test dieu huong D-pad
        rs.selected_idx = 0  # Row 0, Col 0
        rs.handle_input({"btn_right": True})
        self.assertEqual(rs.selected_idx, 1, "Bam Phai tu o 0 phai sang o 1")
        rs.handle_input({"btn_down": True})
        self.assertEqual(rs.selected_idx, 4, "Bam Xuong tu o 1 (hang 0) phai sang o 4 (hang 1)")
        rs.handle_input({"btn_left": True})
        self.assertEqual(rs.selected_idx, 3, "Bam Trai tu o 4 phai sang o 3")
        rs.handle_input({"btn_up": True})
        self.assertEqual(rs.selected_idx, 0, "Bam Len tu o 3 phai quay ve o 0")

        # Test chon A
        rs.selected_idx = 0
        rs.handle_input({"btn_a": True})
        self.assertEqual(self.engine.screen_stack[-1], "store", "Chon o 0 phai mo man hinh store")

        rs.selected_idx = 1
        rs.handle_input({"btn_a": True})
        self.assertEqual(self.engine.screen_stack[-1], "theme_store", "Chon o 1 phai mo theme_store")

        rs.selected_idx = 5
        rs.handle_input({"btn_a": True})
        self.assertTrue(len(self.engine.modal_stack) > 0, "Chon o 5 phai mo modal")
        modal_obj = self.engine.modal_stack[-1][0]
        self.assertEqual(modal_obj.__class__.__name__, "BoxartScraperModal", "O 5 phai mo BoxartScraperModal")

    def test_home_screen_order(self):
        """Kiem tra HomeScreen: Retro Store xep thu 3 sau YouTube, khong con nav_rom_store_menu o stt 5."""
        home = HomeScreen(self.engine)
        home.on_enter()
        item_ids = [it["id"] for it in home.items]

        # Vi tri 0: nav_library, vi tri 1: nav_youtube, vi tri 2: nav_retro_store
        self.assertEqual(item_ids[0], "nav_library")
        self.assertEqual(item_ids[1], "nav_youtube")
        self.assertEqual(item_ids[2], "nav_retro_store", "Retro Store phai xep thu 3 tren Home Menu")

        # Khong con nav_rom_store_menu tren Home
        self.assertNotIn("nav_rom_store_menu", item_ids, "nav_rom_store_menu phai duoc bo khoi Home")

        # Bam A vao nav_retro_store phai push screen "retro_store"
        home.selected_idx = 2
        home.handle_input({"btn_a": True})
        self.assertEqual(self.engine.screen_stack[-1], "retro_store")

    def test_utilities_screen_no_stores(self):
        """Kiem tra UtilitiesScreen: Theme, Icon, Emus Store da duoc chuyen sang Retro Store, bo boxart va cheat."""
        util = UtilitiesScreen(self.engine)
        util.on_enter()
        item_ids = [it["id"] for it in util.items]
        self.assertNotIn("nav_theme_store", item_ids, "nav_theme_store khong con trong Utilities")
        self.assertNotIn("nav_icon_store", item_ids, "nav_icon_store khong con trong Utilities")
        self.assertNotIn("nav_emu_store", item_ids, "nav_emu_store khong con trong Utilities")
        self.assertNotIn("nav_auto_scrape", item_ids, "nav_auto_scrape khong con trong Utilities")
        self.assertNotIn("nav_cheats", item_ids, "nav_cheats khong con trong Utilities")
        self.assertIn("nav_save_manager", item_ids, "nav_save_manager van phai o trong Utilities")

    def test_gdrive_priority_and_candidate_sorting(self):
        """Kiem tra candidate tu downloader va mirror priority uu tien GDRIVE."""
        from rh.downloader import get_game_url_candidates
        game_mock = {
            "id": 999999,
            "title": "Test Game",
            "source_name": "RETROSTIC",
            "rom_url": "https://www.retrostic.com/test.zip",
            "mirrors": [
                {"source": "ARCHIVE", "url": "https://archive.org/download/test.zip", "priority": 1},
                {"source": "GDRIVE", "url": "https://drive.google.com/file/d/test12345/view", "priority": 2},
            ]
        }
        candidates = get_game_url_candidates(game_mock)
        self.assertTrue(len(candidates) >= 2)
        # GDRIVE phai duoc uu tien dua len vi tri dau tien
        self.assertTrue(
            "drive.google.com" in candidates[0] or "drive.usercontent.google.com" in candidates[0],
            f"Candidate dau tien phai la GDRIVE, nhan duoc: {candidates[0]}"
        )


if __name__ == "__main__":
    unittest.main()
