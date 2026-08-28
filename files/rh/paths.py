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
