# -*- coding: utf-8 -*-
"""Emulator Store & Manager for TrimUI RetroHub.

Manages emulator package detection, installation from .tar.gz archives,
core status, ROM directory creation, and uninstallation.
"""

import os
import json
import shutil
import tarfile
import urllib.request

from . import paths
from .emulators import resolve_core_name, _config_of

# Emulator tarballs are content, not source. They live as assets on a GitHub
# Release (see _src/publish_assets.py) instead of in git, which keeps a fresh
# clone small. Asset filenames here contain no spaces, so the name is unchanged.
ASSET_BASE = "https://github.com/nguyenxuanhoa493/repohubtool/releases/download/assets/"
ONLINE_CDN_BASE = ASSET_BASE
GITHUB_RAW_BASE = ASSET_BASE


def get_emus_catalog():
    """Load the emulators catalog json, returning a list of system definitions."""
    if os.path.isfile(paths.EMUS_CATALOG_FILE):
        try:
            with open(paths.EMUS_CATALOG_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, dict) and "systems" in data:
                    return data["systems"]
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[EmulatorStore] Error loading catalog: {e}")
    return []


def count_roms_for_system(sys_id, extlist=""):
    """Count valid ROM files in the system ROM folder."""
    rom_folder = paths.resolve_rom_dir(sys_id)
    if not os.path.isdir(rom_folder):
        return 0
    valid_exts = set()
    if extlist:
        valid_exts = {f".{ext.strip().lower()}" for ext in extlist.split("|") if ext.strip()}
    
    count = 0
    try:
        for entry in os.listdir(rom_folder):
            if entry.startswith("."):
                continue
            full_path = os.path.join(rom_folder, entry)
            if os.path.isfile(full_path):
                if not valid_exts:
                    count += 1
                else:
                    _, ext = os.path.splitext(entry)
                    if ext.lower() in valid_exts:
                        count += 1
            elif os.path.isdir(full_path):
                count += 1
    except OSError:
        pass
    return count


def get_emus_status():
    """Get the full catalog with real-time installation and ROM status on SD card."""
    catalog = get_emus_catalog()
    installed_emus = set()
    if os.path.isdir(paths.EMUS_DIR):
        try:
            installed_emus = {
                d for d in os.listdir(paths.EMUS_DIR)
                if os.path.isdir(os.path.join(paths.EMUS_DIR, d)) and not d.startswith(".") and not d.startswith("_")
            }
        except OSError:
            pass

    results = []
    for item in catalog:
        sys_id = item.get("id")
        emu_path = os.path.join(paths.EMUS_DIR, sys_id)
        is_installed = sys_id in installed_emus or os.path.isdir(emu_path)
        
        cfg = {}
        active_core = item.get("core", "")
        if is_installed:
            cfg = _config_of(emu_path)
            detected_core = resolve_core_name(sys_id, emus_root=paths.EMUS_DIR)
            if detected_core:
                active_core = detected_core
            elif cfg.get("launch"):
                active_core = str(cfg.get("launch"))

        extlist = item.get("extlist") or cfg.get("extlist", "")
        rom_count = count_roms_for_system(sys_id, extlist)

        # Check local package availability
        local_pkg = os.path.join(paths.LOCAL_EMUS_PACKAGES_DIR, f"{sys_id}.tar.gz")
        has_local_pkg = os.path.isfile(local_pkg)

        entry = dict(item)
        entry["installed"] = is_installed
        entry["active_core"] = active_core
        entry["rom_count"] = rom_count
        entry["has_local_pkg"] = has_local_pkg
        entry["emu_dir_exists"] = is_installed
        results.append(entry)

    return results


