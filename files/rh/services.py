# -*- coding: utf-8 -*-
"""On-device services the user can toggle: SFTPGo, SSH, ADB, MTP, screen streamer."""

import os
import sys
import time
import subprocess
import shutil

from .paths import EX_OPTIONS_FILE, STREAMER_SCRIPT, GAMEWEB_SCRIPT
from . import state
from .sysinfo import (get_ip, is_sftpgo_running, is_ssh_running,
                      is_adb_running, is_mtp_running, is_streamer_running,
                      is_gameweb_running, is_remote_tunnel_running)

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

# The streamer shells out to ffmpeg to encode frames. Without it the feature
# cannot work at all, so it is hidden rather than offered and then failing.
FFMPEG = "/usr/bin/ffmpeg"


def stream_supported():
    return os.path.exists(FFMPEG)


def toggle_streamer():
    if is_streamer_running():
        subprocess.call("pkill -9 -f streamer.py 2>/dev/null; killall -9 ffmpeg 2>/dev/null", shell=True)
        return "Đã tắt Stream màn hình" if state.current_lang == "VI" else "Disabled Screen Streamer"
    else:
        # sys.executable, not a fixed path: /mnt/SDCARD/System/bin/python3 does
        # not exist on the Brick Pro, where the interpreter is the one bundled
        # with the app. Whatever is running this process can run the streamer.
        subprocess.Popen([sys.executable, STREAMER_SCRIPT], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        ip = get_ip()
        return f"Đã bật Stream (Web: http://{ip}:8088)" if state.current_lang == "VI" else f"Enabled Stream (Web: http://{ip}:8088)"

def toggle_gameweb():
    if is_gameweb_running():
        subprocess.call("pkill -9 -f gameweb.py 2>/dev/null", shell=True)
        return "Đã tắt Quản lý Game Web" if state.current_lang == "VI" else "Disabled Web Game Manager"
    else:
        subprocess.Popen([sys.executable, GAMEWEB_SCRIPT], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        ip = get_ip()
        return f"Đã bật Quản lý Game (Web: http://{ip}:8090)" if state.current_lang == "VI" else f"Enabled Web Game Manager (http://{ip}:8090)"

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

def get_gameweb_guide_rows():
    ip = get_ip()
    vi = state.current_lang == "VI"
    return [
        ("Mở trên máy tính / điện thoại" if vi else "Open in desktop / mobile browser",
         f"http://{ip}:8090"),
        ("Chức năng Web" if vi else "Web Features",
         "Đổi tên game, Cào ảnh bìa (Art), Chuyển hệ máy, Tải ROM" if vi
         else "Rename games, Scrape boxart, Move systems, Upload ROMs"),
        ("Tương thích" if vi else "Compatibility",
         "Chrome, Safari, Edge, Cốc Cốc trên cùng mạng Wi-Fi" if vi
         else "Any modern browser on same Wi-Fi network"),
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

REMOTE_SSH_INFO_FILE = "/tmp/remote_ssh.json"
REMOTE_SSH_PID_FILE = "/tmp/remote_ssh.pid"
REMOTE_SSH_LOG_FILE = "/tmp/remote_ssh.log"

def get_remote_tunnel_info():
    if not is_remote_tunnel_running():
        return None
    if os.path.exists(REMOTE_SSH_INFO_FILE):
        try:
            import json
            with open(REMOTE_SSH_INFO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def stop_remote_tunnel():
    if os.path.exists(REMOTE_SSH_PID_FILE):
        try:
            with open(REMOTE_SSH_PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 9)
        except Exception:
            pass
        try:
            os.remove(REMOTE_SSH_PID_FILE)
        except Exception:
            pass
    subprocess.call("pkill -9 -f 'tcp@a.pinggy.io' 2>/dev/null; pkill -9 -f 'a.pinggy.io' 2>/dev/null", shell=True)
    if os.path.exists(REMOTE_SSH_INFO_FILE):
        try:
            os.remove(REMOTE_SSH_INFO_FILE)
        except Exception:
            pass
    if os.path.exists(REMOTE_SSH_LOG_FILE):
        try:
            os.remove(REMOTE_SSH_LOG_FILE)
        except Exception:
            pass
    return ("Đã tắt SSH Internet" if state.current_lang == "VI"
            else "Disabled Remote SSH Internet")

def find_ssh_client():
    """Find a usable SSH client (OpenSSH ssh or Dropbear dbclient) and build command."""
    # 1. Check for OpenSSH client
    ssh_candidates = [
        shutil.which("ssh"),
        "/usr/bin/ssh",
        "/usr/local/bin/ssh",
        "/mnt/SDCARD/System/bin/ssh"
    ]
    for p in ssh_candidates:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return [
                p,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
                "-p", "443",
                "-R0:localhost:22",
                "tcp@a.pinggy.io"
            ]

    # 2. Check for Dropbear client (dbclient)
    db_candidates = [
        shutil.which("dbclient"),
        "/mnt/SDCARD/System/bin/dbclient",
        "/usr/bin/dbclient"
    ]
    db_bin = None
    for p in db_candidates:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            db_bin = p
            break

    if db_bin:
        key_candidates = [
            "/etc/dropbear/dropbear_ed25519_host_key",
            "/etc/dropbear/dropbear_rsa_host_key",
            "/root/.ssh/id_dropbear",
            os.path.expanduser("~/.ssh/id_dropbear")
        ]
        key_file = None
        for k in key_candidates:
            if os.path.isfile(k):
                key_file = k
                break

        cmd = [
            db_bin,
            "-T",
            "-y", "-y",
            "-K", "30",
            "-p", "443",
            "-R", "0:localhost:22"
        ]
        if key_file:
            cmd.extend(["-i", key_file])
        cmd.append("tcp@a.pinggy.io")
        return cmd

    return None

def start_remote_tunnel():
    ip = get_ip()
    if not ip or ip.startswith("Chưa") or ip.startswith("Not"):
        return ("Cần kết nối Wi-Fi trước khi mở SSH Internet!" if state.current_lang == "VI"
                else "Wi-Fi connection required for Remote SSH!")

    if not is_ssh_running():
        toggle_ssh()
        time.sleep(0.5)
        if not is_ssh_running():
            return ("Không thể bật SSH Server nội bộ (cổng 22)!" if state.current_lang == "VI"
                    else "Failed to start local SSH Server (port 22)!")

    stop_remote_tunnel()
    time.sleep(0.3)

    cmd = find_ssh_client()
    if not cmd:
        return ("Không tìm thấy SSH client (ssh hoặc dbclient) trên máy!" if state.current_lang == "VI"
                else "No SSH client (ssh or dbclient) found on device!")

    try:
        log_f = open(REMOTE_SSH_LOG_FILE, "w")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True
        )
    except Exception as e:
        return (f"Lỗi khởi động SSH client: {e}" if state.current_lang == "VI"
                else f"Failed to execute ssh client: {e}")

    import re
    import json
    endpoint_host = None
    endpoint_port = None
    start_t = time.time()

    while time.time() - start_t < 6.5:
        if proc.poll() is not None:
            break
        if os.path.exists(REMOTE_SSH_LOG_FILE):
            try:
                with open(REMOTE_SSH_LOG_FILE, "r", errors="ignore") as f:
                    content = f.read()
                m = re.search(r"tcp://([a-zA-Z0-9.\-_]+):(\d+)", content)
                if m:
                    endpoint_host = m.group(1)
                    endpoint_port = m.group(2)
                    break
            except Exception:
                pass
        time.sleep(0.25)

    if not endpoint_host or not endpoint_port:
        stop_remote_tunnel()
        return ("Không nhận được địa chỉ từ Pinggy! Thử lại sau." if state.current_lang == "VI"
                else "Failed to obtain tunnel address from Pinggy!")

    try:
        with open(REMOTE_SSH_PID_FILE, "w") as f:
            f.write(str(proc.pid))
    except Exception:
        pass

    info = {
        "host": endpoint_host,
        "port": endpoint_port,
        "cmd": f"ssh -p {endpoint_port} root@{endpoint_host}",
        "scp": f"scp -P {endpoint_port} root@{endpoint_host}:/mnt/SDCARD/... ./",
        "started_at": time.time(),
        "created_str": time.strftime("%H:%M:%S")
    }
    try:
        with open(REMOTE_SSH_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f)
    except Exception:
        pass

    return (f"Đã mở SSH Internet: cổng {endpoint_port}" if state.current_lang == "VI"
            else f"Remote SSH active: port {endpoint_port}")

def toggle_remote_tunnel():
    if is_remote_tunnel_running():
        return stop_remote_tunnel()
    else:
        return start_remote_tunnel()

def get_remote_tunnel_guide_rows():
    info = get_remote_tunnel_info()
    vi = state.current_lang == "VI"
    if not info:
        return [
            ("Trạng thái" if vi else "Status", "Chưa kích hoạt" if vi else "Not active"),
            ("Bật tính năng" if vi else "To activate",
             "Bật công tắc SSH Internet trong menu" if vi else "Toggle Remote SSH ON in menu")
        ]
    host = info.get("host", "N/A")
    port = info.get("port", "N/A")
    return [
        ("Lệnh SSH từ xa" if vi else "Remote SSH Command", f"ssh -p {port} root@{host}"),
        ("Mật khẩu" if vi else "Password", "root"),
        ("Chép file (SCP)" if vi else "File transfer (SCP)", f"scp -P {port} root@{host}:/mnt/SDCARD/... ./"),
        ("Thời hạn phiên" if vi else "Session duration", "60 phút (tự tạo phiên mới khi bật lại)" if vi else "60 mins (auto refreshes on restart)"),
        ("Mạng hỗ trợ" if vi else "Supported networks", "Mọi mạng (4G, Wi-Fi khác, bypass NAT)" if vi else "All networks (4G, separate Wi-Fi, NAT bypass)")
    ]

