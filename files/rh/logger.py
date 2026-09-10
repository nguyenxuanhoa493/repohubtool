# -*- coding: utf-8 -*-
"""Diagnostic & Debug Logging System for RetroHub on TrimUI handhelds:
Captures hardware specs, network status, crash stack traces, rotating log files,
and uploads diagnostic bundles directly to Telegram Bot.
"""

import os
import sys
import ssl
import time
import json
import socket
import platform
import traceback
import threading
import collections
import urllib.request
import urllib.parse
import uuid
from datetime import datetime

try:
    _SSL_CONTEXT = ssl.create_default_context()
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CONTEXT = None

from .paths import SDCARD_PATH, is_nextui

TELEGRAM_BOT_TOKEN = "8843439406:AAEtTnuMk68ilAniAxj8Kl3uTKZmVKEVDDs"
TELEGRAM_CHAT_ID = "663642384"

LOG_DIR = os.path.join(SDCARD_PATH, "RetroHub", "logs")
LOG_FILE = os.path.join(LOG_DIR, "retrohub.log")
LOG_OLD_FILE = os.path.join(LOG_DIR, "retrohub.log.1")
REPORT_FILE = os.path.join(SDCARD_PATH, "RetroHub_Debug_Report.txt")

MAX_LOG_BYTES = 1024 * 1024  # 1 MB per log file
_RECENT_LOGS = collections.deque(maxlen=300)
_LOG_LOCK = threading.Lock()
_INITIALIZED = False


