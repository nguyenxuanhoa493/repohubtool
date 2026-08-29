# -*- coding: utf-8 -*-
"""Mutable runtime state, shared across modules.

Always reach these through the module (``state.current_lang``), never via
``from .state import current_lang`` - a from-import copies the value at import
time, so later language or view-mode changes would not be visible."""

import os
import json
import threading

from .paths import SETTINGS_FILE, CATALOG_FILE

# Load Settings
current_lang = "VI"
downloaded_view_mode = "grid" # Default to Grid Mode
# Keep the Wi-Fi radio awake between packets. Off saves battery but drops idle
# SSH sessions and can interrupt a long download, so it is user-controlled.
wifi_awake = False
# Check GitHub for a newer build when the app starts.
auto_update = True
# Versions the user chose to skip, so the prompt does not come back for them.
skipped_versions = []
# Overrides the update repo baked into rh/updater.py, so moving the repo does
# not need a rebuild.
update_url = ""
# Version an update just installed. Written before the restart and cleared on
# the next launch, which is the only moment the new build can confirm itself.
pending_update = ""
# sha256 cua catalogue dang nam tren may. So chuoi nay voi manifest re hon doc
# lai 33 MB tu the moi lan kiem tra cap nhat.
catalog_sha = ""
# Thong bao loi catalogue tu lan cap nhat truoc, cho toi khi restart xong moi
# co man hinh de hien. Cung mot ly do voi pending_update: ghi truoc luc
# restart, doc va xoa o lan khoi dong ke tiep - khong the hien ngay vi
# request_restart() ket thuc vong lap chinh chi mot nhip sau do.
pending_catalog_notice = ""

if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            current_lang = cfg.get("language", "VI")
            downloaded_view_mode = cfg.get("view_mode", "grid")
            wifi_awake = cfg.get("wifi_awake", False)
            auto_update = cfg.get("auto_update", True)
            skipped_versions = cfg.get("skipped_versions", []) or []
            update_url = cfg.get("update_url", "") or ""
            pending_update = cfg.get("pending_update", "") or ""
            catalog_sha = cfg.get("catalog_sha", "") or ""
            pending_catalog_notice = cfg.get("pending_catalog_notice", "") or ""
    except:
        current_lang = "VI"
        downloaded_view_mode = "grid"
_save_lock = threading.Lock()


def save_settings():
    """Persist settings atomically.

    Written to a sibling file and renamed into place: a truncated settings.json
    from a power cut mid-write would lose the language, the update URL and the
    list of skipped versions all at once. The lock matters because the updater
    saves from its own thread while the main loop may be saving too."""
    with _save_lock:
        try:
            tmp = SETTINGS_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({
                    "language": current_lang,
                    "view_mode": downloaded_view_mode,
                    "wifi_awake": wifi_awake,
                    "auto_update": auto_update,
                    "skipped_versions": skipped_versions,
                    "update_url": update_url,
                    "pending_update": pending_update,
                    "catalog_sha": catalog_sha,
                    "pending_catalog_notice": pending_catalog_notice
                }, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, SETTINGS_FILE)
        except OSError as e:
            print(f"Error saving settings: {e}")
# Load ROM Catalogs (5,833+ Games)
catalogs = {}
if os.path.exists(CATALOG_FILE):
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            catalogs = json.load(f)
            # Pre-index games for instant search (< 1ms)
            for sc, sdata in catalogs.items():
                for g in sdata.get("games", []):
                    t = g.get("title", "")
                    fn = g.get("filename", "")
                    g["_s_idx"] = f"{t} {fn}".lower()
    except Exception as e:
        print(f"Error loading catalogs: {e}")

SCREEN_W = 1024
SCREEN_H = 768
rom_sort_mode = "downloads"
