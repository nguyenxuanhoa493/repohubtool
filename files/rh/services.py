# -*- coding: utf-8 -*-
"""On-device services the user can toggle: SFTPGo, SSH, ADB, MTP, screen streamer."""

import os
import time
import subprocess

from .paths import EX_OPTIONS_FILE, STREAMER_SCRIPT
from . import state
from .sysinfo import (get_ip, is_sftpgo_running, is_ssh_running,
                      is_adb_running, is_mtp_running, is_streamer_running)

def save_options(sftpgo_val=None, ssh_val=None, adb_val=None, mtp_val=None):
    cur_sftp = sftpgo_val if sftpgo_val is not None else ("Y" if is_sftpgo_running() else "N")
    cur_ssh = ssh_val if ssh_val is not None else ("Y" if is_ssh_running() else "N")
    cur_adb = adb_val if adb_val is not None else ("Y" if is_adb_running() else "N")
    cur_mtp = mtp_val if mtp_val is not None else ("Y" if is_mtp_running() else "N")
    try:
        os.makedirs(os.path.dirname(EX_OPTIONS_FILE), exist_ok=True)
        with open(EX_OPTIONS_FILE, "w", encoding="utf-8") as f:
            f.write(f'export NETWORK_FIX="Y"\nexport NETWORK_SSH="{cur_ssh}"\nexport NETWORK_SFTPGO="{cur_sftp}"\nexport USB_ADB="{cur_adb}"\nexport USB_MTP="{cur_mtp}"\n')
    except Exception as e:
        print(f"Error saving options: {e}")

def toggle_sftpgo():
    if is_sftpgo_running():
        subprocess.call("killall -9 sftpgo 2>/dev/null", shell=True)
        time.sleep(0.4)
        if not is_sftpgo_running():
            save_options(sftpgo_val="N")
            return "Đã tắt SFTPGo (Giải phóng RAM)" if state.current_lang == "VI" else "Disabled SFTPGo (Freed RAM)"
        else:
            return "Không thể dừng SFTPGo!" if state.current_lang == "VI" else "Failed to stop SFTPGo!"
    else:
        subprocess.call("mkdir -p /opt/sftpgo && /mnt/SDCARD/System/sftpgo/sftpgo serve -c /mnt/SDCARD/System/sftpgo/ >/dev/null 2>&1 &", shell=True)
        time.sleep(0.8)
        if is_sftpgo_running():
            save_options(sftpgo_val="Y")
            ip = get_ip()
            return f"Đã bật SFTPGo (Web: http://{ip}:8080 | Port: 2022)" if state.current_lang == "VI" else f"Enabled SFTPGo (Web: http://{ip}:8080 | Port: 2022)"
        else:
            save_options(sftpgo_val="N")
            return "Không thể khởi động SFTPGo! Kiểm tra tệp thực thi." if state.current_lang == "VI" else "Failed to start SFTPGo! Check binary."

def toggle_ssh():
    if is_ssh_running():
        subprocess.call("/etc/init.d/sshd stop 2>/dev/null; /etc/init.d/dropbear stop 2>/dev/null; killall -9 sshd 2>/dev/null; killall -9 dropbear 2>/dev/null", shell=True)
        time.sleep(0.4)
        if not is_ssh_running():
            save_options(ssh_val="N")
            return "Đã tắt SSH Server (Cổng 22)" if state.current_lang == "VI" else "Disabled SSH Server (Port 22)"
        else:
            return "Không thể dừng SSH Server!" if state.current_lang == "VI" else "Failed to stop SSH Server!"
    else:
        subprocess.call("/etc/init.d/sshd start 2>/dev/null || /usr/sbin/sshd -D &", shell=True)
        subprocess.call("/etc/init.d/dropbear start 2>/dev/null || dropbear -R -B &", shell=True)
        time.sleep(0.5)
        if is_ssh_running():
            save_options(ssh_val="Y")
            ip = get_ip()
            return f"Đã bật SSH Server (Host: {ip} | Port: 22)" if state.current_lang == "VI" else f"Enabled SSH Server (Host: {ip} | Port: 22)"
        else:
            save_options(ssh_val="N")
            return "Không thể khởi động SSH Server!" if state.current_lang == "VI" else "Failed to start SSH Server!"

def toggle_adb():
    if is_adb_running():
        subprocess.call("/etc/init.d/adbd stop >/dev/null 2>&1; /etc/init.d/adbd disable >/dev/null 2>&1; killall -9 adbd >/dev/null 2>&1", shell=True)
        save_options(adb_val="N")
        return "Đã tắt USB ADB Debug (Đóng cổng 5037)" if state.current_lang == "VI" else "Disabled USB ADB Debug (Closed port 5037)"
    else:
        subprocess.call("/etc/init.d/adbd enable >/dev/null 2>&1; /etc/init.d/adbd start >/dev/null 2>&1 &", shell=True)
        save_options(adb_val="Y")
        return "Đã bật USB ADB Debug (Mở cổng 5037)" if state.current_lang == "VI" else "Enabled USB ADB Debug (Opened port 5037)"

