#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script quét toàn bộ 16 thư mục hệ máy từ Google Drive Folder công khai
(https://drive.google.com/drive/folders/1wpztcUCBPwdvcGSS_xPR_UK0SPCt3QSk)
và cập nhật vào cơ sở dữ liệu catalog/roms_store.sqlite3 & files/catalog/roms_store.sqlite3.
"""

import os
import sys
import re
import ssl
import json
import gzip
import shutil
import sqlite3
import argparse
import urllib.request


DRIVE_FOLDERS = [
    ("1-H8FW-q-ZvonNI61a65sCLjPFhxUIFaC", "Atari - 2600", "ATARI2600"),
    ("1UA_i13YisPeuW1wGA7N_stLnPE5Z4HHo", "NEC - TurboGrafx CD", "PCE"),
    ("16aaE5fxcUVUfDiQ9xEwQB9FHqsHJWhkg", "NEC - TurboGrafx-16", "PCE"),
    ("1lSbWmyj8ITf-Z8F4GdAm_PvPvNPedlcq", "Nintendo - DS", "NDS"),
    ("1KXhNRQicma0q90SNNF55c-WJqMo1_nKo", "Nintendo - Game Boy Advance", "GBA"),
    ("1gK_9rFqicOzEHyXllcIivIYSOEFcwTyE", "Nintendo - Game Boy Color", "GBC"),
    ("1SIkDdQN3K-paDczXb335hEB9StH_rKkk", "Nintendo - GameCube", "NGC"),
    ("1LJdB6u7UKYb8Yf1rHUskbWihbgNQOtCj", "PortMaster", "PORTS"),
    ("1OSU3ATpWp6VyPnG_jMafLZbqOf7v8c0g", "Sega - Dreamcast", "DC"),
    ("1c6ZSVDEWJ9ie6qCxDhR6KtNp5hxUDS4m", "Sega - Game Gear", "GG"),
    ("1YfCpy_q-dcUTcURoFSlTLfw2tlOjFanD", "Sega - Genesis", "MD"),
    ("10wTwa2s9WVn2hDAkJ1r6EM_iYJW-3Ipr", "Sega - Saturn", "SS"),
    ("13KgjhdkPmYluwyoeVs4KjU-5IhfUQI0N", "Sega - Sega CD", "SEGACD"),
    ("1kL096sOBWwRMQSC1mMN-pYBo3zagWXFj", "SNK - NEO GEO", "NEOGEO"),
    ("1fzAsGjwHOMP-ckFWhdvhNf9gXAdEh5lS", "Sony - PS1", "PS"),
    ("1OOwHAkCdACvynYcp2ZBLtmMaZ3yV3b8n", "Sony - PSP", "PSP"),
]

def format_size(size_bytes):
    try:
        size = float(size_bytes)
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    except Exception:
        return "Unknown"

def clean_rom_title_str(filename):
    base = os.path.splitext(filename)[0] if "." in filename else filename
    base = re.sub(r'^\s*\d{1,4}\s*[\.\-]+\s*', '', base)
    base = re.sub(r'\[.*?\]|\(.*?\)', ' ', base)
    base = re.sub(r'[^a-zA-Z0-9\s]', ' ', base)
    return re.sub(r'\s+', ' ', base).strip().lower()

def raw_display_title(filename):
    base = os.path.splitext(filename)[0] if "." in filename else filename
    base = re.sub(r'^\s*\d{1,4}\s*[\.\-]+\s*', '', base)
    return re.sub(r'\s+', ' ', base).strip()

LOBBY_API_URL = "https://retrohub-lobby.nguyenxuanhoa040993.workers.dev/api"


def list_drive_folder(folder_id, api_key=None):
    # 1. Ưu tiên gọi qua Cloudflare Worker Proxy (100% bảo mật, không cần key ở local)
    if not api_key:
        try:
            worker_url = f"{LOBBY_API_URL}/gdrive/list?folder_id={folder_id}"
            req = urllib.request.Request(worker_url, headers={"User-Agent": "RetroHub-Tool"})
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                if res_json.get("ok"):
                    return res_json.get("files", [])
        except Exception:
            pass

    # 2. Dự phòng: Nếu có api_key được truyền qua tham số hoặc GDRIVE_API_KEY
    if not api_key:
        api_key = os.environ.get("GDRIVE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Không thể quét qua Cloudflare Worker và chưa cung cấp GDRIVE_API_KEY!")

    url = f"https://drivefrontend-pa.clients6.google.com/v1/items:list?key={api_key}"
    headers = {



        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Content-Type": "application/json+protobuf",
        "Origin": "https://drive.google.com",
        "Referer": "https://drive.google.com/",
        "x-goog-drive-client-version": "drive.web-frontend_20260910.12_p2",
        "x-goog-fieldmask": "items(id,title,mime_type,file_size)"
    }
    body = [
        [None, None, None, None, 0, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 0, None, None, [4, 1, 1], None, None, None, None, None, None, None, None, None, None, [[1]], None, None, None, None, None, None, None, [[folder_id, 0]]],
        [1000, "", [2, 5]]
    ]
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    ctx = ssl._create_unverified_context()
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    res_json = json.loads(resp.read().decode("utf-8"))
    items = res_json[0] if res_json and len(res_json) > 0 and isinstance(res_json[0], list) else []
    
    file_list = []
    for it in items:
        if isinstance(it, list) and len(it) > 2:
            fid = it[0]
            fname = it[2]
            fsize = it[13] if len(it) > 13 and it[13] is not None else 0
            mime = it[3] if len(it) > 3 and it[3] is not None else ""
            if mime != "application/vnd.google-apps.folder":
                file_list.append({
                    "id": fid,
                    "filename": fname,
                    "size": fsize,
                    "size_str": format_size(fsize)
                })
    return file_list

def import_to_db(db_path, all_games):
    print(f"\nImporting into {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    inserted_games = 0
    inserted_sources = 0

    for item in all_games:
        sys_code = item["sys_code"]
        filename = item["filename"]
        file_id = item["id"]
        size_str = item["size_str"]
        
        title = raw_display_title(filename)
        clean_title = clean_rom_title_str(filename)
        if not clean_title:
            clean_title = filename.lower()

        # Check existing game by (sys_code, clean_title)
        cur.execute("SELECT id FROM games WHERE sys_code = ? AND clean_title = ?", (sys_code, clean_title))
        row = cur.fetchone()
        if row:
            game_id = row[0]
        else:
            cur.execute("""
                INSERT INTO games (sys_code, title, clean_title, img_url, region, genre, is_viet, is_hit, is_favorite, download_count, rating, is_hack)
                VALUES (?, ?, ?, NULL, 'USA', NULL, 0, 0, 0, 0, 0.0, 0)
            """, (sys_code, title, clean_title))
            game_id = cur.lastrowid
            inserted_games += 1

        rom_url = f"https://drive.google.com/uc?id={file_id}&export=download"

        # Insert or replace game_source
        cur.execute("""
            INSERT OR REPLACE INTO game_sources (game_id, source_name, rom_url, filename, file_size_str, priority, is_alive)
            VALUES (?, 'GDRIVE', ?, ?, ?, 1, 1)
        """, (game_id, rom_url, filename, size_str))
        inserted_sources += 1

    conn.commit()
    conn.close()
    print(f"Finished {db_path}: Added {inserted_games} new games, {inserted_sources} GDRIVE sources.")

def main():
    parser = argparse.ArgumentParser(description="Quét Google Drive Folders và import vào catalog DB.")
    parser.add_argument("--api-key", "-k", default="",
                        help="Google API Key dự phòng (mặc định script sẽ ưu tiên dùng Cloudflare Worker Proxy).")
    parser.add_argument("--folder-id", "-f", default="",
                        help="Chỉ quét 1 folder ID cụ thể thay vì toàn bộ danh sách mặc định.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chỉ quét và in kết quả ra màn hình, KHÔNG ghi vào cơ sở dữ liệu.")
    args = parser.parse_args()

    api_key = (args.api_key or os.environ.get("GDRIVE_API_KEY", "")).strip()

    folders_to_scan = DRIVE_FOLDERS
    if args.folder_id:
        # Tìm xem folder_id có trong danh sách chuẩn không
        matched = [f for f in DRIVE_FOLDERS if f[0] == args.folder_id]
        if matched:
            folders_to_scan = matched
        else:
            folders_to_scan = [(args.folder_id, "Custom Folder", "TEST")]

    all_items = []
    print("--- Scanning Google Drive Folders (Worker Proxy / Direct) ---")
    for fid, ftitle, sys_code in folders_to_scan:
        print(f"Fetching '{ftitle}' ({sys_code}) [ID: {fid}]...", end="", flush=True)
        try:
            files = list_drive_folder(fid, api_key)
            print(f" {len(files)} files")

            for f in files:
                f["sys_code"] = sys_code
                all_items.append(f)
        except Exception as e:
            print(f" ERROR: {e}")

    print(f"\nTotal scanned files: {len(all_items)}")

    if args.dry_run:
        print("\n[DRY RUN] Danh sách mẫu (tối đa 15 file đầu tiên):")
        for i, it in enumerate(all_items[:15], 1):
            print(f"  {i:2d}. [{it['sys_code']}] {it['filename']} ({it.get('size_str', '--')}) - ID: {it['id']}")
        if len(all_items) > 15:
            print(f"  ... và còn {len(all_items) - 15} file khác.")
        print("\nĐã chạy xong chế độ Dry-run (không thay đổi Database).")
        return

    # Update both DB locations
    db_paths = [
        "catalog/roms_store.sqlite3",
        "files/catalog/roms_store.sqlite3"
    ]
    for p in db_paths:
        if os.path.exists(p):
            import_to_db(p, all_items)
            # Re-compress to .gz if .gz exists
            gz_p = p + ".gz"
            if os.path.exists(gz_p):
                print(f"Re-compressing to {gz_p}...")
                with open(p, "rb") as f_in, gzip.open(gz_p, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                print(f"Updated {gz_p}")

if __name__ == "__main__":
    main()
