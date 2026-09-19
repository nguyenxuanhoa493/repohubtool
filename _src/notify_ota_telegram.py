#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gửi thông báo cập nhật OTA vào chủ đề chung của nhóm Telegram RetroHub."""

import os
import json
import ssl
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "files"))
from rh.secrets import get_telegram_token

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
        f"✨ <b>Điểm mới & Nội dung cập nhật:</b>",
        f"• {escaped_note}",
        "",
        "🛠️ <b>Chi tiết kỹ thuật:</b>",
        "• Khắc phục hoàn toàn lỗi thiếu gói cài đặt Giả lập Java (J2ME) bằng cơ chế tự động tải online từ xa.",
        "• Sửa lỗi crash <code>time_elapsed</code> khi bấm cài đặt trong Kho giả lập.",
        "• Chuyển nút Cài đặt Java trực tiếp sang bảng chi tiết Kho giả lập, loại bỏ biểu tượng emoji tránh lỗi font.",
        "• Tinh gọn nhãn tùy chọn hiển thị và bàn phím, bổ sung khung chú thích ngữ cảnh động.",
        "• Động cơ vẽ chữ tích hợp giới hạn chiều rộng <code>max_w</code> triệt tiêu nguy cơ đè chữ.",
        "",
        "📲 <b>Cách cập nhật qua OTA:</b>",
        "1. Bật <b>Wi-Fi</b> trên máy chơi game.",
        "2. Mở ứng dụng <b>RetroHub</b> ➔ Ứng dụng sẽ tự động thông báo và tải cập nhật trong 2–3 giây!",
        "3. Hoặc vào <b>Cài đặt (Settings) ➔ Kiểm tra cập nhật</b>."
    ]
    text = "\n".join(msg_lines)

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