def toggle_mtp():
    if is_mtp_running():
        subprocess.call("/etc/init.d/mtp stop >/dev/null 2>&1; /etc/init.d/mtp disable >/dev/null 2>&1; killall -9 MtpDaemon >/dev/null 2>&1", shell=True)
        save_options(mtp_val="N")
        return "Đã tắt USB MTP Transfer" if state.current_lang == "VI" else "Disabled USB MTP Transfer"
    else:
        subprocess.call("/etc/init.d/mtp enable >/dev/null 2>&1; /etc/init.d/mtp start >/dev/null 2>&1 &", shell=True)
        save_options(mtp_val="Y")
        return "Đã bật USB MTP Transfer" if state.current_lang == "VI" else "Enabled USB MTP Transfer"

def toggle_streamer():
    if is_streamer_running():
        subprocess.call("pkill -9 -f streamer.py 2>/dev/null; killall -9 ffmpeg 2>/dev/null", shell=True)
        return "Đã tắt Stream màn hình" if state.current_lang == "VI" else "Disabled Screen Streamer"
    else:
        subprocess.Popen(["/mnt/SDCARD/System/bin/python3", STREAMER_SCRIPT], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        ip = get_ip()
        return f"Đã bật Stream (Web: http://{ip}:8088)" if state.current_lang == "VI" else f"Enabled Stream (Web: http://{ip}:8088)"

def wifi_iface():
    """Interface holding the default route, e.g. wlan0."""
    try:
        out = subprocess.check_output(
            "ip route 2>/dev/null | awk '/default/{print $5; exit}'",
            shell=True).decode("utf-8", "ignore").strip()
        return out or "wlan0"
    except Exception:
        return "wlan0"

def is_wifi_awake():
    """True when Wi-Fi power save is OFF, i.e. the radio stays up between packets.

    Reported as "awake" rather than as the raw power_save value so the toggle reads
    the same way as every other service here: on means more capability, more battery.
    """
    try:
        out = subprocess.check_output(
            "iw dev %s get power_save 2>/dev/null" % wifi_iface(),
            shell=True).decode("utf-8", "ignore").lower()
        return "power save: off" in out
    except Exception:
        return False

def apply_wifi_awake(awake):
    """Set the radio's power save state. Returns True if the change took effect."""
    target = "off" if awake else "on"
    subprocess.call("iw dev %s set power_save %s 2>/dev/null" % (wifi_iface(), target),
                    shell=True)
    return is_wifi_awake() == bool(awake)

def toggle_wifi_awake():
    want = not is_wifi_awake()
    ok = apply_wifi_awake(want)
    state.wifi_awake = is_wifi_awake()
    state.save_settings()
    if not ok:
        return ("Không đổi được chế độ WiFi (thiếu lệnh iw?)"
                if state.current_lang == "VI" else
                "Could not change Wi-Fi mode (is iw available?)")
    if state.wifi_awake:
        return ("Đã giữ WiFi luôn thức — kết nối ổn định, hao pin hơn"
                if state.current_lang == "VI" else
                "Wi-Fi kept awake - stable connection, more battery use")
    return ("Đã bật tiết kiệm pin WiFi — có thể rớt kết nối khi nhàn rỗi"
            if state.current_lang == "VI" else
            "Wi-Fi power save on - idle connections may drop")

def get_stream_guide_rows():
    """The address to type, then the two things worth knowing.

    This used to list five rows of capabilities. Standing in front of the
    handheld with a browser open, only the address matters - the rest was read
    once and never again, and it pushed the address down into small print.
    """
    ip = get_ip()
    vi = state.current_lang == "VI"
    return [
        ("Mở trên trình duyệt máy tính" if vi else "Open in a desktop browser",
         f"http://{ip}:8088"),
        ("Cho OBS / VLC" if vi else "For OBS / VLC", f"http://{ip}:8088/stream.mjpg"),
        ("Trên web có" if vi else "On the page",
         "Quay video, chụp ảnh, đổi tỉ lệ 4:3 / 16:9" if vi
         else "Record, screenshot, 4:3 / 16:9 switch"),
    ]

def get_sftp_guide_rows():
    """Web address first, then what an SFTP client needs.

    Trimmed the same way as the stream guide: the address is the reason the
    screen is open, so it gets the headline row and the feature blurb goes."""
    ip = get_ip()
    vi = state.current_lang == "VI"
    return [
        ("Mở trên trình duyệt máy tính" if vi else "Open in a desktop browser",
         f"http://{ip}:8080"),
        ("Phần mềm SFTP (WinSCP, FileZilla)" if vi else "SFTP client (WinSCP, FileZilla)",
         f"{ip}  ·  cổng 2022" if vi else f"{ip}  ·  port 2022"),
        ("Đăng nhập" if vi else "Login", "trimui / trimui"),
    ]

def get_ssh_guide_rows():
    """The command to paste, then the password.

    Port 22 and the list of SSH clients were two of four rows and told nobody
    anything they could act on - the command already carries the port."""
    ip = get_ip()
    vi = state.current_lang == "VI"
    return [
        ("Dán vào Terminal / PowerShell" if vi else "Paste into Terminal / PowerShell",
         f"ssh root@{ip}"),
        ("Mật khẩu" if vi else "Password", "root"),
    ]
