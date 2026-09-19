#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gửi thông báo cập nhật OTA vào chủ đề chung của nhóm Telegram RetroHub.

Nội dung lấy từ changelogs.json theo đúng số phiên bản trong manifest.json, nên
mỗi bản phát hành chỉ cần thêm một object vào file JSON đó là thông báo có đủ
headline + bullet của chính bản ấy. Trước đây phần "Chi tiết kỹ thuật" bị
hardcode nội dung của 2.37 và lặp lại y nguyên cho mọi bản sau."""

import os
import json
import ssl
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "files"))
from rh.secrets import get_telegram_token

TELEGRAM_GROUP_CHAT_ID = "-1003890413445"
CHANGELOG_FILE = os.path.join(ROOT, "changelogs.json")
# Telegram tu choi thong diep dai hon 4096 ky tu; chua lai mot it cho phan cuoi.
MAX_MESSAGE_CHARS = 4000

def changelog_entry(version):
    """Object cua *version* trong changelogs.json, hoac None."""
    try:
        with open(CHANGELOG_FILE, encoding="utf-8") as f:
            rels = json.load(f).get("releases", [])
    except Exception as e:
        print(f"Lỗi đọc changelogs.json: {e}")
        return None
    for rel in rels:
        if str(rel.get("version", "")) == str(version):
            return rel
    return None

def build_message(version, entry, lang="vi"):
    """Thông điệp Telegram cho một phiên bản, cắt bớt nếu quá dài."""
    import html
    head = (entry or {}).get("headline") or {}
    bullets = [b for b in ((entry or {}).get("bullets") or []) if b.get(lang)]
    lines = [
        f"🚀 <b>[RetroHub] BẢN CẬP NHẬT MỚI: v{version} (OTA)</b>",
        "",
        "✨ <b>Điểm mới &amp; Nội dung cập nhật:</b>",
        "• %s" % html.escape(head.get(lang, "")),
        "",
        "🛠️ <b>Chi tiết kỹ thuật:</b>",
    ]
    tail = [
        "",
        "📲 <b>Cách cập nhật qua OTA:</b>",
        "1. Bật <b>Wi-Fi</b> trên máy chơi game.",
        "2. Mở ứng dụng <b>RetroHub</b> ➔ Ứng dụng sẽ tự động thông báo và tải cập nhật trong 2–3 giây!",
        "3. Hoặc vào <b>Cài đặt (Settings) ➔ Kiểm tra cập nhật</b>.",
    ]
    fixed = len("\n".join(lines + tail))
    shown = []
    for b in bullets:
        candidate = shown + ["• %s" % html.escape(b[lang])]
        if fixed + len("\n".join(candidate)) > MAX_MESSAGE_CHARS:
            shown = candidate[:-1] + ["• …"]
            break
        shown = candidate
    if not bullets:
        shown = ["• (xem changelog đầy đủ trên web)"]
    return "\n".join(lines + shown + tail)

def send_ota_notification(version=None, note_vi=None):
    manifest_path = os.path.join(ROOT, "manifest.json")
    if not version:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                version = json.load(f).get("version", "")
        except Exception as e:
            print(f"Lỗi đọc manifest.json: {e}")
            return False

    entry = changelog_entry(version)
    if not entry:
        print(f"⚠️  changelogs.json chưa có mục cho v{version}; thông báo chỉ có tiêu đề.")
    text = build_message(version, entry)

    token = get_telegram_token()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_GROUP_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "RetroHub-Deploy"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("ok"):
                print(f"✅ Đã gửi thông báo cập nhật v{version} vào nhóm chung Telegram thành công!")
                return True
            else:
                print(f"❌ Lỗi Telegram: {res_data.get('description')}")
                return False
    except Exception as e:
        import subprocess
        try:
            res = subprocess.run([
                "curl", "-s", "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload)
            ], capture_output=True, text=True, timeout=10)
            res_data = json.loads(res.stdout)
            if res_data.get("ok"):
                print(f"✅ Đã gửi thông báo cập nhật v{version} vào nhóm chung Telegram thành công (qua curl)!")
                return True
            else:
                print(f"❌ Lỗi Telegram: {res_data.get('description')}")
                return False
        except Exception as ce:
            print(f"❌ Lỗi kết nối khi gửi thông báo Telegram: {e} / {ce}")
            return False

if __name__ == "__main__":
    send_ota_notification()
