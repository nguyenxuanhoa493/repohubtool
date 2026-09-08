# -*- coding: utf-8 -*-
"""Quản lý tải và tích hợp kho mã Cheat Code Libretro Official cho RetroArch.

Hỗ trợ 2 chế độ:
1. Tải cho game đang có: Quét game trên thẻ nhớ, đối chiếu với danh sách
   mã Cheat Libretro (28.000 file), chỉ tải trực tiếp từng file .cht tương ứng
   từ CDN jsdelivr / GitHub raw (chỉ vài trăm KB thay vì 37MB). Tự động tạo bản
   sao {rom_basename}.cht để RetroArch tự kích hoạt (Auto-Load).
2. Tải toàn bộ kho (~37MB): Tải file cheats.zip từ buildbot Libretro và giải nén.
"""

import os
import re
import sys
import time
import json
import gzip
import zipfile
import threading
import urllib.request
import urllib.parse
import urllib.error
import ssl
import concurrent.futures

try:
    _SSL_CONTEXT = ssl.create_default_context()
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CONTEXT = None

SDCARD_PATH = os.environ.get("SDCARD_PATH") or (
    "/mnt/SDCARD" if os.path.isdir("/mnt/SDCARD")
    else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_mock_sdcard")
)

LIBRETRO_CHEATS_URL = "https://buildbot.libretro.com/assets/frontend/cheats.zip"
CHEATS_INDEX_FILENAME = "cheats_index.json.gz"

LIBRETRO_SYSTEM_MAP = {
    "GBA": ["Nintendo - Game Boy Advance"],
    "GBC": ["Nintendo - Game Boy Color"],
    "GB": ["Nintendo - Game Boy"],
    "FC": ["Nintendo - Nintendo Entertainment System", "Nintendo - Family Computer Disk System"],
    "NES": ["Nintendo - Nintendo Entertainment System", "Nintendo - Family Computer Disk System"],
    "SFC": ["Nintendo - Super Nintendo Entertainment System"],
    "SNES": ["Nintendo - Super Nintendo Entertainment System"],
    "MD": ["Sega - Mega Drive - Genesis", "Sega - Master System - Mark III"],
    "GENESIS": ["Sega - Mega Drive - Genesis"],
    "GG": ["Sega - Game Gear"],
    "SMS": ["Sega - Master System - Mark III"],
    "SEGACD": ["Sega - Mega-CD - Sega CD"],
    "32X": ["Sega - 32X"],
    "PS": ["Sony - PlayStation"],
    "PS1": ["Sony - PlayStation"],
    "PSX": ["Sony - PlayStation"],
    "PSP": ["Sony - PlayStation Portable"],
    "N64": ["Nintendo - Nintendo 64"],
    "NDS": ["Nintendo - Nintendo DS"],
    "PCE": ["NEC - PC Engine - TurboGrafx 16", "NEC - PC Engine CD - TurboGrafx-CD"],
    "TG16": ["NEC - PC Engine - TurboGrafx 16"],
    "PCECD": ["NEC - PC Engine CD - TurboGrafx-CD"],
    "PCFX": ["NEC - PC-FX"],
    "WSC": ["Bandai - WonderSwan Color"],
    "WS": ["Bandai - WonderSwan"],
    "NGP": ["SNK - Neo Geo Pocket", "SNK - Neo Geo Pocket Color"],
    "NGPC": ["SNK - Neo Geo Pocket Color"],
    "ARCADE": ["FBNeo - Arcade Games", "MAME"],
    "FBNEO": ["FBNeo - Arcade Games"],
    "MAME": ["MAME"],
    "CPS1": ["FBNeo - Arcade Games", "Capcom - CP System I"],
    "CPS2": ["FBNeo - Arcade Games", "Capcom - CP System II"],
    "CPS3": ["FBNeo - Arcade Games", "Capcom - CP System III"],
    "NEOGEO": ["SNK - Neo Geo", "FBNeo - Arcade Games"],
    "ATARI2600": ["Atari - 2600"],
    "ATARI7800": ["Atari - 7800"],
    "LYNX": ["Atari - Lynx"],
    "VECTREX": ["GCE - Vectrex"],
    "GW": ["Handheld Electronic Game"],
    "POKEMINI": ["Nintendo - Pokémon Mini"],
    "VB": ["Nintendo - Virtual Boy"],
    "SG1000": ["Sega - SG-1000"],
    "MSX": ["Microsoft - MSX", "Microsoft - MSX2"],
    "ZXS": ["Sinclair - ZX Spectrum"],
    "AMIGA": ["Commodore - Amiga"],
    "DOS": ["DOS"],
}


