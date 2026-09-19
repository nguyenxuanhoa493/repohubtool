# -*- coding: utf-8 -*-
"""Theme Manager for Trimui Brick Pro / Handhelds.

Handles:
- Lightweight catalog loading (names, metadata & previews) with instant in-memory caching.
- On-demand Online / Remote Download & extraction directly into /mnt/SDCARD/Themes/<ThemeName>.
- Uninstallation to free up SD card space anytime.
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
    THEMES_CATALOG_FILE,
    LOCAL_THEMES_REPO_DIR,
)
from . import state
from .i18n import tr

# Theme zips phan phoi uu tien qua Cloudflare R2 CDN; fallback GitHub Releases.
ASSET_BASE = "https://cdn.xuanhoa493.com/"
GITHUB_ASSET_BASE = "https://github.com/nguyenxuanhoa493/repohubtool/releases/download/assets/"

_SSL_CTX = None
try:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CTX = None


_THEMES_CACHE = None



def load_themes_catalog(force_reload: bool = False) -> List[Dict]:
    """Loads lightweight theme catalog with installation status (Instant in-memory caching)."""
    global _THEMES_CACHE
    if _THEMES_CACHE is not None and not force_reload:
        return _THEMES_CACHE

    catalog_themes = []
    if os.path.isfile(THEMES_CATALOG_FILE):
        try:
            with open(THEMES_CATALOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                catalog_themes = data.get("themes", [])
        except Exception as e:
            print(f"[ThemeManager] Error loading catalog json: {e}")

    # Read installed themes directory ONCE instead of N stat calls
    installed_folders = set()
    if os.path.isdir(THEMES_DIR):
        try:
            installed_folders = {
                d for d in os.listdir(THEMES_DIR)
                if not d.startswith(".") and os.path.isdir(os.path.join(THEMES_DIR, d))
            }
        except Exception:
            pass

    # Read preview directory ONCE instead of N stat calls
    preview_dir = os.path.join(APP_DIR, "assets", "themes_preview")
    available_previews = set()
    if os.path.isdir(preview_dir):
        try:
            available_previews = set(os.listdir(preview_dir))
        except Exception:
            pass

    results = []
    for t in catalog_themes:
        folder = t.get("folder") or t.get("id")
        is_installed = folder in installed_folders
        installed_path = os.path.join(THEMES_DIR, folder) if is_installed else None

        # Fast preview path resolution without redundant disk stat calls
        img_name = f"{folder}.png"
        import re
        safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", folder)
        img_safe = f"{safe_name}.png"
        preview_rel = t.get("preview_rel")
        preview_path = None
        if img_safe in available_previews:
            preview_path = os.path.join(preview_dir, img_safe)
        elif preview_rel and os.path.isfile(os.path.join(APP_DIR, preview_rel)):
            preview_path = os.path.join(APP_DIR, preview_rel)
        elif img_name in available_previews:
            preview_path = os.path.join(preview_dir, img_name)
        elif is_installed:
            local_p = os.path.join(THEMES_DIR, folder, "preview.png")
            if os.path.isfile(local_p):
                preview_path = local_p

        item = dict(t)
        item["folder"] = folder
        item["is_installed"] = is_installed
        item["installed_path"] = installed_path
        item["preview_path"] = preview_path
        results.append(item)

    _THEMES_CACHE = results
    return results


def get_theme_preview_path(folder_name: str) -> Optional[str]:
    """Returns local path to theme preview image or None."""
    import re
    safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", folder_name)
    candidates = [
        os.path.join(APP_DIR, "assets", "themes_preview", f"{safe_name}.png"),
        os.path.join(APP_DIR, "assets", "themes_preview", f"{folder_name.replace(' ', '_')}.png"),
        os.path.join(APP_DIR, "assets", "themes_preview", f"{folder_name}.png"),
        os.path.join(THEMES_DIR, folder_name, "preview.png"),
        os.path.join(LOCAL_THEMES_REPO_DIR, folder_name, "preview.png"),
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
        zip_name = f"{urllib.parse.quote(folder)}.zip"

        # Theme zips phan phoi uu tien qua Cloudflare CDN, fallback GitHub Releases
        download_urls = []
        if theme_info.get("download_url"):
            download_urls.append(theme_info["download_url"])
        download_urls.append(
            ASSET_BASE + urllib.parse.quote(folder.replace(" ", ".")) + ".zip")
        if theme_info.get("raw_git_url"):
            download_urls.append(theme_info["raw_git_url"])
        download_urls.append(
            GITHUB_ASSET_BASE + urllib.parse.quote(folder.replace(" ", ".")) + ".zip")

        # Loc trung lap nhung giu nguyen thu tu uu tien
        dedup_urls = []
        for u in download_urls:
            if u and u not in dedup_urls:
                dedup_urls.append(u)
        download_urls = dedup_urls

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

        global _THEMES_CACHE
        _THEMES_CACHE = None
        return True, tr("theme_install_success")

    except Exception as e:
        print(f"[ThemeManager] Install failed: {e}")
        return False, f"{tr('theme_install_failed')}: {e}"


def uninstall_theme(folder_name: str) -> Tuple[bool, str]:
    """Uninstalls a theme directory from SDCARD/Themes/ to free up space."""
    global _THEMES_CACHE
    target_dir = os.path.join(THEMES_DIR, folder_name)
    if not os.path.isdir(target_dir):
        return False, "Theme chưa được cài đặt!" if state.current_lang == "VI" else "Theme is not installed!"

    try:
        shutil.rmtree(target_dir)
        _THEMES_CACHE = None
        return True, tr("theme_uninstall_success")
    except Exception as e:
        print(f"[ThemeManager] Uninstall error: {e}")
        return False, f"Lỗi gỡ bỏ: {e}" if state.current_lang == "VI" else f"Uninstall error: {e}"

