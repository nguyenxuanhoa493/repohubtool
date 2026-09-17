# -*- coding: utf-8 -*-
"""Theme Manager for Trimui Brick Pro / Trimui Handhelds (Stock OS).

Handles:
- Immutable initial backup of default stock themes (never overwritten by subsequent installs).
- Lightweight catalog loading (names, metadata & previews) without keeping full theme archives locally.
- On-demand Online / Remote Download and installation directly into SDCARD/Themes/<ThemeName>.
- Uninstallation to free up SD card space anytime.
- Restoration of the original factory stock theme state.
"""

import os
import shutil
import json
import zipfile
import urllib.request
import urllib.parse
import ssl
from typing import List, Dict, Tuple, Optional, Callable

from .paths import (
    SDCARD_PATH,
    APP_DIR,
    THEMES_DIR,
    THEME_BACKUP_DIR,
    THEME_BACKUP_MARKER,
    THEMES_CATALOG_FILE,
    LOCAL_THEMES_REPO_DIR,
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


def ensure_default_theme_backup() -> bool:
    """Safely and immutably backs up the default stock themes only ONCE."""
    try:
        if os.path.exists(THEME_BACKUP_MARKER):
            return True

        os.makedirs(THEME_BACKUP_DIR, exist_ok=True)

        backed_up_count = 0
        if os.path.isdir(THEMES_DIR):
            for item in os.listdir(THEMES_DIR):
                if item.startswith(".") or item == "zips":
                    continue
                src_item = os.path.join(THEMES_DIR, item)
                dst_item = os.path.join(THEME_BACKUP_DIR, item)
                if os.path.isdir(src_item) and not os.path.exists(dst_item):
                    shutil.copytree(src_item, dst_item)
                    backed_up_count += 1

        sys_theme_candidates = ["/usr/trimui/res/skin", "/root/mytheme", "/usr/trimui/skin"]
        for cand in sys_theme_candidates:
            if os.path.isdir(cand):
                dst_cand = os.path.join(THEME_BACKUP_DIR, "system_skin")
                if not os.path.exists(dst_cand):
                    try:
                        shutil.copytree(cand, dst_cand)
                        backed_up_count += 1
                    except Exception:
                        pass

        info = {
            "backed_up_at": os.path.getmtime(THEME_BACKUP_DIR),
            "backed_up_count": backed_up_count,
            "stock_preserved": True
        }
        with open(os.path.join(THEME_BACKUP_DIR, "backup_info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2)

        with open(THEME_BACKUP_MARKER, "w") as f:
            f.write("TRIMUI_STOCK_DEFAULT_THEME_BACKUP_OK\n")

        return True
    except Exception as e:
        print(f"[ThemeManager] Backup error: {e}")
        return False


def load_themes_catalog() -> List[Dict]:
    """Loads lightweight theme catalog with installation status."""
    catalog_themes = []
    
    if os.path.isfile(THEMES_CATALOG_FILE):
        try:
            with open(THEMES_CATALOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                catalog_themes = data.get("themes", [])
        except Exception as e:
            print(f"[ThemeManager] Error loading catalog json: {e}")

    results = []
    for t in catalog_themes:
        folder = t.get("folder") or t.get("id")
        installed_path = os.path.join(THEMES_DIR, folder)
        is_installed = os.path.isdir(installed_path) and os.path.exists(os.path.join(installed_path, "config.json"))
        
        # Resolve preview path
        preview_path = get_theme_preview_path(folder)

        item = dict(t)
        item["folder"] = folder
        item["is_installed"] = is_installed
        item["installed_path"] = installed_path if is_installed else None
        item["preview_path"] = preview_path
        results.append(item)

    return results


def get_theme_preview_path(folder_name: str) -> Optional[str]:
    """Returns local path to theme preview image or None."""
    candidates = [
        os.path.join(THEMES_DIR, folder_name, "preview.png"),
        os.path.join(APP_DIR, "assets", "themes_preview", f"{folder_name}.png"),
        os.path.join(LOCAL_THEMES_REPO_DIR, folder_name, "preview.png"),
        f"/tmp/theme_previews/{folder_name}.png",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def download_file_with_progress(url: str, dest_path: str, on_progress: Optional[Callable[[int, str], None]] = None) -> bool:
    """Downloads a file over HTTP/HTTPS with chunked streaming and progress callback."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RetroHub-TrimUI/2.32 (Handheld Linux)"}
    )
    try:
        kwargs = {"timeout": 30}
        if _SSL_CTX and url.startswith("https://"):
            kwargs["context"] = _SSL_CTX

        with urllib.request.urlopen(req, **kwargs) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024
            
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
            return True
    except Exception as e:
        print(f"[ThemeManager] Download failed from {url}: {e}")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False


def install_theme(theme_info: Dict, on_progress: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
    """Installs a theme on-demand by downloading zip archive from Git/CDN or local repo."""
    ensure_default_theme_backup()
    
    folder = theme_info.get("folder") or theme_info.get("id")
    if not folder:
        return False, "Tên theme không hợp lệ!" if state.current_lang == "VI" else "Invalid theme name!"

    target_dir = os.path.join(THEMES_DIR, folder)
    os.makedirs(THEMES_DIR, exist_ok=True)

    if on_progress:
        on_progress(5, tr("theme_installing"))

    try:
        # 1. Check local repo source first if available
        local_src = os.path.join(LOCAL_THEMES_REPO_DIR, folder)
        if os.path.isdir(local_src) and os.path.exists(os.path.join(local_src, "config.json")):
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            if on_progress:
                on_progress(50, tr("theme_installing"))
            shutil.copytree(local_src, target_dir)
            if on_progress:
                on_progress(100, tr("theme_install_success"))
            return True, tr("theme_install_success")

        # 2. Local pre-packaged zip check
        local_zip = os.path.join(LOCAL_THEMES_REPO_DIR, "zips", f"{folder}.zip")
        if os.path.isfile(local_zip):
            if on_progress:
                on_progress(60, "Đang giải nén..." if state.current_lang == "VI" else "Extracting...")
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(local_zip, "r") as zf:
                zf.extractall(target_dir)
            if on_progress:
                on_progress(100, tr("theme_install_success"))
            return True, tr("theme_install_success")

        # 3. Online Download from Git / CDN / Hosting
        enc_folder = urllib.parse.quote(folder)
        zip_name = f"{enc_folder}.zip"
        
        download_urls = [
            f"https://retrohub.xuanhoa493.com/Themes/zips/{zip_name}",
            f"https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main/Themes/zips/{zip_name}",
            f"https://github.com/nguyenxuanhoa493/repohubtool/raw/main/Themes/zips/{zip_name}",
        ]
        if theme_info.get("download_url"):
            download_urls.insert(0, theme_info["download_url"])

        tmp_zip = f"/tmp/{folder}.zip"
        download_ok = False

        for url in download_urls:
            print(f"[ThemeManager] Attempting download from: {url}")
            if download_file_with_progress(url, tmp_zip, on_progress):
                download_ok = True
                break

        if not download_ok or not os.path.isfile(tmp_zip) or os.path.getsize(tmp_zip) < 1000:
            return False, "Không tải được theme từ máy chủ mạng!" if state.current_lang == "VI" else "Failed to download theme from server!"

        # Extract downloaded zip
        if on_progress:
            on_progress(90, "Đang giải nén giao diện..." if state.current_lang == "VI" else "Extracting theme...")
            
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(target_dir)

        try:
            os.remove(tmp_zip)
        except Exception:
            pass

        if on_progress:
            on_progress(100, tr("theme_install_success"))

        return True, tr("theme_install_success")

    except Exception as e:
        print(f"[ThemeManager] Install failed: {e}")
        return False, f"{tr('theme_install_failed')}: {e}"


def uninstall_theme(folder_name: str) -> Tuple[bool, str]:
    """Uninstalls a theme directory from SDCARD/Themes/ to free up space."""
    target_dir = os.path.join(THEMES_DIR, folder_name)
    if not os.path.isdir(target_dir):
        return False, "Theme chưa được cài đặt!" if state.current_lang == "VI" else "Theme is not installed!"

    try:
        shutil.rmtree(target_dir)
        return True, tr("theme_uninstall_success")
    except Exception as e:
        print(f"[ThemeManager] Uninstall error: {e}")
        return False, f"Lỗi gỡ bỏ: {e}" if state.current_lang == "VI" else f"Uninstall error: {e}"


def restore_default_theme() -> Tuple[bool, str]:
    """Restores the original stock default themes from the immutable backup."""
    if not os.path.isdir(THEME_BACKUP_DIR) or not os.path.exists(THEME_BACKUP_MARKER):
        return False, "Không tìm thấy bản sao lưu theme mặc định gốc!" if state.current_lang == "VI" else "Original stock backup not found!"

    try:
        restored_count = 0
        os.makedirs(THEMES_DIR, exist_ok=True)

        for item in os.listdir(THEME_BACKUP_DIR):
            if item.startswith(".") or item == "backup_info.json":
                continue
            src_item = os.path.join(THEME_BACKUP_DIR, item)
            dst_item = os.path.join(THEMES_DIR, item)
            
            if os.path.isdir(src_item) and item != "system_skin":
                if os.path.exists(dst_item):
                    shutil.rmtree(dst_item)
                shutil.copytree(src_item, dst_item)
                restored_count += 1

        sys_skin_backup = os.path.join(THEME_BACKUP_DIR, "system_skin")
        if os.path.isdir(sys_skin_backup):
            cand_dst = "/root/mytheme"
            if os.path.isdir(cand_dst):
                try:
                    for f in os.listdir(sys_skin_backup):
                        shutil.copy2(os.path.join(sys_skin_backup, f), os.path.join(cand_dst, f))
                except Exception:
                    pass

        return True, tr("theme_restore_success")
    except Exception as e:
        print(f"[ThemeManager] Restore error: {e}")
        return False, f"{tr('theme_restore_failed')}: {e}"
