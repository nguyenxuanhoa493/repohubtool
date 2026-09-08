# -*- coding: utf-8 -*-
"""Save Game Manager for TrimUI handheld devices (Stock OS, NextUI, CrossMix):
Scan, backup, and restore game saves (.srm, .sav, .dsv, .eep, etc.) and save states
(.state*) into timestamped zip archives.
"""

import os
import re
import json
import time
import zipfile
import shutil
from datetime import datetime
from .paths import SDCARD_PATH

SAVE_EXTS = {
    ".srm", ".sav", ".state", ".dsv", ".eep", ".nvram", ".mcr",
    ".rtc", ".fs", ".ram", ".fla"
}

BACKUP_DIR = os.path.join(SDCARD_PATH, "RetroHub", "backups")


def _is_save_file(filename):
    lower = filename.lower()
    if lower.startswith("._") or lower == ".ds_store":
        return False
    ext = os.path.splitext(lower)[1]
    if ext in SAVE_EXTS:
        return True
    if re.match(r"^\.state\d*$", ext):
        return True
    if ".state." in lower or lower.endswith(".state.auto"):
        return True
    return False


def get_save_directories(base_sd=None):
    """Xác định các thư mục lưu trữ save game và save state trên thiết bị."""
    sd = base_sd or SDCARD_PATH
    dirs = [
        # RetroArch standard & hidden directories
        os.path.join(sd, "RetroArch", ".retroarch", "saves"),
        os.path.join(sd, "RetroArch", ".retroarch", "states"),
        os.path.join(sd, "RetroArch", "saves"),
        os.path.join(sd, "RetroArch", "states"),

        # Standalone emulators
        os.path.join(sd, ".config", "ppsspp", "PSP", "SAVEDATA"),
        os.path.join(sd, "PSP", "SAVEDATA"),
        os.path.join(sd, "Emus", "NDS", "backup"),
        os.path.join(sd, "Emus", "NDS", "savestates"),

        # NextUI userdata
        os.path.join(sd, ".userdata"),
    ]
    return [d for d in dirs if os.path.isdir(d)]


def scan_all_saves(base_sd=None, include_roms=True):
    """Quét toàn bộ file save và state trên thẻ nhớ."""
    sd = base_sd or SDCARD_PATH
    save_files = []
    seen_paths = set()

    # 1. Quét các thư mục lưu save chuyên dụng
    target_dirs = get_save_directories(sd)
    for d in target_dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if _is_save_file(f):
                    full_p = os.path.join(root, f)
                    if full_p not in seen_paths and os.path.isfile(full_p):
                        seen_paths.add(full_p)
                        try:
                            st = os.stat(full_p)
                            save_files.append({
                                "path": full_p,
                                "name": f,
                                "size": st.st_size,
                                "mtime": st.st_mtime,
                                "rel_sd": os.path.relpath(full_p, sd)
                            })
                        except OSError:
                            pass

    # 2. Quét trong thư mục Roms/ nếu cấu hình lưu save cùng thư mục game
    roms_dir = os.path.join(sd, "Roms")
    if include_roms and os.path.isdir(roms_dir):
        for root, _, files in os.walk(roms_dir):
            for f in files:
                if _is_save_file(f):
                    full_p = os.path.join(root, f)
                    if full_p not in seen_paths and os.path.isfile(full_p):
                        seen_paths.add(full_p)
                        try:
                            st = os.stat(full_p)
                            save_files.append({
                                "path": full_p,
                                "name": f,
                                "size": st.st_size,
                                "mtime": st.st_mtime,
                                "rel_sd": os.path.relpath(full_p, sd)
                            })
                        except OSError:
                            pass

    return sorted(save_files, key=lambda x: x["mtime"], reverse=True)


def get_saves_stats(base_sd=None):
    """Thống kê tổng quan về save game và save state."""
    saves = scan_all_saves(base_sd=base_sd)
    tot_bytes = sum(s["size"] for s in saves)
    types_count = {"srm": 0, "state": 0, "other": 0}
    for s in saves:
        name = s["name"].lower()
        if name.endswith(".srm") or name.endswith(".sav"):
            types_count["srm"] += 1
        elif "state" in name:
            types_count["state"] += 1
        else:
            types_count["other"] += 1

    return {
        "total_files": len(saves),
        "total_bytes": tot_bytes,
        "types": types_count,
        "samples": [s["name"] for s in saves[:5]]
    }


