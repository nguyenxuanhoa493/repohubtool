# -*- coding: utf-8 -*-
"""Libretro Cheat Codes Downloader & Manager for TrimUI handheld devices:
Downloads official Libretro Cheats bundle (~37MB ZIP containing thousands of .cht files)
and selectively extracts cheats only for installed games or extracts all cheats.
"""

import os
import re
import ssl
import time
import zipfile
import threading
import urllib.request
import urllib.parse
from .paths import SDCARD_PATH

try:
    _SSL_CONTEXT = ssl.create_default_context()
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CONTEXT = None

LIBRETRO_CHEATS_URL = "http://buildbot.libretro.com/assets/frontend/cheats.zip"

LIBRETRO_SYSTEM_MAP = {
    "GBA": ["Nintendo - Game Boy Advance"],
    "GBC": ["Nintendo - Game Boy Color"],
    "GB": ["Nintendo - Game Boy"],
    "FC": ["Nintendo - Nintendo Entertainment System", "Nintendo - Family Computer Disk System"],
    "NES": ["Nintendo - Nintendo Entertainment System"],
    "SFC": ["Nintendo - Super Nintendo Entertainment System", "Nintendo - Satellaview"],
    "SNES": ["Nintendo - Super Nintendo Entertainment System"],
    "N64": ["Nintendo - Nintendo 64"],
    "NDS": ["Nintendo - Nintendo DS"],
    "MD": ["Sega - Mega Drive - Genesis"],
    "GENESIS": ["Sega - Mega Drive - Genesis"],
    "SEGACD": ["Sega - Mega-CD - Sega CD"],
    "GG": ["Sega - Game Gear"],
    "MS": ["Sega - Master System - Mark III"],
    "SS": ["Sega - Saturn"],
    "DC": ["Sega - Dreamcast"],
    "PS": ["Sony - PlayStation"],
    "PS1": ["Sony - PlayStation"],
    "PSP": ["Sony - PlayStation Portable"],
    "PCE": ["NEC - PC Engine - TurboGrafx 16", "NEC - PC Engine CD - TurboGrafx-CD", "NEC - PC Engine SuperGrafx"],
    "ATARI2600": ["Atari - 2600"],
    "ATARI5200": ["Atari - 5200"],
    "ATARI7800": ["Atari - 7800"],
    "LYNX": ["Atari - Lynx"],
    "ARCADE": ["FBNeo - Arcade Games"],
    "FBNEO": ["FBNeo - Arcade Games"],
    "CPS1": ["FBNeo - Arcade Games"],
    "CPS2": ["FBNeo - Arcade Games"],
    "CPS3": ["FBNeo - Arcade Games"],
    "MAME": ["FBNeo - Arcade Games"],
}

VALID_ROM_EXTS = {
    ".zip", ".7z", ".rar", ".nes", ".sfc", ".smc", ".gba", ".gbc", ".gb",
    ".md", ".gen", ".smd", ".bin", ".iso", ".cue", ".chd", ".pbp", ".nds",
    ".z64", ".n64", ".v64", ".pce", ".cso"
}


def clean_game_title(name):
    """Chuẩn hóa tên game để đối chiếu: bỏ phần mở rộng, bỏ dấu ngoặc đơn/vuông, bỏ ký tự đặc biệt."""
    base = re.sub(r'\.[a-zA-Z0-9]+$', '', name)
    base = re.sub(r'\s*\((?:Code Breaker|Action Replay|GameShark|Xploder|PAR|Cheats?|Raw)\)', '', base, flags=re.IGNORECASE)
    base = re.sub(r'\(.*?\)|\[.*?\]', '', base)
    base = re.sub(r'[^a-zA-Z0-9]+', ' ', base).lower().strip()
    return base


def get_cheats_dir(base_sd=None):
    """Lấy đường dẫn thư mục cheats chính của RetroArch."""
    sd = base_sd or SDCARD_PATH
    primary = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
    return primary


