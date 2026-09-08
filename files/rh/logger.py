# -*- coding: utf-8 -*-
"""Diagnostic & Debug Logging System for RetroHub on TrimUI handhelds:
Captures hardware specs, network status, crash stack traces, rotating log files,
and uploads diagnostic bundles directly to Telegram Bot.
"""

import os
import sys
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
        if not getattr(state, "enable_logging", True):
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

    diag = get_system_diagnostics()
    log_info("=" * 60)
    log_info(f"RetroHub v{diag['app_version']} khoi dong tren {diag['device_model']}")
    log_info(f"Python: {diag['python_version']} | Kernel: {diag['kernel']}")
    log_info(f"RAM: {diag['ram_avail_mb']}/{diag['ram_total_mb']} MB kha dung | The nho: {diag['sd_free_gb']}/{diag['sd_total_gb']} GB")
    log_info(f"Dia chi IP: {diag['ip_address']}")
    log_info("=" * 60)


def generate_debug_report():
    """Tạo file báo cáo chẩn đoán tổng hợp tại /mnt/SDCARD/RetroHub_Debug_Report.txt."""
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
        "==================================================================",
        "                       NHAT KY LOG HE THONG                       ",
        "==================================================================",
        ""
    ]
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
        "🚨 *[Báo cáo lỗi từ RetroHub]*",
        f"🆔 *Mã máy:* `{dev_id}`",
        f"📱 *Thiết bị:* {diag['device_model']}",
        f"📦 *Phiên bản:* v{diag['app_version']}",
        f"🌐 *IP:* `{diag['ip_address']}`",
        f"💾 *RAM trống:* {diag['ram_avail_mb']} MB / {diag['ram_total_mb']} MB",
        f"🕒 *Thời gian:* {diag['timestamp']}",
    ]
    if note:
        caption_lines.append(f"💬 *Ghi chú:* {note}")

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
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            if resp_data.get("ok"):
                log_info(f"Gui bao cao loi len Telegram thanh cong: {filename}")
                return True, "Đã gửi báo cáo lỗi thành công tới tác giả qua Telegram!"
            else:
                err_desc = resp_data.get("description", "Lỗi không xác định từ Telegram")
                log_error(f"Loi Telegram API: {err_desc}")
                return False, f"Telegram từ chối: {err_desc}"
    except urllib.error.URLError as e:
        log_error(f"Loi ket noi khi gui Telegram: {str(e)}")
        return False, "Không thể kết nối Internet! Vui lòng kiểm tra Wi-Fi trên máy."
    except Exception as e:
        log_error(f"Loi ngoai le khi gui Telegram: {str(e)}")
        return False, f"Lỗi gửi báo cáo: {str(e)}"
