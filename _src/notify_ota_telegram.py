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

    import html
    escaped_note = html.escape(note_vi)
    msg_lines = [
        f"🚀 <b>[RetroHub] BẢN CẬP NHẬT MỚI: v{version} (OTA)</b>",
        "",
        "✨ <b>Điểm mới & Tối ưu nổi bật:</b>",
        "• 🔍 <b>Sửa lỗi Tìm kiếm Game Online:</b> Kết nối trực tiếp SQLite DAO FTS, hỗ trợ tìm kiếm đa từ khóa thông minh (multi-word AND), hiển thị mã hệ máy và chuẩn hóa nút Quay lại.",
        "• 🖼️ <b>Tối ưu Cào ảnh bìa (Boxart):</b> Khắc phục lỗi tương thích tham số và unpack tuple trong Modal hành động khi bấm Tải bìa, kèm thông báo Toast thời gian thực.",
        "• 📦 <b>Tự động Cào ảnh bù & Trích xuất Icon Java:</b> Tự động cào ảnh bìa fallback khi link gốc bị lỗi/placeholder và tự động trích xuất icon gốc từ file .jar của game Java J2ME.",
        "",
        "📲 <b>Cách cập nhật:</b>",
        "Bật Wi-Fi trên máy cầm tay ➔ Mở <b>RetroHub</b> ➔ Ứng dụng sẽ tự động phát hiện và cập nhật tệp mới nhất!"
    ]
    text = "\n".join(msg_lines)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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
        print(f"❌ Lỗi kết nối khi gửi thông báo Telegram: {e}")
        return False

if __name__ == "__main__":
    send_ota_notification()
