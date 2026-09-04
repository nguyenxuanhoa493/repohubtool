# -*- coding: utf-8 -*-
"""The ROM catalogue: local scans, system names, and building list views."""

import os

from .paths import SDCARD_PATH
from . import state

try:
    import db
except Exception:
    db = None

VALID_EXTS = (
    ".gba", ".sfc", ".smc", ".nes", ".nds", ".md", ".gen", ".gb", ".gbc", ".gg", ".sms", 
    ".p8", ".png", ".zip", ".7z", ".rar", ".jar", ".jad", ".iso", ".cso", ".chd", ".pbp", 
    ".cue", ".bin", ".wsc", ".ws", ".ngp", ".ngc", ".pce", ".n64", ".z64", ".v64", ".cdi", 
    ".gdi", ".a26", ".a78", ".lnx", ".fig", ".smd"
)

def scan_all_downloaded_games():
    """Scans all folders in /mnt/SDCARD/Roms/ to list all downloaded games across all systems."""
    results = []
    roms_root = f"{SDCARD_PATH}/Roms"
    if not os.path.exists(roms_root):
        return results

    try:
        sys_dirs = [d for d in os.listdir(roms_root) if os.path.isdir(os.path.join(roms_root, d)) and not d.startswith(".")]
    except Exception:
        sys_dirs = []

    for sys_code in sorted(sys_dirs):
        if sys_code in ("HITS", "VIET", "TOPO", "FAV"):
            continue

        actual_code = sys_code
        if "(" in sys_code and sys_code.endswith(")"):
            extracted = sys_code[sys_code.rfind("(") + 1:-1].strip().upper()
            if extracted:
                actual_code = extracted

        rom_dir = os.path.join(roms_root, sys_code)
        img_dir = f"{SDCARD_PATH}/Imgs/{actual_code}"
        # ROM folders are commonly one level deep, and J2ME depends on it: the
        # launcher reads the screen size from a folder named like 240320. Scan the
        # system folder plus one level below it.
        scan_dirs = [rom_dir]
        try:
            for sub in sorted(os.listdir(rom_dir)):
                p = os.path.join(rom_dir, sub)
                if os.path.isdir(p) and not sub.startswith("."):
                    scan_dirs.append(p)
        except Exception:
            pass

        try:
            for scan_dir in scan_dirs:
                with os.scandir(scan_dir) as entries:
                    for entry in sorted(entries, key=lambda e: e.name.lower()):
                        if not entry.is_file():
                            continue
                        name = entry.name
                        if name.startswith(".") or not name.lower().endswith(VALID_EXTS):
                            continue

                        try: sz = entry.stat().st_size
                        except: sz = 0
                        sz_str = f"{sz / (1024*1024):.1f} MB" if sz > 1024*1024 else f"{sz // 1024} KB"

                        base_name = os.path.splitext(name)[0]
                        if base_name.endswith(".p8"):
                            base_name = os.path.splitext(base_name)[0]

                        img_p = os.path.join(img_dir, f"{base_name}.png")
                        if not os.path.exists(img_p):
                            img_p = os.path.join(img_dir, f"{base_name}.jpg")
                        if not os.path.exists(img_p):
                            media_p = os.path.join(rom_dir, ".media", f"{base_name}.png")
                            if os.path.exists(media_p):
                                img_p = media_p
                            else:
                                sub_media = os.path.join(scan_dir, ".media", f"{base_name}.png")
                                img_p = sub_media if os.path.exists(sub_media) else None

                        results.append({
                            "sys_code": actual_code,
                            "sys_name": get_system_display_name(actual_code),
                            "title": base_name,
                            "filename": name,
                            "rom_path": entry.path,
                            "img_path": img_p,
                            "size_str": sz_str
                        })
        except Exception:
            continue
    return results
SYSTEM_NAMES = {
    "MAME": "Arcade (MAME)",
    "ATARI2600": "Atari 2600",
    "ATARI7800": "Atari 7800",
    "LYNX": "Atari Lynx",
    "PCE": "PC Engine / TurboGrafx-16",
    "SS": "Sega Saturn",
    "DC": "Sega Dreamcast",
    "NGP": "Neo Geo Pocket",
    "WS": "WonderSwan",
    "WSC": "WonderSwan Color",
    "GBA": "Game Boy Advance (GBA)",
    "SFC": "Super Nintendo (SFC / SNES)",
    "FC": "NES / Famicom (FC)",
    "MD": "Sega Genesis (MD / Mega Drive)",
    "GB": "Game Boy (GB)",
    "GBC": "Game Boy Color (GBC)",
    "GG": "Sega Game Gear (GG)",
    "MS": "Sega Master System (MS)",
    "NDS": "Nintendo DS (NDS)",
    "3DS": "Nintendo 3DS (3DS)",
    "N64": "Nintendo 64 (N64)",
    "PS": "Sony PlayStation (PS1)",
    "PS1": "Sony PlayStation (PS1)",
    "PSP": "PlayStation Portable (PSP)",
    "PICO8": "PICO-8 (Indie Games)",
    "ARCADE": "Arcade / NeoGeo / CPS",
    "NEOGEO": "SNK NeoGeo (NEOGEO)",
    "CPS1": "Capcom CPS-1 (CPS1)",
    "CPS2": "Capcom CPS-2 (CPS2)",
    "CPS3": "Capcom CPS-3 (CPS3)",
    "JAVA": "Java J2ME (Mobile .jar)",
    "J2ME": "Java J2ME (Mobile .jar)",
    "RETROSTIC": "Retrostic CDN",
    "ARCHIVE": "Internet Archive",
    "VIET": "Game Việt Hóa",
    "HITS": "Top 100 Game Hay",
    "TOPO": "Nguồn Game TopoShop"
}

