# -*- coding: utf-8 -*-
"""Filesystem locations. Leaf module - imports nothing from rh."""

import os

SDCARD_PATH = "/mnt/SDCARD"
EX_OPTIONS_FILE = f"{SDCARD_PATH}/System/etc/ex_options"
# This module lives in rh/, one level below the app root, so climb out of the
# package before resolving anything relative to the app directory.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_FILE = os.path.join(APP_DIR, "catalog", "catalogs.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
TEMP_DOWNLOAD_DIR = f"{SDCARD_PATH}/Roms/.tmp_download"
STREAMER_SCRIPT = os.path.join(APP_DIR, "streamer.py")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
FLAG_FILES = {"VI": os.path.join(ASSETS_DIR, "flag_vi.png"),
              "EN": os.path.join(ASSETS_DIR, "flag_en.png")}
QR_DONATE_FILE = os.path.join(ASSETS_DIR, "qr_donate.png")
QR_TELEGRAM_FILE = os.path.join(ASSETS_DIR, "qr_telegram.png")
QR_BMC_FILE = os.path.join(ASSETS_DIR, "qr_bmc.png")
SPLASH_BACKUP_DIR = "/mnt/SDCARD/System/backup"
SPLASH_BACKUP_FILE = "/mnt/SDCARD/System/backup/splash_original.png"
SPLASH_DIR = "/mnt/SDCARD/Splash"
SPLASH_SYS_FILE = "/etc/splash.png"
SPLASH_TEMP_PREVIEW = "/tmp/splash_preview.png"
SPLASH_TEMP_BMP = "/tmp/splash_preview.bmp"
BOOTLOGO_BACKUP_FILE = "/mnt/SDCARD/System/backup/bootlogo_original.bmp"
YT_CACHE_DIR = "/tmp/yt_thumbs"
YT_HISTORY_FILE = os.path.join(APP_DIR, "yt_history.json")


def is_nextui():
    """True if running under NextUI / MinUI environment."""
    return bool(os.environ.get("PLATFORM")) or os.path.isdir(f"{SDCARD_PATH}/.system") or os.path.isdir(f"{SDCARD_PATH}/.userdata")


def resolve_rom_dir(sys_tag):
    """Find the best matching ROM directory on SDCARD for a given system tag.

    On NextUI, systems often have folders named 'Nintendo (FC)', 'Game Boy Advance (GBA)',
    etc. We check for existing folders matching the tag in parentheses first, then direct
    subfolder name, and finally fallback to SDCARD_PATH/Roms/<sys_tag>.
    """
    roms_root = f"{SDCARD_PATH}/Roms"
    if not os.path.exists(roms_root):
        return f"{roms_root}/{sys_tag}"

    tag_upper = str(sys_tag).upper()
    tag_pattern = f"({tag_upper})"
    try:
        for entry in os.listdir(roms_root):
            p = os.path.join(roms_root, entry)
            if os.path.isdir(p) and entry.upper().endswith(tag_pattern):
                return p
    except OSError:
        pass

    direct = os.path.join(roms_root, sys_tag)
    if os.path.isdir(direct):
        return direct
    return direct

