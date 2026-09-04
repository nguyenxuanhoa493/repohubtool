#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync updated RetroHub files to TrimUI device via SSH / SFTP."""

import os
import sys
import paramiko

TARGET_FILES = [
    ("rh/yt.py", "rh/yt.py"),
    ("rh/yt_player.py", "rh/yt_player.py"),
    ("rh/i18n.py", "rh/i18n.py"),
    ("rh/paths.py", "rh/paths.py"),
    ("rh/version.py", "rh/version.py"),
    ("rh/catalog.py", "rh/catalog.py"),
    ("db.py", "db.py"),
    ("app.py", "app.py"),
    ("launch.sh", "launch.sh"),
    ("bin/yt-dlp", "bin/yt-dlp"),
]



def get_configured_ip():
    cfg_paths = [
        os.path.expanduser("~/.gemini/config/mcp_servers/ssh_device/device_config.json"),
        os.path.expanduser("~/.gemini/config/mcp_servers/trimui_ssh/trimui_config.json")
    ]
    for p in cfg_paths:
        if os.path.exists(p):
            try:
                import json
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f).get("host", "172.16.3.102")
            except Exception:
                pass
    return "172.16.3.102"


def sync(ip=None, port=22, user="root", pwd="root"):
    if not ip:
        ip = get_configured_ip()
    print(f"[*] Đang kết nối SSH tới {user}@{ip}:{port}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, port=port, username=user, password=pwd, timeout=6)
        print("[+] Kết nối SSH thành công!")
    except Exception as e:
        print(f"[-] Không thể kết nối SSH tới {ip}: {e}")
        return False

    sftp = ssh.open_sftp()

    # Determine app directory on device
    target_candidates = [
        "/mnt/SDCARD/Apps/RetroHub",
        "/mnt/SDCARD/Apps/repohubtool",
        "/mnt/SDCARD/Emus/RetroHub",
        "/mnt/SDCARD/Emus/RETROHUB",
    ]
    app_dir = None
    for cand in target_candidates:
        try:
            sftp.stat(cand)
            app_dir = cand
            print(f"[+] Tìm thấy thư mục RetroHub: {app_dir}")
            break
        except Exception:
            pass

    if not app_dir:
        app_dir = "/mnt/SDCARD/Apps/RetroHub"
        print(f"[!] Mặc định sử dụng thư mục: {app_dir}")

    local_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "files")

    print("[*] Bắt đầu đồng bộ tệp...")
    for rel_src, rel_dst in TARGET_FILES:
        src = os.path.join(local_root, rel_src)
        dst = f"{app_dir}/{rel_dst}"
        dst_parent = os.path.dirname(dst)
        try:
            sftp.stat(dst_parent)
        except Exception:
            try:
                sftp.mkdir(dst_parent)
            except Exception:
                pass

        try:
            sftp.put(src, dst)
            print(f"  ✓ {rel_src} -> {dst}")
        except Exception as e:
            print(f"  ✗ Lỗi đồng bộ {rel_src}: {e}")

    sftp.close()

    # Chmod executable and clear pycache
    print("[*] Phân quyền và dọn dẹp bytecode cache...")
    ssh.exec_command(f"chmod +x {app_dir}/bin/yt-dlp 2>/dev/null; rm -rf {app_dir}/rh/__pycache__ {app_dir}/__pycache__; sync")
    ssh.close()
    print("[+] Hoàn tất cập nhật ứng dụng trên thiết bị!")
    return True


if __name__ == "__main__":
    target_ip = sys.argv[1] if len(sys.argv) > 1 else None
    sync(ip=target_ip)
