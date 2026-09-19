# -*- coding: utf-8 -*-
"""RetroHub Netplay Public Lobby Client.

Communicates with the Cloudflare Worker + KV Lobby API to list, publish, and manage public Netplay rooms.
"""

import json
import ssl
import time
import urllib.request
from . import state

LOBBY_API_URL = "https://retrohub-lobby.nguyenxuanhoa040993.workers.dev/api"

_cached_rooms = []
_last_fetch_time = 0

def _make_ssl_context():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return None

def fetch_public_rooms(sys_code=None, timeout=6, force_refresh=False):
    """Fetch active online rooms from Cloudflare Workers KV lobby.

    Returns:
        (ok: bool, rooms_or_error: list | str)
    """
    global _cached_rooms, _last_fetch_time
    now = time.time()
    if not force_refresh and _cached_rooms and (now - _last_fetch_time < 2.0):
        if sys_code:
            return True, [r for r in _cached_rooms if str(r.get("sys_code", "")).upper() == sys_code.strip().upper()]
        return True, list(_cached_rooms)

    url = f"{LOBBY_API_URL}/rooms"
    if sys_code:
        url += f"?sys={urllib.request.quote(sys_code.strip())}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RetroHub-Handheld",
            "Accept": "application/json"
        }
    )
    ctx = _make_ssl_context()
    kw = {"timeout": timeout}
    if ctx:
        kw["context"] = ctx

    try:
        with urllib.request.urlopen(req, **kw) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                rooms = data.get("rooms", [])
                if not sys_code:
                    _cached_rooms = rooms
                    _last_fetch_time = now
                return True, rooms
            return False, data.get("error", "Lỗi nạp danh sách phòng")
    except Exception as e:
        vi = state.current_lang == "VI"
        return False, ("Không thể kết nối tới Sảnh chờ!" if vi else f"Cannot connect to lobby: {e}")

def find_room_by_port(port, timeout=5):
    """Find active room info by room code (port)."""
    if not port:
        return None
    p_str = str(port).strip()
    global _cached_rooms
    for r in _cached_rooms:
        if str(r.get("port") or r.get("id") or "").strip() == p_str:
            return r
    ok, rooms = fetch_public_rooms(timeout=timeout, force_refresh=True)
    if ok and isinstance(rooms, list):
        for r in rooms:
            if str(r.get("port") or r.get("id") or "").strip() == p_str:
                return r
    return None

def publish_room(room_data, timeout=6):
    """Publish a public Netplay room to the lobby API."""
    url = f"{LOBBY_API_URL}/rooms"
    payload = json.dumps(room_data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "User-Agent": "RetroHub-Handheld",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )
    ctx = _make_ssl_context()
    kw = {"timeout": timeout}
    if ctx:
        kw["context"] = ctx

    try:
        with urllib.request.urlopen(req, **kw) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return True, data.get("room")
            return False, data.get("error", "Lỗi đăng ký phòng")
    except Exception as e:
        return False, str(e)

def delete_room(port, timeout=5):
    """Remove a room from the public lobby."""
    if not port:
        return False, "Thiếu mã phòng"
    url = f"{LOBBY_API_URL}/rooms/{port}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RetroHub-Handheld",
            "Accept": "application/json"
        },
        method="DELETE"
    )
    ctx = _make_ssl_context()
    kw = {"timeout": timeout}
    if ctx:
        kw["context"] = ctx

    try:
        with urllib.request.urlopen(req, **kw) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok", False), data.get("message", "")
    except Exception as e:
        return False, str(e)

def heartbeat_room(port, timeout=5):
    """Extend room TTL on the lobby."""
    if not port:
        return False, "Thiếu mã phòng"
    url = f"{LOBBY_API_URL}/rooms/{port}/heartbeat"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "User-Agent": "RetroHub-Handheld",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    ctx = _make_ssl_context()
    kw = {"timeout": timeout}
    if ctx:
        kw["context"] = ctx

    try:
        with urllib.request.urlopen(req, **kw) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok", False), data.get("message", "")
    except Exception as e:
        return False, str(e)


def send_telegram_via_worker(text, parse_mode="HTML", topic="ssh", timeout=8):
    """Gửi tin nhắn Telegram thông qua Cloudflare Worker Proxy (100% không lộ token trên client)."""
    if not text:
        return False, "Nội dung tin nhắn trống"
    url = f"{LOBBY_API_URL}/telegram/send-message"
    payload = {
        "text": text,
        "parse_mode": parse_mode,
        "topic": topic
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "RetroHub-Handheld",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    ctx = _make_ssl_context()
    kw = {"timeout": timeout}
    if ctx:
        kw["context"] = ctx

    try:
        with urllib.request.urlopen(req, **kw) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                return True, res_data.get("message", "Thành công")
            return False, res_data.get("error", "Lỗi gửi Telegram từ Worker")
    except Exception as e:
        return False, f"Lỗi kết nối tới Worker Proxy: {e}"


def send_log_via_worker(filename, content, caption="", timeout=20):
    """Gửi file log Telegram thông qua Cloudflare Worker Proxy (100% không lộ token trên client)."""
    if not content:
        return False, "Nội dung file log trống"
    url = f"{LOBBY_API_URL}/telegram/send-log"
    payload = {
        "filename": filename or "retrohub_diagnostic.log",
        "content": content,
        "caption": caption
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "RetroHub-Handheld",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    ctx = _make_ssl_context()
    kw = {"timeout": timeout}
    if ctx:
        kw["context"] = ctx

    try:
        with urllib.request.urlopen(req, **kw) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                return True, res_data.get("message", "Thành công")
            return False, res_data.get("error", "Lỗi gửi file log từ Worker")
    except Exception as e:
        return False, f"Lỗi kết nối tới Worker Proxy: {e}"

