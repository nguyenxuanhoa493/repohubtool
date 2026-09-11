# -*- coding: utf-8 -*-
"""Filesystem locations. Leaf module - imports nothing from rh."""

import os

# This module lives in rh/, one level below the app root, so climb out of the
# package before resolving anything relative to the app directory.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _detect_sdcard_path():
    """Detect root directory of the SD card / user storage.

    Precedence:
    1. SDCARD_PATH environment variable (set by launch.sh or OS)
    2. Parent of 'Apps' if APP_DIR is inside Apps/
    3. Common handheld mount points (/mnt/SDCARD, /mnt/mmc, /userdata, /roms, /mnt/sdcard)
    4. Fallback to /mnt/SDCARD
    """
    env_sd = os.environ.get("SDCARD_PATH")
    if env_sd and os.path.isdir(env_sd):
        return os.path.abspath(env_sd)

    # If installed in <SDCARD>/Apps/RetroHub (or similar), deduce root:
    parent = os.path.dirname(APP_DIR)
    if os.path.basename(parent).lower() == "apps":
        card_candidate = os.path.dirname(parent)
        if os.path.isdir(card_candidate):
            return os.path.abspath(card_candidate)

    for candidate in ["/mnt/SDCARD", "/mnt/mmc", "/userdata", "/roms", "/mnt/sdcard"]:
        if os.path.isdir(candidate):
            return candidate

    return env_sd if env_sd else "/mnt/SDCARD"


SDCARD_PATH = _detect_sdcard_path()
EX_OPTIONS_FILE = os.path.join(SDCARD_PATH, "System", "etc", "ex_options")
CATALOG_FILE = os.path.join(APP_DIR, "catalog", "catalogs.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")


def get_roms_root():
    """Locate the ROMs directory on SDCARD (checks Roms, roms, ROMS preserving disk casing)."""
    if os.path.isdir(SDCARD_PATH):
        try:
            for entry in os.listdir(SDCARD_PATH):
                if entry.upper() == "ROMS":
                    candidate = os.path.join(SDCARD_PATH, entry)
                    if os.path.isdir(candidate):
                        return candidate
        except OSError:
            pass
    return os.path.join(SDCARD_PATH, "Roms")


TEMP_DOWNLOAD_DIR = os.path.join(get_roms_root(), ".tmp_download")
STREAMER_SCRIPT = os.path.join(APP_DIR, "streamer.py")
GAMEWEB_SCRIPT = os.path.join(APP_DIR, "gameweb.py")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
FLAG_FILES = {
    "VI": os.path.join(ASSETS_DIR, "flag_vi.png"),
    "EN": os.path.join(ASSETS_DIR, "flag_en.png"),
}
QR_DONATE_FILE = os.path.join(ASSETS_DIR, "qr_donate.png")
QR_TELEGRAM_FILE = os.path.join(ASSETS_DIR, "qr_telegram.png")
QR_BMC_FILE = os.path.join(ASSETS_DIR, "qr_bmc.png")

SPLASH_BACKUP_DIR = os.path.join(SDCARD_PATH, "System", "backup")
SPLASH_BACKUP_FILE = os.path.join(SPLASH_BACKUP_DIR, "splash_original.png")
SPLASH_DIR = os.path.join(SDCARD_PATH, "Splash")
SPLASH_SYS_FILE = "/etc/splash.png"
SPLASH_TEMP_PREVIEW = "/tmp/splash_preview.png"
SPLASH_TEMP_BMP = "/tmp/splash_preview.bmp"
BOOTLOGO_BACKUP_FILE = os.path.join(SPLASH_BACKUP_DIR, "bootlogo_original.bmp")


def get_yt_cache_dir():
    """Persistent thumbnail directory on SDCARD with fallback to RAM tmpfs."""
    sd_cache = os.path.join(SDCARD_PATH, ".retrohub", "cache", "yt_thumbs")
    try:
        os.makedirs(sd_cache, exist_ok=True)
        return sd_cache
    except Exception:
        fallback = "/tmp/yt_thumbs"
        os.makedirs(fallback, exist_ok=True)
        return fallback


YT_CACHE_DIR = get_yt_cache_dir()
YT_FEED_CACHE_FILE = os.path.join(SDCARD_PATH, ".retrohub", "cache", "yt_feed_cache.json")
YT_FEED_FALLBACK_FILE = "/tmp/yt_feed_cache.json"
YT_HISTORY_FILE = os.path.join(APP_DIR, "yt_history.json")
YT_FAVORITES_FILE = os.path.join(SDCARD_PATH, ".retrohub", "yt_favorites.json")
YT_FAVORITES_FALLBACK_FILE = os.path.join(APP_DIR, "yt_favorites.json")


def is_nextui():
    """True if running under NextUI / MinUI environment."""
    return (
        bool(os.environ.get("PLATFORM"))
        or os.path.isdir(os.path.join(SDCARD_PATH, ".system"))
        or os.path.isdir(os.path.join(SDCARD_PATH, ".userdata"))
    )


def resolve_rom_dir(sys_tag):
    """Find the best matching ROM directory on SDCARD for a given system tag.

    On NextUI, systems often have folders named 'Nintendo (FC)', 'Game Boy Advance (GBA)',
    etc. We check for existing folders matching the tag in parentheses first, then direct
    subfolder name, and finally fallback to roms_root/<sys_tag>.
    """
    roms_root = get_roms_root()
    if not os.path.exists(roms_root):
        return os.path.join(roms_root, str(sys_tag))

    tag_upper = str(sys_tag).upper()
    tag_pattern = f"({tag_upper})"
    try:
        entries = os.listdir(roms_root)
    except OSError:
        entries = []

    # 1. Folder ending with '(TAG)' (NextUI / MinUI convention)
    for entry in entries:
        p = os.path.join(roms_root, entry)
        if os.path.isdir(p) and entry.upper().endswith(tag_pattern):
            return p

    # 2. Case-insensitive exact name matching (e.g. gba, GBA, Gba)
    for entry in entries:
        p = os.path.join(roms_root, entry)
        if os.path.isdir(p) and entry.upper() == tag_upper:
            return p

    # 3. Direct match / fallback
    return os.path.join(roms_root, str(sys_tag))

