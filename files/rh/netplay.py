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
TELEGRAM_GROUP_CHAT_ID = "-1003890413445"
TELEGRAM_CHAT_ID_CACHE = "/tmp/netplay_tele_chat_id.txt"

def resolve_netplay_telegram_chat_id():
    """Tự động kiểm tra getUpdates xem nhóm nào có chat 'test_nhóm' hoặc 'test_nhom' để lấy chat_id.
    Nếu có lưu cache thì đọc cache, nếu không mặc định gửi vào nhóm RetroHub (-1003890413445).
    """
    try:
        import urllib.request, ssl
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?limit=50"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "RetroHub-Handheld"})
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for u in reversed(data.get("result", [])):
                msg = u.get("message") or u.get("channel_post") or {}
                txt = (msg.get("text") or "").strip().lower()
                if "test_nhóm" in txt or "test_nhom" in txt:
                    cid = str(msg.get("chat", {}).get("id"))
                    if cid:
                        try:
                            with open(TELEGRAM_CHAT_ID_CACHE, "w") as cf:
                                cf.write(cid)
                        except Exception:
                            pass
                        return cid
    except Exception:
        pass

    if os.path.exists(TELEGRAM_CHAT_ID_CACHE):
        try:
            with open(TELEGRAM_CHAT_ID_CACHE, "r") as cf:
                cid = cf.read().strip()
                if cid:
                    return cid
        except Exception:
            pass

    return TELEGRAM_GROUP_CHAT_ID

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
    old_port = None
    if os.path.exists(NETPLAY_INFO_FILE):
        try:
            with open(NETPLAY_INFO_FILE, "r", encoding="utf-8") as f:
                old_info = json.load(f)
                old_port = old_info.get("port")
        except Exception:
            pass

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
        subprocess.call("pkill -9 -f 'localhost:55435' 2>/dev/null", shell=True)
    except Exception:
        pass
    try:
        if os.path.exists(NETPLAY_INFO_FILE):
            os.remove(NETPLAY_INFO_FILE)
    except Exception:
        pass

    if old_port:
        try:
            from .lobby import delete_room
            threading.Thread(target=delete_room, args=(old_port,), daemon=True).start()
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

    # Replace local port forwarding with Netplay port 55435 (supports OpenSSH -R0:localhost:22 and Dropbear 0:localhost:22)
    netplay_cmd = []
    for arg in cmd:
        if "0:localhost:" in arg:
            prefix = arg.split("0:localhost:")[0]
            netplay_cmd.append(f"{prefix}0:localhost:{NETPLAY_PORT}")
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

    # Publish room to public lobby API in background thread
    try:
        from .lobby import publish_room
        from .emulators import resolve_core_name
        from .sysinfo import detect_device_platform
        room_payload = {
            "port": int(endpoint_port),
            "game_title": game_title,
            "sys_code": sys_code,
            "core": resolve_core_name(sys_code) or "",
            "host": endpoint_host,
            "player_nick": "Host",
            "dev_model": detect_device_platform() or "Handheld"
        }
        threading.Thread(target=publish_room, args=(room_payload,), daemon=True).start()
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
        "🎮 *KÈO NETPLAY RETROHUB*",
        f"🕹️ *Game:* {game_title} `[{sys_code}]`",
        f"👤 *Host:* {dev_model}",
        "",
        f"🔥 *MÃ PHÒNG:*  👉 `{port}` 👈",
        "",
        f"👉 *Vào chơi:* Mở RetroHub ➔ Vào *Sảnh Online* hoặc *Nhập mã* `{port}`"
    ]
    text = "\n".join(msg_lines)

    target_chat_id = resolve_netplay_telegram_chat_id()
    dest_chats = [target_chat_id]
    if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID not in dest_chats:
        dest_chats.append(TELEGRAM_CHAT_ID)

    sent_any = False
    last_err = "Lỗi gửi Telegram"

    for cid in dest_chats:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": cid,
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
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                if res_data.get("ok"):
                    sent_any = True
                else:
                    last_err = res_data.get("description", "Lỗi Telegram")
        except Exception as e:
            last_err = str(e)

    if sent_any:
        return True, "Đã gửi mã phòng Netplay vào nhóm Telegram!"
    else:
        return False, f"Lỗi gửi Telegram: {last_err}"

def build_netplay_param(mode="host", host="a.pinggy.io", port=55435, nick="Player"):
    """Generate NET_PARAM string for RetroArch CLI."""
    if mode == "host":
        return f"-H --port {NETPLAY_PORT} --nick {nick}"
    else:
        clean_host = str(host or "a.pinggy.io").strip()
        clean_port = str(port).strip()
        if ":" in clean_host and (not clean_port or clean_port == "55435"):
            clean_host, clean_port = clean_host.split(":", 1)
        return f"-C {clean_host} --port {clean_port} --nick {nick}"