def get_cheats_dir(base_sd=None):
    sd = base_sd or SDCARD_PATH
    primary = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
    if os.path.isdir(primary):
        return primary
    secondary = os.path.join(sd, "RetroArch", "cheats")
    if os.path.isdir(secondary):
        return secondary
    return primary


def count_cheats(base_sd=None):
    c_dir = get_cheats_dir(base_sd)
    if not os.path.isdir(c_dir):
        return 0
    cnt = 0
    try:
        for root, _, files in os.walk(c_dir):
            for f in files:
                if f.lower().endswith(".cht"):
                    cnt += 1
    except OSError:
        pass
    return cnt


def get_cheats_status(base_sd=None):
    c_dir = get_cheats_dir(base_sd)
    cnt = count_cheats(base_sd)
    return {
        "installed": cnt > 0,
        "count": cnt,
        "dir": c_dir
    }


def clean_game_title(title):
    t = re.sub(r'\(.*?\)|\[.*?\]', '', title)
    t = re.sub(r'^\d+\s*[-_.]\s*', '', t)
    t = re.sub(r'\.cht$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[^a-zA-Z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t


def scan_installed_games(base_sd=None):
    sd = base_sd or SDCARD_PATH
    roms_dir = os.path.join(sd, "Roms")
    installed_map = {}

    if not os.path.isdir(roms_dir):
        return installed_map

    ignored_exts = {".png", ".jpg", ".jpeg", ".xml", ".db", ".txt", ".json", ".cfg", ".sav", ".srm", ".state"}

    try:
        entries = sorted(os.listdir(roms_dir))
        for entry in entries:
            sys_folder = os.path.join(roms_dir, entry)
            if not os.path.isdir(sys_folder) or entry.startswith("."):
                continue

            sys_code = entry.upper()
            target_libretro_sys = LIBRETRO_SYSTEM_MAP.get(sys_code, [entry])

            try:
                rom_files = []
                for rf in os.listdir(sys_folder):
                    if rf.startswith("."):
                        continue
                    ext = os.path.splitext(rf)[1].lower()
                    if ext not in ignored_exts and os.path.isfile(os.path.join(sys_folder, rf)):
                        rom_files.append(rf)
            except OSError:
                continue

            if not rom_files:
                continue

            for rf in rom_files:
                base = os.path.splitext(rf)[0]
                cln = clean_game_title(base)
                w = set(word for word in cln.split() if len(word) > 1)
                item = {
                    "rom_filename": rf,
                    "rom_basename": base,
                    "clean_title": cln,
                    "words": w
                }
                for l_sys in target_libretro_sys:
                    if l_sys not in installed_map:
                        installed_map[l_sys] = []
                    installed_map[l_sys].append(item)
    except OSError:
        pass

    return installed_map


_CHEATS_INDEX_CACHE = None

def get_cheats_index():
    global _CHEATS_INDEX_CACHE
    if _CHEATS_INDEX_CACHE is not None:
        return _CHEATS_INDEX_CACHE

    paths_to_check = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), CHEATS_INDEX_FILENAME),
        os.path.join(SDCARD_PATH, "Apps", "RetroHub", "rh", CHEATS_INDEX_FILENAME),
        os.path.join(SDCARD_PATH, "RetroArch", CHEATS_INDEX_FILENAME),
    ]

    for p in paths_to_check:
        if os.path.isfile(p):
            try:
                with gzip.open(p, "rb") as f:
                    _CHEATS_INDEX_CACHE = json.loads(f.read().decode("utf-8"))
                    return _CHEATS_INDEX_CACHE
            except Exception:
                pass

    index_url = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main/files/rh/cheats_index.json.gz"
    try:
        req = urllib.request.Request(index_url, headers={"User-Agent": "RetroHub-TrimUI/1.94"})
        urlopen_kw = {"timeout": 15}
        if _SSL_CONTEXT is not None:
            urlopen_kw["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **urlopen_kw) as resp:
            compressed = resp.read()
            _CHEATS_INDEX_CACHE = json.loads(gzip.decompress(compressed).decode("utf-8"))
            try:
                with open(paths_to_check[0], "wb") as sf:
                    sf.write(compressed)
            except Exception:
                pass
            return _CHEATS_INDEX_CACHE
    except Exception:
        pass

    return {}


def match_cht_with_installed(cht_filename, installed_games_for_sys):
    cht_clean = clean_game_title(cht_filename)
    cht_words = set(w for w in cht_clean.split() if len(w) > 1)

    for g in installed_games_for_sys:
        r_clean = g["clean_title"]
        r_words = g["words"]

        if r_clean == cht_clean:
            return g

        if len(r_clean) >= 4 and len(cht_clean) >= 4:
            if r_clean in cht_clean or cht_clean in r_clean:
                return g

        if r_words and r_words.issubset(cht_words):
            return g

        if r_words and cht_words:
            inter = len(r_words.intersection(cht_words))
            ratio = inter / max(len(r_words), len(cht_words))
            if ratio >= 0.75:
                return g

    return None


def match_rom_with_available_cheats(game_dict, available_cheats):
    r_clean = game_dict["clean_title"]
    r_words = game_dict["words"]

    for cht in available_cheats:
        if r_clean == clean_game_title(cht):
            return cht

    if len(r_clean) >= 4:
        for cht in available_cheats:
            c_clean = clean_game_title(cht)
            if len(c_clean) >= 4 and (r_clean in c_clean or c_clean in r_clean):
                return cht

    if len(r_words) >= 2:
        for cht in available_cheats:
            c_clean = clean_game_title(cht)
            c_words = set(w for w in c_clean.split() if len(w) > 1)
            if r_words.issubset(c_words):
                return cht

    return None


def find_cheats_to_download(installed_map, index):
    tasks = []
    seen = set()

    for l_sys, games in installed_map.items():
        if l_sys not in index:
            continue
        cheats = index[l_sys]
        if not cheats:
            continue

        for g in games:
            found = match_rom_with_available_cheats(g, cheats)
            if found and (l_sys, found) not in seen:
                seen.add((l_sys, found))
                tasks.append((l_sys, found, g["rom_basename"]))

    return tasks


def download_single_cht_content(sys_part, cht_file):
    enc_sys = urllib.parse.quote(sys_part)
    enc_cht = urllib.parse.quote(cht_file)
    urls = [
        f"https://cdn.jsdelivr.net/gh/libretro/libretro-database@master/cht/{enc_sys}/{enc_cht}",
        f"https://raw.githubusercontent.com/libretro/libretro-database/master/cht/{enc_sys}/{enc_cht}",
    ]
    urlopen_kw = {"timeout": 8}
    if _SSL_CONTEXT is not None:
        urlopen_kw["context"] = _SSL_CONTEXT

    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "RetroHub-TrimUI/1.94"})
            with urllib.request.urlopen(req, **urlopen_kw) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            continue
    return None