def get_cheats_status(base_sd=None):
    """Kiểm tra xem thư mục cheats đã được cài đặt chưa và đếm số lượng file .cht."""
    sd = base_sd or SDCARD_PATH
    c_dir = get_cheats_dir(sd)
    secondary = os.path.join(sd, "RetroArch", "cheats")

    target_dir = c_dir if os.path.isdir(c_dir) else secondary
    if not os.path.isdir(target_dir):
        return {"installed": False, "count": 0, "dir": c_dir}

    count = 0
    try:
        for root, _, files in os.walk(target_dir):
            for f in files:
                if f.lower().endswith(".cht"):
                    count += 1
    except OSError:
        pass

    return {
        "installed": count > 0,
        "count": count,
        "dir": target_dir
    }


def count_cheats(base_sd=None):
    """Đếm nhanh số mã cheat hiện có."""
    st = get_cheats_status(base_sd=base_sd)
    return st.get("count", 0)


def scan_installed_games(base_sd=None):
    """Quét các ROM hiện có trong thẻ nhớ và nhóm theo hệ máy Libretro."""
    sd = base_sd or SDCARD_PATH
    roms_base = os.path.join(sd, "Roms")
    if not os.path.isdir(roms_base):
        roms_base = os.path.join(sd, "Emus")
    if not os.path.isdir(roms_base):
        return {}

    installed_map = {}
    try:
        for sys_dir in os.listdir(roms_base):
            p = os.path.join(roms_base, sys_dir)
            if not os.path.isdir(p) or sys_dir.startswith("."):
                continue

            code = re.sub(r'\(.*?\)|\[.*?\]', '', sys_dir).strip().upper()
            target_libretro_sys = LIBRETRO_SYSTEM_MAP.get(code)
            if not target_libretro_sys:
                for k, v in LIBRETRO_SYSTEM_MAP.items():
                    if k == code or k in code or code in k:
                        target_libretro_sys = v
                        break
            if not target_libretro_sys:
                target_libretro_sys = [sys_dir]

            rom_files = []
            try:
                for f in os.listdir(p):
                    if f.startswith("."):
                        continue
                    ext = os.path.splitext(f)[1].lower()
                    if ext in VALID_ROM_EXTS:
                        rom_files.append(f)
            except OSError:
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


def match_cht_with_installed(cht_filename, installed_games_for_sys):
    """Kiểm tra xem file .cht này có khớp với game nào trong hệ máy đang có hay không."""
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


def check_or_download_single_cheat(sys_code, rom_filename, base_sd=None):
    """Kiểm tra hoặc tải cheat riêng lẻ cho một game cụ thể."""
    sd = base_sd or SDCARD_PATH
    primary_dir = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
    rom_base = os.path.splitext(rom_filename)[0]

    code = re.sub(r'\(.*?\)|\[.*?\]', '', sys_code).strip().upper()
    libretro_systems = LIBRETRO_SYSTEM_MAP.get(code, [sys_code])

    # 1. Kiểm tra xem file cheat đã có sẵn trên máy chưa
    for l_sys in libretro_systems:
        target_cht = os.path.join(primary_dir, l_sys, f"{rom_base}.cht")
        if os.path.isfile(target_cht):
            return {"ok": True, "exists": True, "path": target_cht, "message": "Game này đã có sẵn file Cheat trên máy."}

    # 2. Thử tải trực tiếp file cheat theo tên từ GitHub raw repository
    for l_sys in libretro_systems:
        try:
            sys_dest = os.path.join(primary_dir, l_sys)
            os.makedirs(sys_dest, exist_ok=True)

            clean_enc = urllib.parse.quote(rom_base)
            url = f"https://raw.githubusercontent.com/libretro/libretro-database/master/cht/{urllib.parse.quote(l_sys)}/{clean_enc}.cht"
            req = urllib.request.Request(url, headers={"User-Agent": "RetroHub-TrimUI/1.92"})
            urlopen_kw = {"timeout": 10}
            if _SSL_CONTEXT is not None:
                urlopen_kw["context"] = _SSL_CONTEXT
            try:
                with urllib.request.urlopen(req, **urlopen_kw) as resp:
                    content = resp.read()
                    target_file = os.path.join(sys_dest, f"{rom_base}.cht")
                    with open(target_file, "wb") as f:
                        f.write(content)
                    return {"ok": True, "downloaded": True, "path": target_file, "message": "Đã tải file Cheat thành công!"}
            except Exception:
                pass
        except Exception:
            pass

    return {"ok": False, "message": "Chưa có file Cheat riêng cho game này. Bạn có thể bấm Tải Cheat cho game đang có."}


