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

echo "==> 2. Sao chép gói RetroHub-2.27-full.zip sang thiết bị..."
scp -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$ROOT/dist/RetroHub-2.27-full.zip" root@"$IP":/tmp/RetroHub-2.27-full.zip

echo "==> 3. Giải nén cài đặt sạch..."
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@"$IP" "
    unzip -q -o /tmp/RetroHub-2.27-full.zip -d /mnt/SDCARD/
    rm -f /tmp/RetroHub-2.27-full.zip
    chmod +x /mnt/SDCARD/Apps/RetroHub/launch.sh 2>/dev/null || true
    chmod +x /mnt/SDCARD/Apps/RetroHub/bin/* 2>/dev/null || true
    find /mnt/SDCARD/Apps/RetroHub -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find /mnt/SDCARD/Apps/RetroHub -name '*.pyc' -delete 2>/dev/null || true
    sync
"

echo "==> Hoàn tất cài đặt sạch bản RetroHub 2.27 Full trên thiết bị!"