def check_or_download_single_cheat(sys_code, rom_filename, base_sd=None):
    sd = base_sd or SDCARD_PATH
    primary_dir = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
    rom_base = os.path.splitext(rom_filename)[0]

    code = re.sub(r'\(.*?\)|\[.*?\]', '', sys_code).strip().upper()
    libretro_systems = LIBRETRO_SYSTEM_MAP.get(code, [sys_code])

    for l_sys in libretro_systems:
        target_cht = os.path.join(primary_dir, l_sys, f"{rom_base}.cht")
        if os.path.isfile(target_cht):
            return {"ok": True, "exists": True, "path": target_cht, "message": "Game này đã có sẵn file Cheat trên máy."}

    idx = get_cheats_index()
    for l_sys in libretro_systems:
        available_cheats = idx.get(l_sys, [])
        cln = clean_game_title(rom_base)
        w = set(word for word in cln.split() if len(word) > 1)
        g = {"clean_title": cln, "words": w, "rom_basename": rom_base}
        matched_cht = match_rom_with_available_cheats(g, available_cheats)
        if matched_cht:
            content = download_single_cht_content(l_sys, matched_cht)
            if content:
                sys_dest = os.path.join(primary_dir, l_sys)
                os.makedirs(sys_dest, exist_ok=True)
                target_file = os.path.join(sys_dest, f"{rom_base}.cht")
                with open(target_file, "wb") as f:
                    f.write(content)
                orig_file = os.path.join(sys_dest, matched_cht)
                if not os.path.isfile(orig_file):
                    try:
                        with open(orig_file, "wb") as of:
                            of.write(content)
                    except Exception:
                        pass
                return {"ok": True, "downloaded": True, "path": target_file, "message": "Đã tải file Cheat thành công!"}

    return {"ok": False, "message": "Chưa có file Cheat trong kho Libretro cho game này."}


