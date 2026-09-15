# -*- coding: utf-8 -*-
"""RetroHub Netplay Public Lobby Client.

Communicates with the Cloudflare Worker + KV Lobby API to list, publish, and manage public Netplay rooms.
"""

import json
import ssl
import urllib.request
from . import state

LOBBY_API_URL = "https://retrohub-lobby.nguyenxuanhoa040993.workers.dev/api"

def _make_ssl_context():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return None

def fetch_public_rooms(sys_code=None, timeout=6):
    """Fetch active online rooms from Cloudflare Workers KV lobby.

    Returns:
        (ok: bool, rooms_or_error: list | str)
    """
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
                return True, data.get("rooms", [])
            return False, data.get("error", "Lỗi nạp danh sách phòng")
    except Exception as e:
        vi = state.current_lang == "VI"
        return False, ("Không thể kết nối tới Sảnh chờ!" if vi else f"Cannot connect to lobby: {e}")

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