def install_emu(sys_id):
    """Install or update an emulator by extracting its .tar.gz archive into Emus/."""
    sys_id = str(sys_id).strip().upper()
    tar_name = f"{sys_id}.tar.gz"
    local_pkg = os.path.join(paths.LOCAL_EMUS_PACKAGES_DIR, tar_name)
    
    temp_download = f"/tmp/{tar_name}"
    target_archive = None

    if os.path.isfile(local_pkg):
        target_archive = local_pkg
    else:
        # Fallback candidate search
        candidates = [
            os.path.join(paths.APP_DIR, "emus", tar_name),
            os.path.join(os.path.dirname(paths.APP_DIR), "emus", tar_name),
        ]
        for cand in candidates:
            if os.path.isfile(cand):
                target_archive = cand
                break

    if not target_archive:
        # Try downloading from CDN or GitHub Raw
        urls_to_try = [
            f"{ONLINE_CDN_BASE}{tar_name}",
            f"{GITHUB_RAW_BASE}{tar_name}",
        ]
        downloaded = False
        for url in urls_to_try:
            try:
                print(f"[EmulatorStore] Downloading {url}...")
                req = urllib.request.Request(url, headers={"User-Agent": "RetroHub-EmulatorStore/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp, open(temp_download, "wb") as out:
                    shutil.copyfileobj(resp, out)
                if os.path.isfile(temp_download) and os.path.getsize(temp_download) > 0:
                    target_archive = temp_download
                    downloaded = True
                    break
            except Exception as e:
                print(f"[EmulatorStore] Download failed from {url}: {e}")

        if not downloaded or not target_archive:
            return {"success": False, "error": f"Không tìm thấy gói cài đặt cho hệ máy {sys_id}."}

    os.makedirs(paths.EMUS_DIR, exist_ok=True)
    target_emu_dir = os.path.join(paths.EMUS_DIR, sys_id)

    try:
        with tarfile.open(target_archive, "r:gz") as tar:
            tar.extractall(path=paths.EMUS_DIR)

        # Set executable permissions on scripts and binaries
        if os.path.isdir(target_emu_dir):
            for root, _, files in os.walk(target_emu_dir):
                for file in files:
                    if file.endswith(".sh") or "." not in file:
                        full_f = os.path.join(root, file)
                        try:
                            os.chmod(full_f, 0o755)
                        except OSError:
                            pass

        # Ensure ROMs directory exists
        rom_dir = paths.resolve_rom_dir(sys_id)
        os.makedirs(rom_dir, exist_ok=True)

        # Ensure theme assets in Emus/_theme if present in app assets
        os.makedirs(paths.EMU_THEME_DIR, exist_ok=True)
        preview_dir = os.path.join(paths.APP_DIR, "assets", "emus_preview")
        if os.path.isdir(preview_dir):
            for suffix in ("ic-", "poster-", "bg-"):
                asset_name = f"{suffix}{sys_id.lower()}.png"
                src_asset = os.path.join(preview_dir, asset_name)
                dst_asset = os.path.join(paths.EMU_THEME_DIR, asset_name)
                if os.path.isfile(src_asset) and not os.path.isfile(dst_asset):
                    try:
                        shutil.copy2(src_asset, dst_asset)
                    except Exception:
                        pass

        # Cleanup tmp download
        if target_archive == temp_download and os.path.isfile(temp_download):
            try:
                os.remove(temp_download)
            except OSError:
                pass

        return {
            "success": True,
            "message": f"Đã cài đặt thành công hệ máy {sys_id}!",
            "sys_id": sys_id,
            "emu_dir": target_emu_dir,
            "rom_dir": rom_dir,
        }
    except Exception as e:
        return {"success": False, "error": f"Lỗi khi giải nén hệ máy {sys_id}: {str(e)}"}


def uninstall_emu(sys_id):
    """Uninstall an emulator folder from Emus/, NEVER deleting user ROMs."""
    sys_id = str(sys_id).strip().upper()
    target_emu_dir = os.path.join(paths.EMUS_DIR, sys_id)
    
    if not os.path.isdir(target_emu_dir):
        return {"success": False, "error": f"Hệ máy {sys_id} chưa được cài đặt."}

    try:
        shutil.rmtree(target_emu_dir)
        return {
            "success": True,
            "message": f"Đã gỡ bỏ hệ máy {sys_id} thành công (Dữ liệu ROM game vẫn được giữ nguyên).",
            "sys_id": sys_id,
        }
    except Exception as e:
        return {"success": False, "error": f"Lỗi khi gỡ bỏ hệ máy {sys_id}: {str(e)}"}