class CheatDownloaderRunner:
    """Điều phối tải kho mã Cheat Code chạy nền."""

    def __init__(self):
        self.active = False
        self.done = False
        self.stop_requested = False
        self.phase = "idle"
        self.mode = "installed"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.progress_pct = 0
        self.speed_bps = 0
        self.status_msg = ""
        self.extracted_count = 0
        self.matched_games_count = 0
        self.total_installed_games = 0
        self.total_to_download = 0
        self.downloaded_count = 0
        self.error_msg = ""
        self._lock = threading.Lock()
        self._thread = None

    def is_running(self):
        return self.active and not self.done

    def get_state(self):
        with self._lock:
            return {
                "active": self.active,
                "running": self.is_running(),
                "done": self.done,
                "stop_requested": self.stop_requested,
                "phase": self.phase,
                "mode": self.mode,
                "downloaded_bytes": self.downloaded_bytes,
                "total_bytes": self.total_bytes,
                "progress_pct": self.progress_pct,
                "speed_bps": self.speed_bps,
                "status_msg": self.status_msg,
                "extracted_count": self.extracted_count,
                "matched_games_count": self.matched_games_count,
                "total_installed_games": self.total_installed_games,
                "total_to_download": self.total_to_download,
                "downloaded_count": self.downloaded_count,
                "error_msg": self.error_msg,
            }

    def request_stop(self):
        self.stop_requested = True
        with self._lock:
            self.status_msg = "Đang dừng tải Cheat Code..."

    def start(self, base_sd=None, url=None, mode="installed"):
        if self.active and not self.done:
            return False

        self.active = True
        self.done = False
        self.stop_requested = False
        self.mode = mode
        self.phase = "scanning" if mode == "installed" else "downloading"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.progress_pct = 0
        self.speed_bps = 0
        self.status_msg = "Đang quét danh sách game trên máy..." if mode == "installed" else "Bắt đầu kết nối tải kho Cheat..."
        self.extracted_count = 0
        self.matched_games_count = 0
        self.total_installed_games = 0
        self.total_to_download = 0
        self.downloaded_count = 0
        self.error_msg = ""

        self._thread = threading.Thread(
            target=self._run,
            args=(base_sd, url),
            daemon=True
        )
        self._thread.start()
        return True

    def _run(self, base_sd=None, url=None):
        sd = base_sd or SDCARD_PATH
        primary_dir = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
        secondary_dir = os.path.join(sd, "RetroArch", "cheats")
        os.makedirs(primary_dir, exist_ok=True)
        os.makedirs(secondary_dir, exist_ok=True)
        self._run_installed(sd, primary_dir, secondary_dir)

    def _run_installed(self, sd, primary_dir, secondary_dir):
        """Chế độ thông minh: Chỉ tải các file cheat của game đang có từ CDN."""
        try:
            with self._lock:
                self.phase = "scanning"
                self.status_msg = "Đang quét danh sách game trên thẻ nhớ..."

            installed = scan_installed_games(sd)
            total_roms = sum(len(v) for v in installed.values())

            with self._lock:
                self.total_installed_games = total_roms

            if total_roms == 0:
                with self._lock:
                    self.done = True
                    self.active = False
                    self.phase = "error"
                    self.status_msg = "Chưa có game nào trong thư mục Roms để tải Cheat."
                return

            with self._lock:
                self.phase = "matching"
                self.status_msg = f"Đang đối chiếu mã Cheat cho {total_roms} game..."

            idx = get_cheats_index()
            tasks = find_cheats_to_download(installed, idx)

            if not tasks:
                with self._lock:
                    self.done = True
                    self.active = False
                    self.phase = "done"
                    self.progress_pct = 100
                    self.status_msg = "Không tìm thấy mã Cheat phù hợp cho các game đang có."
                return

            with self._lock:
                self.phase = "downloading"
                self.total_to_download = len(tasks)
                self.downloaded_count = 0
                self.status_msg = f"Tìm thấy {len(tasks)} mã Cheat. Bắt đầu tải..."

            downloaded = 0
            downloaded_bytes = 0
            start_t = time.time()
            matched_games = set()

            def fetch_and_save(task):
                if self.stop_requested:
                    return None
                sys_part, cht_file, rom_base = task
                content = download_single_cht_content(sys_part, cht_file)
                if not content:
                    return None

                for base_dir in (primary_dir, secondary_dir):
                    if not os.path.isdir(base_dir):
                        continue
                    dest_sys = os.path.join(base_dir, sys_part)
                    os.makedirs(dest_sys, exist_ok=True)
                    orig_f = os.path.join(dest_sys, cht_file)
                    with open(orig_f, "wb") as f:
                        f.write(content)
                    alias_f = os.path.join(dest_sys, f"{rom_base}.cht")
                    if not os.path.isfile(alias_f):
                        try:
                            with open(alias_f, "wb") as af:
                                af.write(content)
                        except Exception:
                            pass
                return (sys_part, rom_base, len(content))

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(fetch_and_save, t) for t in tasks]
                for fut in concurrent.futures.as_completed(futures):
                    if self.stop_requested:
                        break
                    res = fut.result()
                    if res:
                        sys_p, rom_b, byte_cnt = res
                        downloaded += 1
                        downloaded_bytes += byte_cnt
                        matched_games.add((sys_p, rom_b))

                    now = time.time()
                    elapsed = max(0.001, now - start_t)
                    speed = downloaded_bytes / elapsed

                    pct = min(99, int((downloaded / len(tasks)) * 100))
                    with self._lock:
                        self.downloaded_count = downloaded
                        self.downloaded_bytes = downloaded_bytes
                        self.progress_pct = pct
                        self.speed_bps = speed
                        self.status_msg = f"Đang tải: {downloaded}/{len(tasks)} mã Cheat ({speed/1024:.0f} KB/s)..."

            if self.stop_requested:
                with self._lock:
                    self.done = True
                    self.active = False
                    self.status_msg = "Đã hủy tải Cheat Code!"
                return

            size_kb = downloaded_bytes / 1024
            with self._lock:
                self.done = True
                self.active = False
                self.phase = "done"
                self.progress_pct = 100
                self.extracted_count = downloaded
                self.matched_games_count = len(matched_games)
                self.status_msg = f"Hoàn tất! Đã tải {downloaded} mã Cheat ({size_kb:.0f} KB) cho {len(matched_games)} game."

        except Exception as e:
            with self._lock:
                self.done = True
                self.active = False
                self.phase = "error"
                self.error_msg = str(e)
                self.status_msg = f"Lỗi tải Cheat: {str(e)}"


cheat_runner = CheatDownloaderRunner()