class CheatDownloaderRunner:
    """Điều phối tải và giải nén kho Cheat Code chạy nền với thanh tiến độ thời gian thực."""

    def __init__(self):
        self.active = False
        self.done = False
        self.stop_requested = False
        self.phase = "idle"  # idle, scanning, downloading, extracting, done, error
        self.mode = "installed"  # "installed" hoặc "all"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.progress_pct = 0
        self.speed_bps = 0
        self.status_msg = ""
        self.extracted_count = 0
        self.matched_games_count = 0
        self.total_installed_games = 0
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
        download_url = url or LIBRETRO_CHEATS_URL

        primary_dir = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
        secondary_dir = os.path.join(sd, "RetroArch", "cheats")
        os.makedirs(primary_dir, exist_ok=True)
        os.makedirs(secondary_dir, exist_ok=True)

        installed_games = {}
        if self.mode == "installed":
            with self._lock:
                self.phase = "scanning"
                self.status_msg = "Đang quét danh sách game trên thẻ nhớ..."
            installed_games = scan_installed_games(sd)
            tot_g = sum(len(v) for v in installed_games.values())
            with self._lock:
                self.total_installed_games = tot_g
            if tot_g == 0:
                with self._lock:
                    self.done = True
                    self.active = False
                    self.phase = "error"
                    self.error_msg = "Không tìm thấy game nào trong thư mục Roms!"
                    self.status_msg = "Chưa có game nào trong thư mục Roms để tải Cheat."
                return

        tmp_zip = os.path.join(sd, "RetroArch", ".cheats_download.zip")
        if not os.path.isdir(os.path.dirname(tmp_zip)):
            tmp_zip = "/tmp/cheats_download.zip"

        try:
            # -------------------------------------------------------------
            # BƯỚC 1: TẢI FILE CHEATS.ZIP TỪ BUILDBOT
            # -------------------------------------------------------------
            with self._lock:
                self.phase = "downloading"
                self.status_msg = "Đang kết nối tới máy chủ Libretro..."

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "RetroHub-TrimUI/1.92"}
            )

            urlopen_kw = {"timeout": 20}
            if _SSL_CONTEXT is not None:
                urlopen_kw["context"] = _SSL_CONTEXT
            with urllib.request.urlopen(req, **urlopen_kw) as resp, open(tmp_zip, "wb") as out_f:
                tot_header = resp.getheader("Content-Length")
                total_len = int(tot_header) if tot_header and tot_header.isdigit() else 37157000
                with self._lock:
                    self.total_bytes = total_len

                downloaded = 0
                start_t = time.time()
                last_t = start_t
                last_bytes = 0

                chunk_size = 65536
                while True:
                    if self.stop_requested:
                        break

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break

                    out_f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if now - last_t >= 0.2:
                        speed = (downloaded - last_bytes) / (now - last_t)
                        pct = min(99, int((downloaded / total_len) * 100)) if total_len > 0 else 0
                        mb_done = downloaded / (1024 * 1024)
                        mb_tot = total_len / (1024 * 1024)
                        speed_kbs = speed / 1024

                        with self._lock:
                            self.downloaded_bytes = downloaded
                            self.progress_pct = pct
                            self.speed_bps = speed
                            self.status_msg = f"Đang tải: {mb_done:.1f}/{mb_tot:.1f} MB ({speed_kbs:.0f} KB/s)"

                        last_t = now
                        last_bytes = downloaded

            if self.stop_requested:
                if os.path.isfile(tmp_zip):
                    try:
                        os.remove(tmp_zip)
                    except Exception:
                        pass
                with self._lock:
                    self.done = True
                    self.active = False
                    self.phase = "idle"
                    self.status_msg = "Đã hủy tải Cheat Code!"
                return

            # -------------------------------------------------------------
            # BƯỚC 2: GIẢI NÉN VÀO THƯ MỤC CHEATS
            # -------------------------------------------------------------
            with self._lock:
                self.phase = "extracting"
                self.progress_pct = 99
                if self.mode == "installed":
                    self.status_msg = f"Đang đối chiếu & trích xuất Cheat cho {self.total_installed_games} game..."
                else:
                    self.status_msg = "Đang giải nén hàng ngàn mã Cheat vào RetroArch..."

            extracted = 0
            matched_games = set()
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                namelist = zf.namelist()

                for idx, member in enumerate(namelist):
                    if self.stop_requested:
                        break

                    norm_p = os.path.normpath(member)
                    if norm_p.startswith("..") or os.path.isabs(norm_p):
                        continue
                    if member.endswith("/"):
                        continue

                    parts = norm_p.split(os.sep)
                    if len(parts) < 2:
                        continue

                    sys_part = parts[0]
                    cht_file = parts[-1]

                    matched_rom = None
                    if self.mode == "installed":
                        if sys_part not in installed_games:
                            continue
                        matched_rom = match_cht_with_installed(cht_file, installed_games[sys_part])
                        if not matched_rom:
                            continue
                        matched_games.add((sys_part, matched_rom["rom_basename"]))

                    target_file = os.path.join(primary_dir, norm_p)
                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    content = zf.read(member)
                    with open(target_file, "wb") as dst:
                        dst.write(content)
                    extracted += 1

                    if self.mode == "installed" and matched_rom:
                        alias_target = os.path.join(primary_dir, sys_part, f"{matched_rom['rom_basename']}.cht")
                        if not os.path.isfile(alias_target):
                            try:
                                with open(alias_target, "wb") as af:
                                    af.write(content)
                            except Exception:
                                pass

                    if idx % 100 == 0:
                        with self._lock:
                            self.extracted_count = extracted
                            self.matched_games_count = len(matched_games)
                            if self.mode == "installed":
                                self.status_msg = f"Đang trích xuất: {extracted} mã Cheat cho {len(matched_games)} game..."
                            else:
                                self.status_msg = f"Đang giải nén: {extracted} file cheat..."

            # Xóa file zip tạm sau khi giải nén
            if os.path.isfile(tmp_zip):
                try:
                    os.remove(tmp_zip)
                except Exception:
                    pass

            with self._lock:
                self.done = True
                self.active = False
                self.phase = "done"
                self.progress_pct = 100
                self.extracted_count = extracted
                self.matched_games_count = len(matched_games)
                if self.mode == "installed":
                    self.status_msg = f"Hoàn tất! Đã cài {extracted} mã Cheat cho {len(matched_games)} game của bạn."
                else:
                    self.status_msg = f"Hoàn tất! Đã cài đặt toàn bộ {extracted} mã Cheat."

        except Exception as e:
            if os.path.isfile(tmp_zip):
                try:
                    os.remove(tmp_zip)
                except Exception:
                    pass
            with self._lock:
                self.done = True
                self.active = False
                self.phase = "error"
                self.error_msg = str(e)
                self.status_msg = f"Lỗi tải Cheat: {str(e)}"


cheat_runner = CheatDownloaderRunner()
