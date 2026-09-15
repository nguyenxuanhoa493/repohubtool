#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gửi thông báo cập nhật OTA vào chủ đề chung của nhóm Telegram RetroHub."""

import os
import json
import ssl
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEGRAM_BOT_TOKEN = "8843439406:AAEtTnuMk68ilAniAxj8Kl3uTKZmVKEVDDs"
TELEGRAM_GROUP_CHAT_ID = "-1003890413445"

def send_ota_notification(version=None, note_vi=None):
    manifest_path = os.path.join(ROOT, "manifest.json")
    if not version or not note_vi:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                version = version or data.get("version", "")
                note_vi = note_vi or data.get("note", {}).get("vi", "")
        except Exception as e:
            print(f"Lỗi đọc manifest.json: {e}")
            return False

    msg_lines = [
        f"🚀 *[RetroHub] BẢN CẬP NHẬT MỚI: v{version} (OTA)*",
        "",
        "✨ *Nội dung cập nhật:*",
        f"• {note_vi}",
        "",
        "📲 *Cách cập nhật:*",
        "Bật Wi-Fi trên máy cầm tay ➔ Mở *RetroHub* ➔ Ứng dụng sẽ tự động phát hiện và cập nhật tệp mới nhất!"
    ]
    text = "\n".join(msg_lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_GROUP_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
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
        print(f"❌ Lỗi kết nối khi gửi thông báo Telegram: {e}")
        return False

if __name__ == "__main__":
    send_ota_notification()