def get_system_display_name(code):
    if code in SYSTEM_NAMES:
        return SYSTEM_NAMES[code]
    if code in state.catalogs and "system_name" in state.catalogs[code]:
        return state.catalogs[code]["system_name"]
    return code

def get_source_systems_list(src_code):
    """Returns a list of (sys_code, count) for the given source using SQLite DAO."""
    if db and os.path.exists(db.DB_PATH):
        try:
            return db.get_source_systems_counts(src_code)
        except Exception as e:
            print(f"DB get_source_systems_counts error: {e}")

    # Fallback to in-memory catalogs dict
    if src_code == "ARCHIVE":
        archive_keys = ["GBA", "SFC", "FC", "MD", "GB", "GBC", "GG", "MS", "NDS", "PICO8", "ARCADE"]
        res = []
        total = 0
        for k in archive_keys:
            c = len(state.catalogs.get(k, {}).get("games", []))
            if c > 0:
                res.append((k, c))
                total += c
        return [("ALL", total)] + res
    elif src_code == "ALL":
        sys_counts = {}
        total = 0
        for k, v in state.catalogs.items():
            for g in v.get("games", []):
                sc = g.get("sys_code") or k
                sys_counts[sc] = sys_counts.get(sc, 0) + 1
                total += 1
        sorted_sys = sorted(sys_counts.items(), key=lambda x: -x[1])
        return [("ALL", total)] + sorted_sys
    else:
        games = state.catalogs.get(src_code, {}).get("games", [])
        total = len(games)
        sys_counts = {}
        for g in games:
            sc = g.get("sys_code") or src_code
            sys_counts[sc] = sys_counts.get(sc, 0) + 1
        sorted_sys = sorted(sys_counts.items(), key=lambda x: -x[1])
        return [("ALL", total)] + sorted_sys

def get_java_category_list():
    """[(category, count)] for the J2ME shelves, or [] when the DB is absent."""
    if db and os.path.exists(db.DB_PATH):
        try:
            return db.get_java_categories()
        except Exception as e:
            print(f"DB get_java_categories error: {e}")
    return []


def alpha_index(games):
    """(vi_tri_dau_tien, so_luong) theo tung chu cai, tinh tren danh sach dua vao.

    Index chi co nghia trong dung mot thu tu, nen ham phai duoc goi voi chinh
    danh sach se hien ra sau khi nhay; dua nham thu tu thi bam "A" se roi vao
    mot game bat dau bang chu khac. Ten khong bat dau bang chu cai - "1942",
    "<unknown>", ten rong - deu ve chung ke "#"."""
    avail = {}
    counts = {}
    for idx, g in enumerate(games):
        title = (g.get("title") or "").strip().upper()
        ch = title[0] if title and title[0].isalpha() else "#"
        if ch not in avail:
            avail[ch] = idx
        counts[ch] = counts.get(ch, 0) + 1
    return avail, counts


_catalog_view_cache = {}

def clear_catalog_cache():
    global _catalog_view_cache
    _catalog_view_cache.clear()

def get_games_for_view(src_code, sys_code, sort_by=None, category=None):
    """Returns list of game dicts for the specified source and system filter using SQLite DAO.
    Caches raw rows in memory so switching sort mode or opening alphabet jump is instantaneous."""
    active_sort = sort_by or state.rom_sort_mode
    base_key = (src_code, sys_code, category)

    if base_key in _catalog_view_cache:
        raw_games = _catalog_view_cache[base_key]
    else:
        raw_games = None
        if db and os.path.exists(db.DB_PATH):
            try:
                raw_games = db.get_games_page(src_code, sys_code, sort_by="downloads",
                                              category=category)
            except Exception as e:
                print(f"DB get_games_page error: {e}")

        if raw_games is None:
            # Fallback to in-memory catalogs dict
            if src_code == "VIET":
                games = state.catalogs.get("VIET", {}).get("games", [])
            elif src_code == "HITS":
                games = state.catalogs.get("HITS", {}).get("games", [])
            elif src_code == "ARCHIVE":
                if sys_code != "ALL":
                    games = state.catalogs.get(sys_code, {}).get("games", [])
                else:
                    archive_keys = ["GBA", "SFC", "FC", "MD", "GB", "GBC", "GG", "MS", "NDS", "PICO8", "ARCADE"]
                    games = []
                    for k in archive_keys:
                        games.extend(state.catalogs.get(k, {}).get("games", []))
                raw_games = games
            elif src_code == "ALL":
                if sys_code != "ALL":
                    res = []
                    for k, v in state.catalogs.items():
                        for g in v.get("games", []):
                            if (g.get("sys_code") or k) == sys_code:
                                res.append(g)
                    raw_games = res
                else:
                    games = []
                    for k, v in state.catalogs.items():
                        games.extend(v.get("games", []))
                    raw_games = games
            else:
                games = state.catalogs.get(src_code, {}).get("games", [])
                if sys_code == "ALL":
                    raw_games = games
                else:
                    raw_games = [g for g in games if (g.get("sys_code") or src_code) == sys_code]

        if len(_catalog_view_cache) > 8:
            _catalog_view_cache.pop(next(iter(_catalog_view_cache)))
        _catalog_view_cache[base_key] = raw_games

    # Instant C-level Timsort in Python memory
    res = list(raw_games)
    if active_sort == "downloads":
        res.sort(key=lambda g: (-int(g.get("download_count") or 0), (g.get("title") or "").strip().lower()))
    elif active_sort == "rating":
        res.sort(key=lambda g: (-float(g.get("rating") or 0), -int(g.get("download_count") or 0)))
    else: # title / alpha / A-Z
        res.sort(key=lambda g: ((g.get("title") or "").strip().lower(), -int(g.get("download_count") or 0)))

    return res
