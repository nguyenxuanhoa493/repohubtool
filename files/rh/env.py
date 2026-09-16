# -*- coding: utf-8 -*-
"""Startup environment checks, repair, and emulator provisioning."""

import os
import shutil
from .paths import SDCARD_PATH
from . import state
from .j2me import (ensure_latest_j2me_installed, repair_unsafe_jar_names,
                   repair_encrypted_jars)
from .services import is_wifi_awake, apply_wifi_awake

startup_notice = {"msg": None}


def ensure_segacd_installed():
    """Ensure SEGACD emulator configs, scripts, themes, and directories exist on SDCARD."""
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_segacd = os.path.join(app_dir, "emus", "SEGACD")
    if not os.path.isdir(bundled_segacd):
        return False

    target_emu = f"{SDCARD_PATH}/Emus/SEGACD"
    os.makedirs(target_emu, exist_ok=True)
    os.makedirs(f"{SDCARD_PATH}/Roms/SEGACD", exist_ok=True)
    os.makedirs(f"{SDCARD_PATH}/Imgs/SEGACD", exist_ok=True)

    # Sync emulator scripts & config
    try:
        for fname in os.listdir(bundled_segacd):
            src = os.path.join(bundled_segacd, fname)
            dst = os.path.join(target_emu, fname)
            if not os.path.isfile(src):
                continue
            should_copy = False
            if not os.path.exists(dst):
                should_copy = True
            else:
                try:
                    if os.path.getsize(src) != os.path.getsize(dst):
                        should_copy = True
                except OSError:
                    should_copy = True
            if should_copy:
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    print(f"Error copying SEGACD {fname}: {e}")
            if fname.endswith(".sh"):
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
    except Exception as e:
        print(f"Error syncing SEGACD emulator files: {e}")

    # Sync theme files
    bundled_theme = os.path.join(app_dir, "emus", "_theme")
    if os.path.isdir(bundled_theme):
        target_theme = f"{SDCARD_PATH}/Emus/_theme"
        os.makedirs(target_theme, exist_ok=True)
        for tf in ("bg-segacd.png", "ic-segacd.png", "poster-segacd.png"):
            tsrc = os.path.join(bundled_theme, tf)
            tdst = os.path.join(target_theme, tf)
            if os.path.isfile(tsrc) and (not os.path.exists(tdst) or os.path.getsize(tsrc) != os.path.getsize(tdst)):
                try:
                    shutil.copy2(tsrc, tdst)
                except Exception as e:
                    print(f"Error copying theme {tf}: {e}")
    return True


def auto_check_and_supplement_environment():
    """Silently checks and auto-supplements missing libraries, emulator cores, and fixes permissions."""
    repaired_items = []
    
    # 1. Luon kiem tra va cai/cap nhat gia lap Java moi nhat khi mo app
    try:
        ok_java, msg_java = ensure_latest_j2me_installed()
        if ok_java and msg_java:
            startup_notice["msg"] = msg_java
            repaired_items.append(msg_java)
    except Exception as e:
        print(f"Error ensuring latest J2ME runtime on startup: {e}")

    # 1b. Tu dong kiem tra va cai dat/dong bo gia lap Sega CD
    try:
        ensure_segacd_installed()
    except Exception as e:
        print(f"Error ensuring SEGACD runtime on startup: {e}")

    # 1c. Sua ten cac file JAR co ky tu gay loi
    try:
        n_fixed = repair_unsafe_jar_names()
        if n_fixed:
            msg_fix = (f"Đã sửa tên {n_fixed} game Java để mở được"
                       if state.current_lang == "VI"
                       else f"Renamed {n_fixed} Java games so they will open")
            startup_notice["msg"] = msg_fix
            repaired_items.append(msg_fix)
    except Exception as e:
        print(f"Error repairing J2ME jar names: {e}")

    # 1d. Sua file JAR bi khoa sai
    try:
        n_jar = repair_encrypted_jars()
        if n_jar:
            msg_jar = (f"Đã sửa {n_jar} game Java bị khoá sai để mở được"
                       if state.current_lang == "VI"
                       else f"Repaired {n_jar} Java games the emulator refused to open")
            startup_notice["msg"] = msg_jar
            repaired_items.append(msg_jar)
    except Exception as e:
        print(f"Error repairing encrypted J2ME jars: {e}")

    # 2. Ap dung lai cai dat Wi-Fi power save neu dang bat
    try:
        if state.wifi_awake and not is_wifi_awake():
            if apply_wifi_awake(True):
                repaired_items.append("Đã giữ WiFi luôn thức theo cài đặt" if state.current_lang == "VI"
                                      else "Reapplied keep-Wi-Fi-awake setting")
    except Exception as e:
        print(f"Error reapplying Wi-Fi power save: {e}")

    # 3. Tao san cac thu muc ROMs & Imgs tieu chuan
    for d in [f"{SDCARD_PATH}/Roms/JAVA", f"{SDCARD_PATH}/Imgs/JAVA",
              f"{SDCARD_PATH}/Roms/SEGACD", f"{SDCARD_PATH}/Imgs/SEGACD",
              f"{SDCARD_PATH}/Apps/RetroHub/catalog"]:
        try:
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
        except Exception:
            pass

    # 4. Cap quyen thuc thi cho cac script launch
    try:
        if os.path.exists(f"{SDCARD_PATH}/Emus/JAVA/launch.sh"):
            os.chmod(f"{SDCARD_PATH}/Emus/JAVA/launch.sh", 0o755)
        for sname in ("launch.sh", "launch_genplus.sh", "launch_genplus_wide.sh", "cpufreq.sh", "cpuswitch.sh"):
            sp = f"{SDCARD_PATH}/Emus/SEGACD/{sname}"
            if os.path.exists(sp):
                os.chmod(sp, 0o755)
    except Exception:
        pass

    return repaired_items