def create_save_backup(base_sd=None, note=""):
    """Nén toàn bộ file save game thành 1 file ZIP lưu trữ có đánh dấu thời gian.
    
    Returns: (bool_success, zip_path_or_err, stats_dict)
    """
    sd = base_sd or SDCARD_PATH
    backup_dir = os.path.join(sd, "RetroHub", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    saves = scan_all_saves(base_sd=sd)
    if not saves:
        return False, "Không tìm thấy file save nào trên thẻ nhớ để sao lưu!", {}

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    zip_name = f"saves_backup_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_name)
    tmp_zip = f"{zip_path}.tmp"

    manifest_data = {
        "version": "1.0",
        "created_at": now.isoformat(),
        "date_str": now.strftime("%Y-%m-%d %H:%M:%S"),
        "note": note,
        "total_files": len(saves),
        "total_bytes": sum(s["size"] for s in saves),
        "files": []
    }

    try:
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in saves:
                abs_p = item["path"]
                rel_p = item["rel_sd"]
                manifest_data["files"].append({
                    "rel_sd": rel_p,
                    "size": item["size"],
                    "mtime": item["mtime"],
                    "name": item["name"]
                })
                zf.write(abs_p, arcname=rel_p)

            # Ghi manifest vào zip
            zf.writestr("_backup_manifest.json", json.dumps(manifest_data, ensure_ascii=False, indent=2))

        # Atomic move
        os.replace(tmp_zip, zip_path)
        stats = {
            "total_files": len(saves),
            "total_bytes": os.path.getsize(zip_path),
            "filename": zip_name,
            "path": zip_path,
            "created_at": manifest_data["date_str"]
        }
        return True, zip_path, stats

    except Exception as e:
        if os.path.isfile(tmp_zip):
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
        return False, f"Lỗi khi nén file sao lưu: {str(e)}", {}


def list_save_backups(base_sd=None):
    """Liệt kê toàn bộ các bản sao lưu đã có trong thư mục backups."""
    sd = base_sd or SDCARD_PATH
    backup_dir = os.path.join(sd, "RetroHub", "backups")
    if not os.path.isdir(backup_dir):
        return []

    backups = []
    try:
        entries = os.listdir(backup_dir)
    except OSError:
        return []

    for name in entries:
        if name.startswith("saves_backup_") and name.endswith(".zip"):
            full_p = os.path.join(backup_dir, name)
            if os.path.isfile(full_p):
                try:
                    st = os.stat(full_p)
                    file_count = 0
                    date_str = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
                    note = ""

                    # Đọc nhanh manifest trong zip nếu có
                    try:
                        with zipfile.ZipFile(full_p, "r") as zf:
                            if "_backup_manifest.json" in zf.namelist():
                                mf_raw = zf.read("_backup_manifest.json").decode("utf-8", "ignore")
                                mf = json.loads(mf_raw)
                                file_count = mf.get("total_files", len(zf.namelist()) - 1)
                                date_str = mf.get("date_str", date_str)
                                note = mf.get("note", "")
                            else:
                                file_count = len(zf.namelist())
                    except Exception:
                        pass

                    backups.append({
                        "filename": name,
                        "filepath": full_p,
                        "size": st.st_size,
                        "mtime": st.st_mtime,
                        "date_str": date_str,
                        "file_count": file_count,
                        "note": note
                    })
                except OSError:
                    pass

    return sorted(backups, key=lambda x: x["mtime"], reverse=True)


def restore_save_backup(zip_path, base_sd=None):
    """Khôi phục các file save game từ file ZIP về đúng thư mục tương ứng trên thẻ nhớ.
    
    Returns: (bool_success, restored_count, error_msg)
    """
    sd = base_sd or SDCARD_PATH
    if not os.path.isfile(zip_path):
        return False, 0, "Không tìm thấy file sao lưu!"

    try:
        restored = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()

            manifest = None
            if "_backup_manifest.json" in namelist:
                try:
                    mf_raw = zf.read("_backup_manifest.json").decode("utf-8", "ignore")
                    manifest = json.loads(mf_raw)
                except Exception:
                    pass

            for member in namelist:
                if member == "_backup_manifest.json" or member.endswith("/"):
                    continue

                # Kiểm tra chống Zip Slip vulnerability
                norm_p = os.path.normpath(member)
                if norm_p.startswith("..") or os.path.isabs(norm_p):
                    continue

                target_dest = os.path.join(sd, norm_p)
                os.makedirs(os.path.dirname(target_dest), exist_ok=True)

                with zf.open(member) as src, open(target_dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                restored += 1

        return True, restored, ""

    except Exception as e:
        return False, 0, f"Lỗi khôi phục save game: {str(e)}"


def delete_save_backup(zip_path):
    """Xóa một bản sao lưu."""
    if os.path.isfile(zip_path):
        try:
            os.remove(zip_path)
            return True, "Đã xóa bản sao lưu thành công!"
        except Exception as e:
            return False, f"Lỗi xóa file: {str(e)}"
    return False, "File sao lưu không tồn tại!"
