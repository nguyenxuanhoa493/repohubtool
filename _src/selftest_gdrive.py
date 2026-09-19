#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest cho chuc nang Google Drive Resolver va Thu vien Game Drive (headless, offline).

    python _src/selftest_gdrive.py
"""

import os
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")

SD = tempfile.mkdtemp(prefix="rh-gdrive-")
os.environ["SDCARD_PATH"] = SD
sys.path.insert(0, FILES)
sys.modules.setdefault("db", None)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from rh import gdrive

def test_extract_file_id():
    cases = [
        ("https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view?usp=sharing", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
        ("https://drive.google.com/open?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
        ("https://drive.google.com/uc?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs&export=download", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
        ("https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs?usp=drive_link", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
        ("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
        ("   https://drive.google.com/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/view   ", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"),
    ]
    for url, expected in cases:
        fid = gdrive.extract_file_id(url)
        assert fid == expected, f"Expected {expected}, got {fid} for {url}"
    print("[PASS] test_extract_file_id")

def test_folder_rejection():
    try:
        gdrive.resolve_gdrive_info("https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs")
        assert False, "Should have raised ValueError for folder URL"
    except ValueError as e:
        assert "Thu muc" in str(e)
    print("[PASS] test_folder_rejection")

def test_parse_confirm_html():
    mock_html = """
    <html>
    <head><title>Google Drive - Can't scan file for viruses</title></head>
    <body>
      <span class="uc-name-size"><a href="#">Pokemon_Emerald_VI.gba</a> (16.2M)</span>
      <form id="download-form" action="https://drive.usercontent.google.com/download" method="get">
        <input type="hidden" name="id" value="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs">
        <input type="hidden" name="export" value="download">
        <input type="hidden" name="confirm" value="t_abc123">
        <input type="hidden" name="uuid" value="9876-uuid-xyz">
        <input type="submit" value="Download anyway">
      </form>
    </body>
    </html>
    """
    direct_link, filename, file_ext, file_size = gdrive.parse_download_page_html(mock_html, "default_url")
    assert filename == "Pokemon_Emerald_VI.gba", f"Filename mismatch: {filename}"
    assert file_ext == "gba", f"File ext mismatch: {file_ext}"
    assert file_size == "16.2M", f"File size mismatch: {file_size}"
    assert "confirm=t_abc123" in direct_link, f"confirm token missing: {direct_link}"
    assert "uuid=9876-uuid-xyz" in direct_link, f"uuid missing: {direct_link}"
    assert "id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs" in direct_link, f"id missing: {direct_link}"
    print("[PASS] test_parse_confirm_html")

def test_guess_system():
    cases = [
        ("Pokemon.gba", "GBA"),
        ("Super Mario World.sfc", "SFC"),
        ("Contra.nes", "FC"),
        ("Sonic.md", "MD"),
        ("Tekken.iso", "PS"),
        ("Crisis Core.cso", "PSP"),
        ("Harvest Moon.nds", "NDS"),
        ("Ninja School 3.jar", "JAVA"),
        ("Game.p8", "PICO8"),
        ("Pacman.zip", "ARCADE"),
    ]
    for fname, expected in cases:
        sys_code = gdrive.guess_system_from_filename(fname)
        assert sys_code == expected, f"Expected {expected}, got {sys_code} for {fname}"
    print("[PASS] test_guess_system")

def test_library_crud():
    initial = gdrive.load_gdrive_library()
    assert initial == [], f"Expected empty library, got {initial}"

    item1 = {
        "file_id": "file_123",
        "title": "Chrono Trigger VI",
        "filename": "Chrono_Trigger_VI.sfc",
        "file_size": "4.0 MB",
        "direct_link": "https://drive.usercontent.google.com/download?id=file_123",
        "suggested_sys": "SFC"
    }
    saved_item = gdrive.add_to_gdrive_library(item1)
    assert saved_item["id"] == "gdrive_file_123"

    lib = gdrive.load_gdrive_library()
    assert len(lib) == 1
    assert lib[0]["title"] == "Chrono Trigger VI"

    # Add duplicate should update instead of duplicating
    item1_updated = dict(item1)
    item1_updated["title"] = "Chrono Trigger Vietnamese Remaster"
    gdrive.add_to_gdrive_library(item1_updated)
    lib2 = gdrive.load_gdrive_library()
    assert len(lib2) == 1
    assert lib2[0]["title"] == "Chrono Trigger Vietnamese Remaster"

    # Delete item
    deleted = gdrive.delete_from_gdrive_library("gdrive_file_123")
    assert deleted is True
    assert len(gdrive.load_gdrive_library()) == 0
    print("[PASS] test_library_crud")

if __name__ == "__main__":
    try:
        test_extract_file_id()
        test_folder_rejection()
        test_parse_confirm_html()
        test_guess_system()
        test_library_crud()
        print("\nALL GDRIVE TESTS PASSED SUCCESSFULLY!")
    finally:
        shutil.rmtree(SD, ignore_errors=True)
