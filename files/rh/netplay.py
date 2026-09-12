# -*- coding: utf-8 -*-
"""Internet Netplay over Pinggy reverse tunnel for 2-player multiplayer on RetroArch."""

import os
import sys
import time
import subprocess
import json
import threading
import re

from . import state
from .paths import SDCARD_PATH
from .sysinfo import get_ip, is_proc_running
from .services import find_ssh_client

NETPLAY_PORT = 55435
NETPLAY_PID_FILE = "/tmp/netplay_tunnel.pid"
NETPLAY_INFO_FILE = "/tmp/netplay_info.json"
NETPLAY_LOG_FILE = "/tmp/netplay_tunnel.log"

TELEGRAM_BOT_TOKEN = "8843439406:AAEtTnuMk68ilAniAxj8Kl3uTKZmVKEVDDs"
TELEGRAM_CHAT_ID = "663642384"

def is_netplay_tunnel_running():
    if os.path.exists(NETPLAY_PID_FILE):
        try:
            with open(NETPLAY_PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except Exception:
            pass
    return False

def get_netplay_tunnel_info():
    if not is_netplay_tunnel_running():
        return None
    if os.path.exists(NETPLAY_INFO_FILE):
        try:
            with open(NETPLAY_INFO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def stop_netplay_tunnel():
    if os.path.exists(NETPLAY_PID_FILE):
        try:
            with open(NETPLAY_PID_FILE, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, 9)
        except Exception:
            pass
        try:
            os.remove(NETPLAY_PID_FILE)
        except Exception:
            pass
    try:
        subprocess.call("pkill -9 -f '0:localhost:55435' 2>/dev/null", shell=True)
    except Exception:
        pass
    try:
        if os.path.exists(NETPLAY_INFO_FILE):
            os.remove(NETPLAY_INFO_FILE)
    except Exception:
        pass
    return "Đã đóng phòng Netplay" if state.current_lang == "VI" else "Netplay room closed"

def start_netplay_tunnel(game_title="Game", sys_code="NES"):
    """Launch Pinggy TCP reverse tunnel forwarding port 55435."""
    ip = get_ip()
    vi = state.current_lang == "VI"
    if not ip or ip.startswith("Chưa") or ip.startswith("Not"):
        return False, ("Cần kết nối Wi-Fi trước khi mở phòng Netplay!" if vi
                       else "Wi-Fi connection required for Netplay!")

    stop_netplay_tunnel()
    time.sleep(0.3)

    cmd = find_ssh_client()
    if not cmd:
        return False, ("Không tìm thấy SSH client trên máy!" if vi
                       else "No SSH client found on device!")

    # Replace local port forwarding with Netplay port 55435
    netplay_cmd = []
    for arg in cmd:
        if arg.startswith("0:localhost:"):
            netplay_cmd.append(f"0:localhost:{NETPLAY_PORT}")
        else:
            netplay_cmd.append(arg)

    try:
        log_f = open(NETPLAY_LOG_FILE, "w")
        proc = subprocess.Popen(
            netplay_cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True
        )
    except Exception as e:
        return False, f"Lỗi khởi động: {e}" if vi else f"Start error: {e}"

    endpoint_host = None
    endpoint_port = None
    start_t = time.time()

    while time.time() - start_t < 7.0:
        if proc.poll() is not None:
            break
        if os.path.exists(NETPLAY_LOG_FILE):
            try:
                with open(NETPLAY_LOG_FILE, "r", errors="ignore") as f:
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
        stop_netplay_tunnel()
        return False, ("Không nhận được địa chỉ phòng từ Pinggy!" if vi
                       else "Failed to obtain Netplay room from Pinggy!")

    try:
        with open(NETPLAY_PID_FILE, "w") as f:
            f.write(str(proc.pid))
    except Exception:
        pass

    info = {
        "host": endpoint_host,
        "port": endpoint_port,
        "game_title": game_title,
        "sys_code": sys_code,
        "started_at": time.time(),
        "created_str": time.strftime("%H:%M:%S")
    }
    try:
        with open(NETPLAY_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f)
    except Exception:
        pass

    # Send room details to Telegram in background thread
    try:
        threading.Thread(target=send_netplay_info_to_telegram,
                         args=(game_title, sys_code, endpoint_host, endpoint_port),
                         daemon=True).start()
    except Exception:
        pass

    return True, info

def send_netplay_info_to_telegram(game_title=None, sys_code=None, host=None, port=None):
    """Send Netplay room invitation with port and game name to Telegram."""
    if not host or not port:
        info = get_netplay_tunnel_info()
        if not info:
            return False, "Chưa có phòng Netplay nào đang mở!"
        host = info.get("host")
        port = info.get("port")
        game_title = game_title or info.get("game_title", "Retro Game")
        sys_code = sys_code or info.get("sys_code", "")

    try:
        from .logger import get_device_id
        dev_id = get_device_id()
    except Exception:
        dev_id = "N/A"

    from .sysinfo import detect_device_platform
    dev_model = detect_device_platform()

    msg_lines = [
        "🎮 *[RetroHub] Lời mời chơi Netplay qua Internet*",
        f"🕹️ *Tựa game:* {game_title} `[{sys_code}]`",
        f"📱 *Máy chủ (Host):* {dev_model} (`{dev_id}`)",
        "",
        "🔑 *MÃ PHÒNG (PORT):*",
        f"`{port}`",
        "",
        "🌐 *Địa chỉ kết nối đầy đủ:*",
        f"`{host}:{port}`",
        "",
        "👉 *Cách vào chơi (Player 2):*",
        f"Mở RetroHub ➔ chọn cùng game `{game_title}` ➔ chọn *Netplay* ➔ chọn *[Vào phòng]* và nhập mã: `{port}`!"
    ]
    text = "\n".join(msg_lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        import urllib.request
        import ssl
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "RetroHub-Handheld"
            }
        )
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        except Exception:
            ctx = None

        kw = {"timeout": 10}
        if ctx:
            kw["context"] = ctx

        with urllib.request.urlopen(req, **kw) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                return True, "Đã gửi mã phòng Netplay vào Telegram!"
            else:
                return False, res_data.get("description", "Lỗi Telegram")
    except Exception as e:
        return False, f"Lỗi gửi Telegram: {e}"

def build_netplay_param(mode="host", host="a.pinggy.io", port=55435, nick="Player"):
    """Generate NET_PARAM string for RetroArch CLI."""
    if mode == "host":
        return f"-H --port {NETPLAY_PORT} --nick {nick}"
    else:
        return f"-C {host} --port {port} --nick {nick}"
