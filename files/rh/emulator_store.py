# -*- coding: utf-8 -*-
"""Emulator Store & Manager for TrimUI RetroHub.

Manages emulator package detection, installation from .tar.gz archives,
core status, ROM directory creation, and uninstallation.
"""

import os
import json
import ssl
import shutil
import subprocess
import tarfile
import urllib.request

from . import paths
from .storage import unlock
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


def safe_extract_tar_gz(archive_path, target_root, sys_id=None):
    """Giai nen an toan goi .tar.gz vao target_root tren the nho FAT32/exFAT.

    Thu tu uu tien:
    1. Lệnh tar native cua he thong: nhanh nhat, stream truc tiep, khong ton RAM,
       bo qua xung dot quyen POSIX tren FAT32.
    2. Binary 7-Zip static (7zzs) di kem ung dung.
    3. Trinh doc tarfile thuan Python voi set_attrs=False va kiem tra OWASP path traversal.
    """
    if not os.path.isfile(archive_path):
        return False, "Tap tin archive khong ton tai."

    os.makedirs(target_root, exist_ok=True)
    target_emu_dir = os.path.join(target_root, sys_id) if sys_id else target_root

    # 0. Mo khoa (unlock) cay thu muc dich neu da ton tai de tranh co DOS Read-Only
    if os.path.exists(target_emu_dir):
        unlock(target_emu_dir)
        try:
            for root, dirs, files in os.walk(target_emu_dir):
                for d in dirs:
                    unlock(os.path.join(root, d))
                for f in files:
                    unlock(os.path.join(root, f))
        except OSError:
            pass

    # Tier 1: Try native tar CLI
    try:
        cmd = ["tar", "-xzf", archive_path, "-C", target_root]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if res.returncode == 0:
            return True, None
    except Exception:
        pass

    # Tier 2: Try 7-Zip (7zzs) if available
    try:
        from .archive import sevenzip
        exe = sevenzip()
        if exe:
            p1 = subprocess.Popen([exe, "x", archive_path, "-so", "-y"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p2 = subprocess.Popen([exe, "x", "-si", "-ttar", f"-o{target_root}", "-y", "-bso0"], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p1.stdout.close()
            _, err2 = p2.communicate(timeout=180)
            if p2.returncode == 0:
                return True, None
    except Exception:
        pass

    # Tier 3: Python tarfile fallback (member-by-member safe streaming, no set_attrs)
    try:
        dest_abs = os.path.abspath(target_root)
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                # OWASP check path traversal
                target_path = os.path.abspath(os.path.join(dest_abs, member.name))
                if not (target_path == dest_abs or target_path.startswith(dest_abs + os.sep)):
                    continue

                if member.isdir():
                    os.makedirs(target_path, exist_ok=True)
                    continue

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                unlock(target_path)

                extracted = False
                try:
                    tar.extract(member, path=target_root, set_attrs=False)
                    extracted = True
                except Exception:
                    pass

                if not extracted:
                    f_in = tar.extractfile(member)
                    if f_in:
                        try:
                            with open(target_path, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        finally:
                            f_in.close()
        return True, None
    except Exception as e:
        return False, str(e)


def install_emu(sys_id):
    """Install or update an emulator by extracting its .tar.gz archive into Emus/."""
    sys_id = str(sys_id).strip().upper()
    tar_name = f"{sys_id}.tar.gz"
    local_pkg = os.path.join(paths.LOCAL_EMUS_PACKAGES_DIR, tar_name)
    
    # Uu tien dung thu muc tam tren the nho SD de tranh chiem dung bo nho RAM/tmpfs
    temp_download = f"/tmp/{tar_name}"
    try:
        if os.path.isdir(paths.SDCARD_PATH):
            sd_tmp = paths.TEMP_DOWNLOAD_DIR
            os.makedirs(sd_tmp, exist_ok=True)
            temp_download = os.path.join(sd_tmp, tar_name)
    except OSError:
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
        last_error = ""

        # Build unverified SSL context to bypass missing CA certificates on TrimUI
        ssl_ctx = None
        try:
            ssl_ctx = ssl._create_unverified_context()
        except Exception:
            try:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            except Exception:
                ssl_ctx = None

        for url in urls_to_try:
            # Clean any stale/partial download
            if os.path.isfile(temp_download):
                try:
                    os.remove(temp_download)
                except OSError:
                    pass

            # 1. Try urllib with unverified SSL context
            try:
                print(f"[EmulatorStore] Downloading {url}...")
                req = urllib.request.Request(url, headers={"User-Agent": "RetroHub-EmulatorStore/1.0"})
                open_kwargs = {"timeout": 60}
                if ssl_ctx:
                    open_kwargs["context"] = ssl_ctx
                with urllib.request.urlopen(req, **open_kwargs) as resp, open(temp_download, "wb") as out:
                    shutil.copyfileobj(resp, out)
                if os.path.isfile(temp_download) and os.path.getsize(temp_download) > 0:
                    target_archive = temp_download
                    downloaded = True
                    break
            except Exception as e:
                last_error = str(e)
                print(f"[EmulatorStore] urllib download failed from {url}: {e}")

            # 2. Fallback to curl (immune to TrimUI Python SSL issues & supports redirects)
            try:
                print(f"[EmulatorStore] Fallback to curl for {url}...")
                cmd = ["curl", "-fsSLk", "--connect-timeout", "15", "--max-time", "180", "-o", temp_download, url]
                ret = subprocess.run(cmd, capture_output=True, timeout=190)
                if ret.returncode == 0 and os.path.isfile(temp_download) and os.path.getsize(temp_download) > 0:
                    target_archive = temp_download
                    downloaded = True
                    break
                else:
                    err_out = ret.stderr.decode("utf-8", errors="ignore").strip()
                    if err_out:
                        last_error = f"curl: {err_out}"
            except Exception as ce:
                last_error = f"curl error: {ce}"
                print(f"[EmulatorStore] curl download failed from {url}: {ce}")

        if not downloaded or not target_archive:
            if os.path.isfile(temp_download):
                try:
                    os.remove(temp_download)
                except OSError:
                    pass
            err_msg = f"Tải {sys_id} online thất bại. Vui lòng kiểm tra Wi-Fi."
            if last_error:
                err_msg = f"Lỗi tải {sys_id}: {last_error[:40]}"
            return {"success": False, "error": err_msg}

    os.makedirs(paths.EMUS_DIR, exist_ok=True)
    target_emu_dir = os.path.join(paths.EMUS_DIR, sys_id)

    try:
        ok_ext, err_ext = safe_extract_tar_gz(target_archive, paths.EMUS_DIR, sys_id)
        if not ok_ext:
            if target_archive == temp_download and os.path.isfile(temp_download):
                try:
                    os.remove(temp_download)
                except OSError:
                    pass
            err_msg = f"Lỗi khi giải nén hệ máy {sys_id}: {err_ext}"
            if "Input/output error" in str(err_ext) or "Errno 5" in str(err_ext):
                err_msg += " (Thẻ nhớ lỗi cluster/định dạng FAT32. Vui lòng cắm thẻ vào PC để quét sửa lỗi Scan & Fix)."
            return {"success": False, "error": err_msg}

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

        # Rieng he may JAVA: kich hoat dong bo save game, nextui pak va cau hinh
        if sys_id == "JAVA":
            try:
                from .j2me import ensure_latest_j2me_installed
                ensure_latest_j2me_installed()
            except Exception as je:
                print(f"[EmulatorStore] Java post-install sync warning: {je}")

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
        if target_archive == temp_download and os.path.isfile(temp_download):
            try:
                os.remove(temp_download)
            except OSError:
                pass
        err_msg = f"Lỗi khi giải nén hệ máy {sys_id}: {str(e)}"
        if "Input/output error" in str(e) or "Errno 5" in str(e):
            err_msg += " (Thẻ nhớ lỗi cluster/định dạng FAT32. Vui lòng cắm thẻ vào PC để quét sửa lỗi Scan & Fix)."
        return {"success": False, "error": err_msg}


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