def _get_local_ip():
    """Lấy địa chỉ IP Wi-Fi nội mạng hiện tại."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Chưa có IP (Chưa kết nối Wi-Fi)"


def _get_memory_info():
    """Đọc thông tin RAM từ /proc/meminfo."""
    mem_info = {"total_mb": 0, "free_mb": 0, "avail_mb": 0}
    try:
        if os.path.isfile("/proc/meminfo"):
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip().split()[0]
                        if k == "MemTotal":
                            mem_info["total_mb"] = int(v) // 1024
                        elif k == "MemFree":
                            mem_info["free_mb"] = int(v) // 1024
                        elif k == "MemAvailable":
                            mem_info["avail_mb"] = int(v) // 1024
    except Exception:
        pass
    return mem_info


def _get_storage_info(path=None):
    """Đo dung lượng thẻ nhớ SD Card."""
    target = path or SDCARD_PATH
    try:
        st = os.statvfs(target)
        free_bytes = st.f_bavail * st.f_frsize
        total_bytes = st.f_blocks * st.f_frsize
        return {
            "total_gb": round(total_bytes / (1024**3), 2),
            "free_gb": round(free_bytes / (1024**3), 2),
            "free_pct": round((free_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0
        }
    except Exception:
        return {"total_gb": 0, "free_gb": 0, "free_pct": 0}


def get_device_id():
    """Lấy mã định danh ngẫu nhiên duy nhất cho máy từ state/settings."""
    try:
        from . import state
        dev_id = getattr(state, "device_id", "")
        if dev_id:
            return dev_id
    except Exception:
        pass
    return "RH-0000"


def get_log_size_str():
    """Lấy kích thước định dạng chuỗi của file log hiện tại trên máy."""
    try:
        sz = 0
        if os.path.isfile(LOG_FILE):
            sz += os.path.getsize(LOG_FILE)
        if os.path.isfile(LOG_OLD_FILE):
            sz += os.path.getsize(LOG_OLD_FILE)
        ra_log = os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "logs", "retroarch.log")
        if os.path.isfile(ra_log):
            sz += os.path.getsize(ra_log)
        java_log = os.path.join(SDCARD_PATH, "RetroHub-java.log")
        if os.path.isfile(java_log):
            sz += os.path.getsize(java_log)
        if sz >= 1024 * 1024:
            return f"{sz / (1024 * 1024):.1f} MB"
        elif sz >= 1024:
            return f"{sz / 1024:.1f} KB"
        else:
            return f"{sz} B"
    except Exception:
        return "0 B"


def clear_log():
    """Làm sạch toàn bộ nhật ký log file và bộ nhớ đệm RAM."""
    with _LOG_LOCK:
        _RECENT_LOGS.clear()
        try:
            if os.path.isfile(LOG_FILE):
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
            if os.path.isfile(LOG_OLD_FILE):
                os.remove(LOG_OLD_FILE)
            if os.path.isfile(REPORT_FILE):
                os.remove(REPORT_FILE)
            ra_log = os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "logs", "retroarch.log")
            if os.path.isfile(ra_log):
                with open(ra_log, "w", encoding="utf-8") as f:
                    f.write("")
            java_log = os.path.join(SDCARD_PATH, "RetroHub-java.log")
            if os.path.isfile(java_log):
                with open(java_log, "w", encoding="utf-8") as f:
                    f.write("")
        except Exception:
            pass
    dev_id = get_device_id()
    log_info(f"Nhat ky he thong da duoc lam sach boi nguoi dung (Ma may: {dev_id})")
    return True


def get_system_diagnostics():
    """Tổng hợp toàn bộ thông tin chẩn đoán phần cứng, hệ điều hành và mạng."""
    from .version import APP_VERSION

    mem = _get_memory_info()
    sd = _get_storage_info()
    ip = _get_local_ip()
    dev_id = get_device_id()

    # Nhận diện dòng máy
    device_model = "TrimUI Handheld"
    if os.path.isfile("/usr/trimui/bin/trimui_inputd") or os.path.isdir("/usr/trimui"):
        device_model = "TrimUI Smart Pro / Brick"
    if is_nextui():
        device_model += " (NextUI OS)"
    elif os.path.isdir("/mnt/SDCARD/Emus"):
        device_model += " (Stock OS / CrossMix)"

    return {
        "device_id": dev_id,
        "app_version": APP_VERSION,
        "device_model": device_model,
        "python_version": platform.python_version(),
        "kernel": platform.release(),
        "ip_address": ip,
        "ram_total_mb": mem["total_mb"],
        "ram_avail_mb": mem["avail_mb"],
        "sd_total_gb": sd["total_gb"],
        "sd_free_gb": sd["free_gb"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def log(msg, level="INFO"):
    """Ghi một dòng nhật ký vào file và bộ nhớ đệm RAM nếu chức năng ghi log đang BẬT."""
    try:
        from . import state
        if not getattr(state, "enable_logging", False):
            return
    except Exception:
        pass

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now_str}] [{level}] {msg}"

    with _LOG_LOCK:
        _RECENT_LOGS.append(line)

        # Ghi log file trên thẻ nhớ nếu có thể
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            if os.path.isfile(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_BYTES:
                if os.path.isfile(LOG_OLD_FILE):
                    os.remove(LOG_OLD_FILE)
                os.rename(LOG_FILE, LOG_OLD_FILE)

            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    # Đồng thời in ra stdout nếu đang test console
    try:
        print(line)
    except Exception:
        pass


def log_info(msg):
    log(msg, "INFO")


def log_warn(msg):
    log(msg, "WARN")


def log_error(msg):
    log(msg, "ERROR")


def log_debug(msg):
    log(msg, "DEBUG")


def get_recent_logs(max_lines=100):
    """Lấy danh sách các dòng log gần nhất từ bộ nhớ đệm RAM."""
    with _LOG_LOCK:
        lines = list(_RECENT_LOGS)
        return lines[-max_lines:]


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Bắt và ghi nhận mọi crash chưa được xử lý vào log file."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    crash_msg = "".join(tb_lines).strip()
    log_error(f"UNHANDLED CRASH:\n{crash_msg}")

    # Xuất ngay report ra thẻ nhớ
    try:
        generate_debug_report()
    except Exception:
        pass

    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def init_logger():
    """Khởi động hệ thống ghi log và gắn hook bắt lỗi."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass

    sys.excepthook = _handle_unhandled_exception

    try:
        from . import state
        if getattr(state, "enable_logging", False):
            sync_retroarch_logging(True)
    except Exception:
        pass

    diag = get_system_diagnostics()
    log_info("=" * 60)
    log_info(f"RetroHub v{diag['app_version']} khoi dong tren {diag['device_model']}")
    log_info(f"Python: {diag['python_version']} | Kernel: {diag['kernel']}")
    log_info(f"RAM: {diag['ram_avail_mb']}/{diag['ram_total_mb']} MB kha dung | The nho: {diag['sd_free_gb']}/{diag['sd_total_gb']} GB")
    log_info(f"Dia chi IP: {diag['ip_address']}")
    log_info("=" * 60)


