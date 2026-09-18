# -*- coding: utf-8 -*-
"""Emu Icon Manager for TrimUI Handhelds.

Handles:
- Lightweight catalog loading (names, metadata & previews) with instant in-memory caching.
- Automatic Stock Icons backup before first overwrite.
- On-demand Online / Remote Download & extraction directly into /mnt/SDCARD/Emus/_themes.
- One-click Restore Stock Icons to revert back to original state.
"""

import os
import shutil
import json
import time
import zipfile
import urllib.request
import urllib.parse
import ssl
from typing import List, Dict, Tuple, Optional, Callable

from .paths import (
    SDCARD_PATH,
    APP_DIR,
    EMUS_DIR,
    EMU_THEME_DIR,
    EMU_THEMES_DIR,
    EMU_ICON_BACKUP_DIR,
    EMU_ICON_BACKUP_MARKER,
    ICONS_CATALOG_FILE,
    ACTIVE_ICON_PACK_FILE,
    LOCAL_ICONS_REPO_DIR,
)
from . import state
from .i18n import tr

_SSL_CTX = None
try:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CTX = None


_ICONS_CACHE = None


def has_stock_backup() -> bool:
    """Returns True if original stock emulator icons can be restored (from backup or built-in stock pack)."""
    if os.path.isdir(EMU_ICON_BACKUP_DIR):
        for item in os.listdir(EMU_ICON_BACKUP_DIR):
            if not item.startswith("."):
                return True
    # Check fallback built-in stock packs or zips
    stock_zips = [
        os.path.join(LOCAL_ICONS_REPO_DIR, "zips", "Stock - TrimUI Stock OS 1.1.0.zip"),
        os.path.join(APP_DIR, "EmuIcons", "zips", "Stock - TrimUI Stock OS 1.1.0.zip"),
        os.path.join(SDCARD_PATH, "EmuIcons", "zips", "Stock - TrimUI Stock OS 1.1.0.zip"),
    ]
    for sz in stock_zips:
        if os.path.isfile(sz) and os.path.getsize(sz) > 1000:
            return True
    stock_dirs = [
        os.path.join(LOCAL_ICONS_REPO_DIR, "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
        os.path.join(APP_DIR, "EmuIcons", "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
        os.path.join(SDCARD_PATH, "EmuIcons", "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
    ]
    for sd in stock_dirs:
        if os.path.isdir(sd) and any(not f.startswith(".") for f in os.listdir(sd)):
            return True
    return False


def get_active_icon_pack() -> Optional[Dict]:
    """Reads the currently activated icon pack info from active_icon_pack.json."""
    if os.path.isfile(ACTIVE_ICON_PACK_FILE):
        try:
            with open(ACTIVE_ICON_PACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def set_active_icon_pack(icon_info: Dict):
    """Saves currently active icon pack info to disk."""
    try:
        os.makedirs(os.path.dirname(ACTIVE_ICON_PACK_FILE), exist_ok=True)
        data = {
            "id": icon_info.get("id", ""),
            "name": icon_info.get("name", ""),
            "version": icon_info.get("version", ""),
            "folder": icon_info.get("folder", ""),
            "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(ACTIVE_ICON_PACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[IconManager] Error saving active icon pack: {e}")


def backup_stock_icons() -> Tuple[bool, str]:
    """Backs up /mnt/SDCARD/Emus/_theme (and _themes) into System/backup/emu_icons_stock."""
    if os.path.isdir(EMU_ICON_BACKUP_DIR) and any(not f.startswith(".") for f in os.listdir(EMU_ICON_BACKUP_DIR)):
        return True, "Đã có bản sao lưu gốc!" if state.current_lang == "VI" else "Stock backup already exists!"

    src_dirs = [EMU_THEME_DIR, EMU_THEMES_DIR]
    valid_src = None
    for s in src_dirs:
        if os.path.isdir(s) and any(not f.startswith(".") for f in os.listdir(s)):
            valid_src = s
            break

    if not valid_src:
        # Fallback to built-in stock pack if present
        stock_pack_dirs = [
            os.path.join(LOCAL_ICONS_REPO_DIR, "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
            os.path.join(APP_DIR, "EmuIcons", "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
            os.path.join(SDCARD_PATH, "EmuIcons", "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
        ]
        for d in stock_pack_dirs:
            if os.path.isdir(d) and any(not f.startswith(".") for f in os.listdir(d)):
                valid_src = d
                break

    if not valid_src:
        os.makedirs(EMU_ICON_BACKUP_DIR, exist_ok=True)
        with open(EMU_ICON_BACKUP_MARKER, "w", encoding="utf-8") as f:
            f.write("stock_backup_empty")
        return True, "Khởi tạo bản sao lưu rỗng." if state.current_lang == "VI" else "Initialized empty stock backup."

    try:
        os.makedirs(EMU_ICON_BACKUP_DIR, exist_ok=True)
        for item in os.listdir(valid_src):
            if item.startswith("."):
                continue
            s = os.path.join(valid_src, item)
            d = os.path.join(EMU_ICON_BACKUP_DIR, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            elif os.path.isfile(s):
                shutil.copy2(s, d)

        with open(EMU_ICON_BACKUP_MARKER, "w", encoding="utf-8") as f:
            f.write(f"stock_backup_done_at_{time.time()}")

        print(f"[IconManager] Successfully backed up stock icons to {EMU_ICON_BACKUP_DIR}")
        return True, tr("icon_backup_success")
    except Exception as e:
        print(f"[IconManager] Backup failed: {e}")
        return False, f"{tr('icon_backup_failed')}: {e}"


def restore_stock_icons(on_progress: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
    """Restores original emulator icons from backup or stock pack into both _theme and _themes."""
    global _ICONS_CACHE
    if not has_stock_backup():
        return False, "Không tìm thấy bản sao lưu gốc!" if state.current_lang == "VI" else "No stock backup found!"

    if on_progress:
        on_progress(20, "Đang khôi phục icon gốc..." if state.current_lang == "VI" else "Restoring stock icons...")

    try:
        target_dirs = [EMU_THEME_DIR, EMU_THEMES_DIR]
        for t_dir in target_dirs:
            os.makedirs(t_dir, exist_ok=True)

        backup_src = None
        if os.path.isdir(EMU_ICON_BACKUP_DIR) and any(not f.startswith(".") for f in os.listdir(EMU_ICON_BACKUP_DIR)):
            backup_src = EMU_ICON_BACKUP_DIR
        else:
            stock_dirs = [
                os.path.join(LOCAL_ICONS_REPO_DIR, "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
                os.path.join(APP_DIR, "EmuIcons", "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
                os.path.join(SDCARD_PATH, "EmuIcons", "Stock - TrimUI Stock OS 1.1.0", "Emus", "_theme"),
            ]
            for sd in stock_dirs:
                if os.path.isdir(sd) and any(not f.startswith(".") for f in os.listdir(sd)):
                    backup_src = sd
                    break

        if backup_src:
            if on_progress:
                on_progress(50, "Đang sao chép tệp tin..." if state.current_lang == "VI" else "Copying files...")

            backup_files = [f for f in os.listdir(backup_src) if not f.startswith(".")]
            for item in backup_files:
                s = os.path.join(backup_src, item)
                for t_dir in target_dirs:
                    d = os.path.join(t_dir, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    elif os.path.isfile(s):
                        shutil.copy2(s, d)
        else:
            # Try stock zip extraction
            stock_zips = [
                os.path.join(LOCAL_ICONS_REPO_DIR, "zips", "Stock - TrimUI Stock OS 1.1.0.zip"),
                os.path.join(APP_DIR, "EmuIcons", "zips", "Stock - TrimUI Stock OS 1.1.0.zip"),
                os.path.join(SDCARD_PATH, "EmuIcons", "zips", "Stock - TrimUI Stock OS 1.1.0.zip"),
            ]
            extracted = False
            for sz in stock_zips:
                if os.path.isfile(sz) and zipfile.is_zipfile(sz):
                    with zipfile.ZipFile(sz, "r") as zf:
                        zf.extractall(SDCARD_PATH)
                    sync_theme_directories()
                    extracted = True
                    break
            if not extracted:
                return False, "Không tìm thấy tệp icon gốc để khôi phục!" if state.current_lang == "VI" else "No stock icon files found to restore!"

        if os.path.exists(ACTIVE_ICON_PACK_FILE):
            try:
                os.remove(ACTIVE_ICON_PACK_FILE)
            except Exception:
                pass

        try:
            os.system("sync")
        except Exception:
            pass

        _ICONS_CACHE = None
        if on_progress:
            on_progress(100, tr("icon_restore_success"))
        return True, tr("icon_restore_success")
    except Exception as e:
        print(f"[IconManager] Restore failed: {e}")
        return False, f"{tr('icon_restore_failed')}: {e}"


def sync_theme_directories(primary_dir: str = EMU_THEME_DIR):
    """Mirrors primary_dir into the alternate theme directory so both _theme and _themes stay 100% identical without stale overwrites."""
    try:
        if primary_dir == EMU_THEME_DIR:
            src = EMU_THEME_DIR
            dst = EMU_THEMES_DIR
        else:
            src = EMU_THEMES_DIR
            dst = EMU_THEME_DIR

        if not os.path.isdir(src):
            return

        os.makedirs(dst, exist_ok=True)
        for item in os.listdir(src):
            if item.startswith("."):
                continue
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            elif os.path.isfile(s):
                shutil.copy2(s, d)

        try:
            os.system("sync")
        except Exception:
            pass
    except Exception as e:
        print(f"[IconManager] Sync theme directories warning: {e}")


def load_icons_catalog(force_reload: bool = False) -> List[Dict]:
    """Loads lightweight icon catalog with installation status (Instant in-memory caching)."""
    global _ICONS_CACHE
    if _ICONS_CACHE is not None and not force_reload:
        return _ICONS_CACHE

    catalog_icons = []
    if os.path.isfile(ICONS_CATALOG_FILE):
        try:
            with open(ICONS_CATALOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                catalog_icons = data.get("icons", [])
        except Exception as e:
            print(f"[IconManager] Error loading catalog json: {e}")

    active_pack = get_active_icon_pack()
    active_id = active_pack.get("id") if active_pack else None

    # Read preview directory ONCE instead of N stat calls
    preview_dir = os.path.join(APP_DIR, "assets", "icons_preview")
    available_previews = set()
    if os.path.isdir(preview_dir):
        try:
            available_previews = set(os.listdir(preview_dir))
        except Exception:
            pass

    results = []
    for it in catalog_icons:
        folder = it.get("folder") or it.get("id")
        is_active = (folder == active_id or it.get("id") == active_id)

        # Fast preview path resolution
        icon_id = str(it.get("id") or "").lower()
        preview_path = None
        for candidate_name in (f"{icon_id}.png", f"{folder}.png", f"{folder.replace(' ', '_')}.png"):
            if candidate_name in available_previews:
                preview_path = os.path.join(preview_dir, candidate_name)
                break
        if not preview_path:
            local_p = os.path.join(LOCAL_ICONS_REPO_DIR, folder, "preview.png")
            if os.path.isfile(local_p):
                preview_path = local_p

        item = dict(it)
        item["folder"] = folder
        item["is_active"] = is_active
        item["is_installed"] = is_active  # On TrimUI, active = installed
        item["preview_path"] = preview_path
        results.append(item)

    _ICONS_CACHE = results
    return results


def get_icon_preview_path(folder_name: str, icon_id: str = "") -> Optional[str]:
    """Returns local path to icon preview image or None."""
    candidates = [
        os.path.join(APP_DIR, "assets", "icons_preview", f"{icon_id}.png") if icon_id else None,
        os.path.join(APP_DIR, "assets", "icons_preview", f"{folder_name}.png"),
        os.path.join(APP_DIR, "assets", "icons_preview", f"{folder_name.replace(' ', '_')}.png"),
        os.path.join(LOCAL_ICONS_REPO_DIR, folder_name, "preview.png"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def download_file_with_progress(url: str, dest_path: str, on_progress: Optional[Callable[[int, str], None]] = None) -> bool:
    """Downloads a file over HTTP/HTTPS with chunked streaming and progress callback, with curl fallback."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RetroHub-TrimUI/2.32 (Handheld Linux)"}
    )
    try:
        kwargs = {"timeout": 45}
        if _SSL_CTX and url.startswith("https://"):
            kwargs["context"] = _SSL_CTX

        with urllib.request.urlopen(req, **kwargs) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 128 * 1024
            
            with open(dest_path, "wb") as out_f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and on_progress:
                        pct = min(95, int((downloaded / total_size) * 80) + 10)
                        mb_cur = round(downloaded / (1024 * 1024), 1)
                        mb_tot = round(total_size / (1024 * 1024), 1)
                        msg = f"Đang tải: {mb_cur}/{mb_tot} MB ({pct}%)" if state.current_lang == "VI" else f"Downloading: {mb_cur}/{mb_tot} MB ({pct}%)"
                        on_progress(pct, msg)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
                return True
    except Exception as e:
        print(f"[IconManager] Python download failed from {url}: {e}")

    # Fallback to curl if available
    try:
        import subprocess
        if on_progress:
            on_progress(30, "Đang tải qua cURL..." if state.current_lang == "VI" else "Downloading via cURL...")
        res = subprocess.run(["curl", "-k", "-L", "--connect-timeout", "15", "-o", dest_path, url], capture_output=True, timeout=120)
        if res.returncode == 0 and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 1000:
            return True
    except Exception as ce:
        print(f"[IconManager] cURL fallback failed: {ce}")

    if os.path.exists(dest_path):
        try:
            os.remove(dest_path)
        except Exception:
            pass
    return False


def install_icon_pack(icon_info: Dict, on_progress: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
    """Installs an icon pack by automatically backing up stock icons, then downloading/extracting."""
    folder = icon_info.get("folder") or icon_info.get("id")
    if not folder:
        return False, "Tên bộ icon không hợp lệ!" if state.current_lang == "VI" else "Invalid icon pack name!"

    # Step 1: Automatic Stock Backup before modifying
    if on_progress:
        on_progress(5, "Đang kiểm tra và sao lưu icon gốc..." if state.current_lang == "VI" else "Checking and backing up stock icons...")
    
    backup_ok, backup_msg = backup_stock_icons()
    if not backup_ok:
        print(f"[IconManager] Warning during backup: {backup_msg}")

    os.makedirs(EMUS_DIR, exist_ok=True)

    try:
        # Step 2: Check local extracted repo source first
        local_src_candidates = [
            os.path.join(LOCAL_ICONS_REPO_DIR, folder, "Emus"),
            os.path.join(APP_DIR, "EmuIcons", folder, "Emus"),
            os.path.join(SDCARD_PATH, "EmuIcons", folder, "Emus"),
        ]
        for local_src in local_src_candidates:
            if os.path.isdir(local_src):
                if on_progress:
                    on_progress(50, tr("icon_installing"))
                for item in os.listdir(local_src):
                    s = os.path.join(local_src, item)
                    d = os.path.join(EMUS_DIR, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    elif os.path.isfile(s):
                        shutil.copy2(s, d)

                sync_theme_directories()
                set_active_icon_pack(icon_info)
                global _ICONS_CACHE
                _ICONS_CACHE = None
                if on_progress:
                    on_progress(100, tr("icon_install_success"))
                return True, tr("icon_install_success")

        # Step 3: Local pre-packaged zip check (Comprehensive candidate search)
        candidate_zips = [
            os.path.join(LOCAL_ICONS_REPO_DIR, "zips", f"{folder}.zip"),
            os.path.join(LOCAL_ICONS_REPO_DIR, f"{folder}.zip"),
            os.path.join(APP_DIR, "EmuIcons", "zips", f"{folder}.zip"),
            os.path.join(APP_DIR, "EmuIcons", f"{folder}.zip"),
            os.path.join(SDCARD_PATH, "EmuIcons", "zips", f"{folder}.zip"),
            os.path.join(SDCARD_PATH, "EmuIcons", f"{folder}.zip"),
            os.path.join(SDCARD_PATH, "EmuIcons_repo", "zips", f"{folder}.zip"),
            os.path.join(SDCARD_PATH, "EmuIcons_repo", f"{folder}.zip"),
        ]
        for local_zip in candidate_zips:
            if os.path.isfile(local_zip) and os.path.getsize(local_zip) > 1000:
                print(f"[IconManager] Found local zip: {local_zip}")
                if not zipfile.is_zipfile(local_zip):
                    print(f"[IconManager] Corrupt local zip: {local_zip}, removing...")
                    try:
                        os.remove(local_zip)
                    except Exception:
                        pass
                    continue

                if on_progress:
                    on_progress(60, "Đang giải nén bộ icon..." if state.current_lang == "VI" else "Extracting icon pack...")
                try:
                    with zipfile.ZipFile(local_zip, "r") as zf:
                        zf.extractall(SDCARD_PATH)
                    
                    sync_theme_directories()
                    set_active_icon_pack(icon_info)
                    _ICONS_CACHE = None
                    if on_progress:
                        on_progress(100, tr("icon_install_success"))
                    return True, tr("icon_install_success")
                except Exception as ze:
                    print(f"[IconManager] Error extracting local zip {local_zip}: {ze}")
                    try:
                        os.remove(local_zip)
                    except Exception:
                        pass

        # Step 4: Online Download from Git / CDN / Hosting
        enc_folder = urllib.parse.quote(folder)
        zip_name = f"{enc_folder}.zip"
        
        download_urls = []
        # Raw GitHub CDN is the most reliable direct endpoint
        if icon_info.get("raw_git_url"):
            download_urls.append(icon_info["raw_git_url"])
        download_urls.append(f"https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main/EmuIcons/zips/{zip_name}")
        download_urls.append(f"https://github.com/nguyenxuanhoa493/repohubtool/raw/main/EmuIcons/zips/{zip_name}")
        if icon_info.get("download_url"):
            download_urls.append(icon_info["download_url"])
        download_urls.append(f"https://retrohub.xuanhoa493.com/EmuIcons/zips/{zip_name}")

        # Deduplicate while preserving priority
        dedup_urls = []
        for u in download_urls:
            if u and u not in dedup_urls:
                dedup_urls.append(u)
        download_urls = dedup_urls

        tmp_zip = f"/tmp/icon_{enc_folder}.zip"
        download_ok = False

        for url in download_urls:
            print(f"[IconManager] Attempting download from: {url}")
            if download_file_with_progress(url, tmp_zip, on_progress):
                download_ok = True
                break

        if not download_ok or not os.path.isfile(tmp_zip) or os.path.getsize(tmp_zip) < 1000:
            return False, "Không tải được bộ icon từ máy chủ mạng!" if state.current_lang == "VI" else "Failed to download icon pack from server!"

        # Extract downloaded zip
        if on_progress:
            on_progress(90, "Đang giải nén bộ icon vào thẻ nhớ..." if state.current_lang == "VI" else "Extracting icon pack to SD card...")

        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(SDCARD_PATH)

        try:
            os.remove(tmp_zip)
        except Exception:
            pass

        sync_theme_directories()
        set_active_icon_pack(icon_info)
        _ICONS_CACHE = None
        return True, tr("icon_install_success")

    except Exception as e:
        print(f"[IconManager] Install failed: {e}")
        return False, f"{tr('icon_install_failed')}: {e}"
