#!/usr/bin/env bash
set -e

IP="192.168.100.115"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Đang kiểm tra kết nối tới thiết bị $IP..."
if ! ping -c 1 -W 2000 "$IP" > /dev/null 2>&1; then
    echo "[!] Thiết bị đang tắt màn hình hoặc ngắt kết nối Wi-Fi. Vui lòng bật sáng màn hình máy TrimUI."
    exit 1
fi

echo "==> 1. Xóa bản cài đặt cũ trên máy..."
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@"$IP" "rm -rf /mnt/SDCARD/Apps/RetroHub"

VERSION=$(grep '"version"' "$ROOT/manifest.json" | head -n 1 | sed -E 's/.*"version": "([^"]+)".*/\1/')
ZIP_FILE="$ROOT/dist/RetroHub-${VERSION}-full.zip"

if [ ! -f "$ZIP_FILE" ]; then
    echo "[!] Không tìm thấy $ZIP_FILE. Đang đóng gói từ tools/make_release.py..."
    python3 "$ROOT/tools/make_release.py"
fi

echo "==> 2. Sao chép gói RetroHub-${VERSION}-full.zip sang thiết bị..."
scp -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$ZIP_FILE" root@"$IP":/tmp/RetroHub-latest.zip

echo "==> 3. Giải nén cài đặt sạch..."
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@"$IP" "
    unzip -q -o /tmp/RetroHub-latest.zip -d /mnt/SDCARD/
    rm -f /tmp/RetroHub-latest.zip
    chmod +x /mnt/SDCARD/Apps/RetroHub/launch.sh 2>/dev/null || true
    chmod +x /mnt/SDCARD/Apps/RetroHub/bin/* 2>/dev/null || true
    find /mnt/SDCARD/Apps/RetroHub -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find /mnt/SDCARD/Apps/RetroHub -name '*.pyc' -delete 2>/dev/null || true
    sync
"

echo "==> Hoàn tất cài đặt sạch bản RetroHub v${VERSION} Full trên thiết bị!"