def sync_retroarch_logging(enable=True):
    """Đồng bộ cấu hình ghi log giữa RetroHub và RetroArch.
    Khi BẬT: RetroArch sẽ tự động ghi toàn bộ log thực thi game vào file.
    """
    ra_cfg = os.path.join(SDCARD_PATH, "RetroArch", "retroarch.cfg")
    if not os.path.isfile(ra_cfg):
        return False
    try:
        log_dir_path = os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "logs")
        if enable:
            os.makedirs(log_dir_path, exist_ok=True)

        with open(ra_cfg, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        keys_to_set = {
            "log_to_file": '"true"' if enable else '"false"',
            "log_verbosity": '"true"' if enable else '"false"',
            "log_dir": f'"{log_dir_path}"'
        }

        new_lines = []
        found_keys = set()
        for line in lines:
            line_s = line.strip()
            matched = False
            for k, val in keys_to_set.items():
                if line_s.startswith(f"{k} =") or line_s.startswith(f"{k}="):
                    new_lines.append(f"{k} = {val}\n")
                    found_keys.add(k)
                    matched = True
                    break
            if not matched:
                new_lines.append(line)

        for k, val in keys_to_set.items():
            if k not in found_keys:
                new_lines.append(f"{k} = {val}\n")

        with open(ra_cfg, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        log_info(f"Dong bo trang thai ghi log RetroArch -> {enable}")
        return True
    except Exception as e:
        log_error(f"Loi dong bo log sang retroarch.cfg: {e}")
        return False


def _get_recent_game_diagnostics():
    """Trích xuất thông tin chi tiết về game vừa khởi chạy gần nhất từ RetroArch history."""
    candidates = [
        os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "content_history.lpl"),
        os.path.join(SDCARD_PATH, "RetroArch", "content_history.lpl"),
        os.path.join(SDCARD_PATH, "System", "recent.json"),
    ]
    items = []
    for fpath in candidates:
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
                if content.startswith("{"):
                    data = json.loads(content)
                    raw_items = data.get("items", [])
                    if isinstance(raw_items, list):
                        for it in raw_items[:3]:
                            if isinstance(it, dict) and it.get("path"):
                                items.append({
                                    "path": it.get("path", ""),
                                    "label": it.get("label", ""),
                                    "core_path": it.get("core_path", ""),
                                    "core_name": it.get("core_name", "")
                                })
                    if items:
                        break
                elif content.startswith("["):
                    data = json.loads(content)
                    if isinstance(data, list):
                        for it in data[:3]:
                            if isinstance(it, dict) and it.get("path"):
                                items.append({
                                    "path": it.get("path", ""),
                                    "label": it.get("title") or it.get("label", ""),
                                    "core_path": it.get("core", ""),
                                    "core_name": ""
                                })
                    if items:
                        break
                else:
                    lines = content.splitlines()
                    for i in range(0, min(len(lines), 18), 6):
                        chunk = lines[i:i+6]
                        if len(chunk) >= 4 and chunk[0].strip():
                            items.append({
                                "path": chunk[0].strip(),
                                "label": chunk[1].strip() if len(chunk) > 1 else "",
                                "core_path": chunk[2].strip() if len(chunk) > 2 else "",
                                "core_name": chunk[3].strip() if len(chunk) > 3 else ""
                            })
                    if items:
                        break
        except Exception:
            pass

    if not items:
        return [
            "Khong tim thay lich su game vua chay (chua co content_history.lpl tren the).",
            "Goi y: Mo 1 game bat ky tren may roi quay lai day de thu thap nhat ky chinh xac."
        ]

    res = []
    for idx, it in enumerate(items):
        title = f"Game #{idx + 1}: {it.get('label') or os.path.basename(it.get('path', ''))}"
        res.append(title)
        res.append("-" * len(title))
        rom_path = it.get("path", "")
        res.append(f"  • File ROM         : {rom_path}")
        if os.path.isfile(rom_path):
            sz_b = os.path.getsize(rom_path)
            sz_mb = sz_b / (1024 * 1024)
            if sz_b == 0:
                sz_str = "0 Bytes [NGUY HIEM: FILE ROM BI RONG!]"
            elif sz_mb < 0.05:
                sz_str = f"{sz_b} Bytes [CANH BAO: FILE ROM RAT NHO DE BI LOI DUMP]"
            else:
                sz_str = f"{sz_mb:.2f} MB"
            res.append(f"  • Tinh trang ROM   : TON TAI ({sz_str})")
        else:
            res.append(f"  • Tinh trang ROM   : [CANH BAO: KHONG TIM THAY FILE TRUOC DO!]")

        core_path = it.get("core_path", "")
        core_name = it.get("core_name", "")
        res.append(f"  • Core su dung     : {core_name} ({core_path})")
        if core_path and os.path.isfile(core_path):
            c_sz_mb = os.path.getsize(core_path) / (1024 * 1024)
            res.append(f"  • Tinh trang Core  : TON TAI ({c_sz_mb:.2f} MB)")
        elif core_path:
            res.append(f"  • Tinh trang Core  : [CANH BAO: FILE CORE KHONG TON TAI!]")

        # Nhận diện hệ máy từ đường dẫn ROM (VD: /mnt/SDCARD/Roms/MAME/...)
        sys_code = ""
        parts = rom_path.replace("\\", "/").split("/")
        for p_idx, part in enumerate(parts):
            if part.lower() == "roms" and p_idx + 1 < len(parts):
                sys_code = parts[p_idx + 1]
                break

        if sys_code:
            res.append(f"  • He may nhan dien : {sys_code}")
            emu_dir = os.path.join(SDCARD_PATH, "Emus", sys_code)
            cfg_path = os.path.join(emu_dir, "config.json")
            launch_path = os.path.join(emu_dir, "launch.sh")

            if os.path.isfile(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f_cfg:
                        cfg_obj = json.load(f_cfg)
                        res.append(f"  • config.json      : launch={cfg_obj.get('launch')}, rompath={cfg_obj.get('rompath')}, extlist={cfg_obj.get('extlist')}")
                except Exception as e_cfg:
                    res.append(f"  • config.json      : Loi doc JSON ({e_cfg})")
            else:
                res.append(f"  • config.json      : Khong ton tai ({cfg_path})")

            if os.path.isfile(launch_path):
                try:
                    with open(launch_path, "r", encoding="utf-8", errors="ignore") as f_l:
                        l_lines = [line.strip() for line in f_l if line.strip() and not line.strip().startswith("#")]
                        res.append(f"  • launch.sh lenh   : {' | '.join(l_lines[:4])}")
                except Exception as e_l:
                    res.append(f"  • launch.sh        : Loi doc file ({e_l})")
            else:
                res.append(f"  • launch.sh        : Khong ton tai ({launch_path})")

        res.append("")
    return res


def _get_retroarch_logs_diagnostics(max_lines=100):
    """Thu thập dòng log gần nhất của RetroArch để phát hiện lỗi crash core hoặc load ROM."""
    candidates = [
        os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "logs", "retroarch.log"),
        os.path.join(SDCARD_PATH, "RetroArch", "retroarch.log"),
        os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "retroarch.log"),
        "/tmp/retroarch.log",
        "/tmp/log",
    ]
    target_file = None
    target_mtime = -1
    for c in candidates:
        if os.path.isfile(c):
            try:
                mt = os.path.getmtime(c)
                if mt > target_mtime:
                    target_mtime = mt
                    target_file = c
            except Exception:
                pass

    if not target_file:
        return [
            "Chua tim thay file nhat ky retroarch.log nao tren may.",
            "GOI Y: Vao Cai dat -> Bat 'Ghi nhat ky he thong' de RetroHub tu dong kich hoat ghi log chi tiet cho RetroArch khi mo game."
        ]

    try:
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        tail = [line.rstrip() for line in lines[-max_lines:]]
        errors = [l.strip() for l in lines if any(k in l.upper() for k in ("ERROR", "FAILED", "SEGMENTATION", "CRASH", "NOT FOUND", "CANNOT OPEN"))]

        header = [
            f"Tep log tim thay : {target_file} (Tong cong {len(lines)} dong)",
            f"Thoi diem sua doi: {datetime.fromtimestamp(target_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if errors:
            header.append(f"\n--- [CAC DONG CANH BAO / LOI TIM THAY TRONG LOG ({len(errors)})] ---")
            header.extend(errors[-20:])
            header.append("\n--- [CHI TIET CAC DONG CUOI CUNG CUA RETROARCH LOG] ---")
        else:
            header.append("\n--- [CHI TIET CAC DONG CUOI CUNG CUA RETROARCH LOG] ---")
        header.extend(tail)
        return header
    except Exception as e:
        return [f"Loi doc file {target_file}: {e}"]


def _get_dmesg_diagnostics(max_lines=60):
    """Trích xuất log kernel dmesg để phát hiện lỗi Out of Memory (OOM), Segfault, hoặc I/O."""
    try:
        import subprocess
        res = subprocess.run(["dmesg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode != 0 or not res.stdout:
            return ["dmesg khong kha dung tren thiet bi nay."]
        all_lines = res.stdout.strip().splitlines()
        tail = all_lines[-max_lines:]
        crashes = [
            l for l in all_lines
            if any(k in l.lower() for k in ("out of memory", "kill process", "killed process", "segfault", "sigsegv", "panic", "oom-killer", "buffer i/o error"))
        ]
        out = []
        if crashes:
            out.append(f"CANH BAO: Phat hien {len(crashes)} su co Kernel / Crash / OOM:")
            out.extend(crashes[-15:])
            out.append("")
        out.append(f"--- [DMESG TAIL ({len(tail)} dong)] ---")
        out.extend(tail)
        return out
    except Exception as e:
        return [f"Khong the trich xuat dmesg: {e}"]


def _get_retroarch_config_diagnostics():
    """Trích xuất các thông số cấu hình video và override của RetroArch."""
    ra_cfg = os.path.join(SDCARD_PATH, "RetroArch", "retroarch.cfg")
    res = []
    if not os.path.isfile(ra_cfg):
        return ["Khong tim thay RetroArch/retroarch.cfg"]

    target_keys = {
        "video_driver", "aspect_ratio_index", "video_aspect_ratio",
        "video_aspect_ratio_auto", "video_scale_integer", "video_threaded",
        "video_fullscreen", "log_to_file", "log_verbosity", "log_dir"
    }
    extracted = {}
    try:
        with open(ra_cfg, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_s = line.strip()
                for k in target_keys:
                    if line_s.startswith(f"{k} =") or line_s.startswith(f"{k}="):
                        val = line_s.split("=", 1)[1].strip().strip('"')
                        extracted[k] = val
        for k in sorted(target_keys):
            res.append(f"  • {k:<25}: {extracted.get(k, '[khong co]')}")
    except Exception as e:
        res.append(f"Loi doc retroarch.cfg: {e}")
    return res


def _get_installed_cores_diagnostics():
    """Liệt kê danh sách các core libretro đang cài đặt trên máy."""
    cores_dir = os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "cores")
    if not os.path.isdir(cores_dir):
        return [f"Khong tim thay thu muc cores ({cores_dir})"]
    try:
        cores = [f for f in os.listdir(cores_dir) if f.endswith("_libretro.so")]
        cores.sort()
        if not cores:
            return ["Thu muc cores rong (chua cai dat core libretro nao)."]
        lines = [f"Tong so core: {len(cores)} cores da cai dat"]
        for c in cores:
            c_path = os.path.join(cores_dir, c)
            sz_mb = os.path.getsize(c_path) / (1024 * 1024)
            lines.append(f"  • {c:<35} ({sz_mb:.1f} MB)")
        return lines
    except Exception as e:
        return [f"Loi doc danh sach cores: {e}"]


def _get_java_diagnostics(max_lines=100):
    """Trích xuất tình trạng giả lập Java J2ME và nhật ký chạy RetroHub-java.log."""
    res = []
    java_emu_dir = os.path.join(SDCARD_PATH, "Emus", "JAVA")
    zulu_bin = os.path.join(java_emu_dir, "zulu17", "bin")
    jar_file = os.path.join(zulu_bin, "freej2me-sdl.jar")
    sdl_iface = os.path.join(zulu_bin, "sdl_interface")
    gfx_cfg = os.path.join(zulu_bin, "graphics.cfg")
    key_cfg = os.path.join(zulu_bin, "keymap.cfg")

    # Kiểm tra runtime và file thực thi
    if os.path.isdir(java_emu_dir):
        j_ver = "Zulu OpenJDK 17" if os.path.isdir(os.path.join(java_emu_dir, "zulu17")) else "Khong ro"
        res.append(f"  • Thu muc Java J2ME: TON TAI ({java_emu_dir}) | Runtime: {j_ver}")

        if os.path.isfile(jar_file):
            sz_mb = os.path.getsize(jar_file) / (1024 * 1024)
            res.append(f"  • freej2me-sdl.jar : TON TAI ({sz_mb:.2f} MB)")
        else:
            res.append(f"  • freej2me-sdl.jar : [CANH BAO: THIEU FILE!]")

        if os.path.isfile(sdl_iface):
            can_exec = os.access(sdl_iface, os.X_OK)
            res.append(f"  • sdl_interface    : TON TAI (Quyen thuc thi: {'CO' if can_exec else 'KHONG - CAN CHMOD +X'})")
        else:
            res.append(f"  • sdl_interface    : [CANH BAO: THIEU FILE!]")

        if os.path.isfile(gfx_cfg):
            try:
                with open(gfx_cfg, "r", encoding="utf-8", errors="ignore") as f:
                    res.append(f"  • graphics.cfg     : {f.read().strip()}")
            except Exception:
                pass
        if os.path.isfile(key_cfg):
            try:
                with open(key_cfg, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                    res.append(f"  • keymap.cfg       : {first_line}")
            except Exception:
                pass
    else:
        res.append(f"  • Thu muc Java J2ME: CHUA CAI DAT ({java_emu_dir})")

    res.append("")

    # Đọc log file
    candidates = [
        os.path.join(SDCARD_PATH, "RetroHub-java.log"),
        "/tmp/RetroHub-java.log",
        os.path.join(zulu_bin, "log.txt"),
    ]
    log_path = None
    for c in candidates:
        if os.path.isfile(c):
            log_path = c
            break

    if not log_path:
        res.append("Chua co file nhat ky RetroHub-java.log (chua mo game Java nao tren thiet bi).")
        return res

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        mt = os.path.getmtime(log_path)
        res.append(f"Tep log tim thay : {log_path} (Tong cong {len(lines)} dong)")
        res.append(f"Thoi gian sua doi: {datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M:%S')}")

        errors = [l.strip() for l in lines if any(k in l for k in (
            "Exception", "Error", "Caused by", "OutOfMemory", "CRASH", "FATAL", "Failed", "ClassNotFound"
        ))]
        if errors:
            res.append(f"\n--- [CAC DONG NGOAI LE / LOI JAVA TIM THAY ({len(errors)})] ---")
            res.extend(errors[-20:])

        res.append(f"\n--- [CHI TIET {min(len(lines), max_lines)} DONG CUOI CUNG CUA LOG JAVA] ---")
        tail = [l.rstrip() for l in lines[-max_lines:]]
        res.extend(tail)
    except Exception as e:
        res.append(f"Loi doc file log Java {log_path}: {e}")

    return res


def generate_debug_report():
    """Tạo file báo cáo chẩn đoán tổng hợp toàn diện tại /mnt/SDCARD/RetroHub_Debug_Report.txt."""
    diag = get_system_diagnostics()
    logs = get_recent_logs(250)

    report_lines = [
        "==================================================================",
        "              RETROHUB SYSTEM DIAGNOSTIC REPORT                   ",
        "==================================================================",
        f"Ma thiet bi (ID)  : {diag.get('device_id') or get_device_id()}",
        f"Thoi gian tao     : {diag['timestamp']}",
        f"Phien ban App     : v{diag['app_version']}",
        f"Thiet bi / He OS  : {diag['device_model']}",
        f"Dia chi IP        : {diag['ip_address']}",
        f"Bo nho RAM        : {diag['ram_avail_mb']} MB trong / {diag['ram_total_mb']} MB tong",
        f"The nho SD Card   : {diag['sd_free_gb']} GB trong / {diag['sd_total_gb']} GB tong",
        f"Python Runtime    : {diag['python_version']} ({sys.executable})",
        f"Linux Kernel      : {diag['kernel']}",
        "",
        "==================================================================",
        "                 THONG TIN GAME VUA CHAY GAN NHAT                 ",
        "==================================================================",
        ""
    ]
    report_lines.extend(_get_recent_game_diagnostics())
    report_lines.extend([
        "==================================================================",
        "               NHAT KY THUC THI RETROARCH (RUNTIME LOG)           ",
        "==================================================================",
        ""
    ])
    report_lines.extend(_get_retroarch_logs_diagnostics())
    report_lines.extend([
        "",
        "==================================================================",
        "               NHAT KY GIA LAP JAVA J2ME (FREEJ2ME LOG)           ",
        "==================================================================",
        ""
    ])
    report_lines.extend(_get_java_diagnostics())
    report_lines.extend([
        "",
        "==================================================================",
        "               NHAT KY KERNEL & DMESG CRASH DUMP                  ",
        "==================================================================",
        ""
    ])
    report_lines.extend(_get_dmesg_diagnostics())
    report_lines.extend([
        "",
        "==================================================================",
        "              THIET LAP HIEN THI & VIDEO RETROARCH                ",
        "==================================================================",
        ""
    ])
    report_lines.extend(_get_retroarch_config_diagnostics())
    report_lines.extend([
        "",
        "==================================================================",
        "              DANH SACH CORE LIBRETRO DA CAI DAT                  ",
        "==================================================================",
        ""
    ])
    report_lines.extend(_get_installed_cores_diagnostics())
    report_lines.extend([
        "",
        "==================================================================",
        "                       NHAT KY LOG RETROHUB                       ",
        "==================================================================",
        ""
    ])
    report_lines.extend(logs)
    report_lines.append("\n[Het noi dung bao cao]")

    content = "\n".join(report_lines)
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return True, REPORT_FILE
    except Exception as e:
        fallback = "/tmp/RetroHub_Debug_Report.txt"
        try:
            with open(fallback, "w", encoding="utf-8") as f:
                f.write(content)
            return True, fallback
        except Exception as e2:
            return False, f"Loi ghi report: {str(e2)}"


def upload_log_to_telegram(note=""):
    """Gửi tệp báo cáo chẩn đoán trực tiếp vào Telegram Bot của tác giả.
    
    Returns: (bool_success, result_message)
    """
    ok, path_or_err = generate_debug_report()
    if not ok:
        return False, f"Không tạo được báo cáo: {path_or_err}"

    report_path = path_or_err
    try:
        with open(report_path, "rb") as f:
            content_bytes = f.read()
    except Exception as e:
        return False, f"Không đọc được tệp báo cáo: {str(e)}"

    diag = get_system_diagnostics()
    dev_id = diag.get("device_id") or get_device_id()
    timestamp_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    device_tag = "TrimUI"
    if "NextUI" in diag["device_model"]:
        device_tag = "TrimUI_NextUI"
    elif "CrossMix" in diag["device_model"]:
        device_tag = "TrimUI_CrossMix"

    filename = f"RetroHub_Log_{dev_id}_{device_tag}_{timestamp_tag}.txt"

    caption_lines = [
        "*[Báo cáo lỗi từ RetroHub]*",
        f"*Mã máy:* `{dev_id}`",
        f"*Thiết bị:* {diag['device_model']}",
        f"*Phiên bản:* v{diag['app_version']}",
        f"*IP:* `{diag['ip_address']}`",
        f"*RAM trống:* {diag['ram_avail_mb']} MB / {diag['ram_total_mb']} MB",
        f"*Thời gian:* {diag['timestamp']}",
    ]
    if note:
        caption_lines.append(f"*Ghi chú:* {note}")

    caption = "\n".join(caption_lines)

    # Gửi qua Telegram API bằng Multipart Form Data thuần stdlib
    boundary = uuid.uuid4().hex
    body = bytearray()

    # chat_id
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body.extend(f"{TELEGRAM_CHAT_ID}\r\n".encode("utf-8"))

    # caption
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
    body.extend(caption.encode("utf-8") + b"\r\n")

    # parse_mode
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\n')
    body.extend(b"Markdown\r\n")

    # document file
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: text/plain; charset=utf-8\r\n\r\n")
    body.extend(content_bytes)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": f"RetroHub-Handheld/{diag['app_version']}"
        }
    )

    try:
        urlopen_kw = {"timeout": 25}
        if _SSL_CONTEXT is not None:
            urlopen_kw["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **urlopen_kw) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            if resp_data.get("ok"):
                log_info(f"Gui bao cao loi len Telegram thanh cong: {filename}")
                return True, "Đã gửi báo cáo lỗi thành công tới tác giả qua Telegram!"
            else:
                err_desc = resp_data.get("description", "Lỗi không xác định từ Telegram")
                log_error(f"Loi Telegram API: {err_desc}")
                return False, f"Telegram từ chối: {err_desc}"
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", str(e))
        log_error(f"Loi ket noi khi gui Telegram: {reason}")
        return False, f"Lỗi kết nối: {reason}"
    except Exception as e:
        log_error(f"Loi ngoai le khi gui Telegram: {str(e)}")
        return False, f"Lỗi gửi báo cáo: {str(e)}"
