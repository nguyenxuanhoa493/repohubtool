#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# RETROHUB - WEB GAME MANAGER (PORT 8090)
# Quản lý kho game qua Web: Đổi tên, Cào ảnh bìa (Scrape Art), Chuyển hệ máy, Tải ROM
# Hoàn toàn thuần Python stdlib - Zero external dependencies - Siêu nhẹ, mượt mà
# ==============================================================================

import os
import sys
import re
import time
import json
import shutil
import subprocess
import ssl
import urllib.request
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

try:
    _SSL_CONTEXT = ssl.create_default_context()
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CONTEXT = None

PORT = 8090

try:
    from rh import state
    from rh.save_manager import (scan_all_saves, get_saves_stats, create_save_backup,
        list_save_backups, restore_save_backup, delete_save_backup)
    from rh.cheat_manager import get_cheats_status, count_cheats, cheat_runner
    from rh.logger import (upload_log_to_telegram, generate_debug_report, LOG_FILE,
        clear_log, get_log_size_str, get_device_id)
except ImportError:
    _cur_d = os.path.dirname(os.path.abspath(__file__))
    if _cur_d not in sys.path:
        sys.path.insert(0, _cur_d)
    from rh import state
    from rh.save_manager import (scan_all_saves, get_saves_stats, create_save_backup,
        list_save_backups, restore_save_backup, delete_save_backup)
    from rh.cheat_manager import get_cheats_status, count_cheats, cheat_runner
    from rh.logger import (upload_log_to_telegram, generate_debug_report, LOG_FILE,
        clear_log, get_log_size_str, get_device_id)

# Xác định đường dẫn thẻ nhớ
SDCARD_PATH = os.environ.get("SDCARD_PATH") or ("/mnt/SDCARD" if os.path.isdir("/mnt/SDCARD") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_mock_sdcard"))
ROMS_DIR = os.path.join(SDCARD_PATH, "Roms")
IMGS_DIR = os.path.join(SDCARD_PATH, "Imgs")
EMUS_DIR = os.path.join(SDCARD_PATH, "Emus")

# Tên các hệ máy chuẩn
SYSTEM_NAMES = {
    "MAME": "Arcade (MAME)",
    "ARCADE": "Arcade / CPS / NeoGeo",
    "CPS1": "Capcom CPS-1",
    "CPS2": "Capcom CPS-2",
    "CPS3": "Capcom CPS-3",
    "NEOGEO": "SNK Neo Geo",
    "FC": "NES / Famicom",
    "NES": "NES / Famicom",
    "SFC": "Super Nintendo (SNES)",
    "SNES": "Super Nintendo (SNES)",
    "GBA": "Game Boy Advance",
    "GBC": "Game Boy Color",
    "GB": "Game Boy",
    "N64": "Nintendo 64",
    "NDS": "Nintendo DS",
    "MD": "Sega Genesis / Mega Drive",
    "GENESIS": "Sega Genesis / Mega Drive",
    "SEGACD": "Sega CD / Mega CD",
    "GG": "Sega Game Gear",
    "MS": "Sega Master System",
    "SS": "Sega Saturn",
    "DC": "Sega Dreamcast",
    "PS": "Sony PlayStation (PS1)",
    "PS1": "Sony PlayStation (PS1)",
    "PSP": "PlayStation Portable (PSP)",
    "PCE": "PC Engine / TG-16",
    "WS": "WonderSwan",
    "WSC": "WonderSwan Color",
    "NGP": "Neo Geo Pocket",
    "PICO8": "PICO-8",
    "ATARI2600": "Atari 2600",
    "ATARI7800": "Atari 7800",
    "LYNX": "Atari Lynx",
    "JAVA": "Java J2ME (Mobile)",
}

# Mapping sang tên hệ máy chuẩn trên thumbnails.libretro.com
LIBRETRO_MAP = {
    "GBA": "Nintendo - Game Boy Advance",
    "GBC": "Nintendo - Game Boy Color",
    "GB": "Nintendo - Game Boy",
    "FC": "Nintendo - Nintendo Entertainment System",
    "NES": "Nintendo - Nintendo Entertainment System",
    "SFC": "Nintendo - Super Nintendo Entertainment System",
    "SNES": "Nintendo - Super Nintendo Entertainment System",
    "N64": "Nintendo - Nintendo 64",
    "NDS": "Nintendo - Nintendo DS",
    "MD": "Sega - Mega Drive - Genesis",
    "GENESIS": "Sega - Mega Drive - Genesis",
    "SEGACD": "Sega - Mega-CD - Sega CD",
    "GG": "Sega - Game Gear",
    "MS": "Sega - Master System - Mark III",
    "SS": "Sega - Saturn",
    "DC": "Sega - Dreamcast",
    "PS": "Sony - PlayStation",
    "PS1": "Sony - PlayStation",
    "PSP": "Sony - PlayStation Portable",
    "PCE": "NEC - PC Engine - TurboGrafx 16",
    "WS": "Bandai - WonderSwan",
    "WSC": "Bandai - WonderSwan Color",
    "NGP": "SNK - Neo Geo Pocket",
    "NEOGEO": "SNK - Neo Geo",
    "ATARI2600": "Atari - 2600",
    "ATARI7800": "Atari - 7800",
    "LYNX": "Atari - Lynx",
    "FBNEO": "FBNeo - Arcade Games",
    "MAME": "MAME",
    "ARCADE": "FBNeo - Arcade Games",
    "CPS1": "FBNeo - Arcade Games",
    "CPS2": "FBNeo - Arcade Games",
    "CPS3": "FBNeo - Arcade Games",
}

_LIBRETRO_INDEX_CACHE = {}

def get_catalog_db_path():
    # 1. Tìm trực tiếp database sqlite3
    candidates = [
        os.path.join(SDCARD_PATH, "Apps", "RetroHub", "catalog", "roms_store.sqlite3"),
        os.path.join(SDCARD_PATH, "RetroHub", "catalog", "roms_store.sqlite3"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalog", "roms_store.sqlite3"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog", "roms_store.sqlite3"),
        "/tmp/roms_store.sqlite3",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.path.getsize(c) > 1000000:
            return c

    # 2. Tìm file nén .sqlite3.gz để giải nén tức thì vào /tmp
    gz_candidates = [
        os.path.join(SDCARD_PATH, "Apps", "RetroHub", "catalog", "roms_store.sqlite3.gz"),
        os.path.join(SDCARD_PATH, "RetroHub", "catalog", "roms_store.sqlite3.gz"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalog", "roms_store.sqlite3.gz"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog", "roms_store.sqlite3.gz"),
    ]
    for gz in gz_candidates:
        if os.path.isfile(gz):
            try:
                import gzip
                out_tmp = "/tmp/roms_store.sqlite3"
                if not os.path.isfile(out_tmp) or os.path.getsize(out_tmp) < 1000000:
                    with gzip.open(gz, "rb") as f_in, open(out_tmp, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return out_tmp
            except Exception as e:
                print(f"Error decompressing {gz}: {e}")
    return None

STOP_WORDS = {
    'of', 'the', 'a', 'an', 'and', 'in', 'on', 'to', 'for', 'at', 'by', 'from',
    'with', 'de', 'der', 'die', 'das', 'le', 'la', 'les',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
}

def search_catalog_db(sys_code, query, max_results=8):
    db_p = get_catalog_db_path()
    if not db_p:
        return []
    try:
        import sqlite3
        conn = sqlite3.connect(db_p, timeout=5)
        cur = conn.cursor()

        sys_aliases = [sys_code.upper()]
        if sys_code.upper() in ("NES", "FC"):
            sys_aliases = ["FC", "NES"]
        elif sys_code.upper() in ("SNES", "SFC"):
            sys_aliases = ["SFC", "SNES"]
        elif sys_code.upper() in ("GENESIS", "MD"):
            sys_aliases = ["MD", "GENESIS"]
        elif sys_code.upper() in ("PS1", "PS"):
            sys_aliases = ["PS", "PS1"]

        clean_q = re.sub(r'\(.*?\)|\[.*?\]', '', query).strip()
        words = [w.lower() for w in clean_q.split() if w]
        if not words:
            words = [w.lower() for w in query.strip().split() if w]
        if not words:
            return []

        placeholders = ",".join("?" * len(sys_aliases))

        def execute_query(w_list):
            sql = f"SELECT title, img_url FROM games WHERE sys_code IN ({placeholders}) AND img_url IS NOT NULL AND img_url != ''"
            params = list(sys_aliases)
            for w in w_list:
                sql += " AND lower(title) LIKE ?"
                params.append(f"%{w}%")
            sql += f" LIMIT {max_results}"
            cur.execute(sql, params)
            return [r for r in cur.fetchall() if r[1] and "no-image" not in r[1].lower()]

        # Lần 1: Khớp tất cả các từ trong query
        rows = execute_query(words)

        # Lần 2: Nếu không có kết quả, loại bỏ stop words và số phụ để tìm từ khóa cốt lõi
        if not rows and len(words) > 1:
            sig_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
            if sig_words and sig_words != words:
                rows = execute_query(sig_words)

        conn.close()

        results = []
        for title, img_url in rows:
            results.append({
                "title": title,
                "type": "Catalog DB",
                "url": img_url
            })
        return results
    except Exception as e:
        print(f"Error querying catalog db: {e}")
        return []

def get_libretro_file_list(sys_folder, category="Named_Boxarts", allow_fetch=True):
    global _LIBRETRO_INDEX_CACHE
    cache_key = f"{sys_folder}#{category}"
    if cache_key in _LIBRETRO_INDEX_CACHE:
        return _LIBRETRO_INDEX_CACHE[cache_key]

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', cache_key)
    tmp_path = f"/tmp/rh_{safe_name}.json"
    if os.path.isfile(tmp_path):
        try:
            if time.time() - os.path.getmtime(tmp_path) < 7 * 86400:
                with open(tmp_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        _LIBRETRO_INDEX_CACHE[cache_key] = data
                        return data
        except Exception:
            pass

    if not allow_fetch:
        return []

    url = f"http://thumbnails.libretro.com/{urllib.parse.quote(sys_folder)}/{category}/"
    html = ""
    try:
        res = subprocess.run(["curl", "-s", "--max-time", "6", url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=7)
        if res.returncode == 0 and res.stdout:
            html = res.stdout.decode("utf-8", errors="ignore")
    except Exception:
        pass

    if not html:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Connection": "close"})
            kwargs = {"timeout": 5}
            if _SSL_CONTEXT:
                kwargs["context"] = _SSL_CONTEXT
            with urllib.request.urlopen(req, **kwargs) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            pass

    if html:
        pattern = re.compile(r'href=\"([^\"/]+\.png)\"')
        files = pattern.findall(html)
        decoded = [urllib.parse.unquote(f) for f in files]
        if decoded:
            _LIBRETRO_INDEX_CACHE[cache_key] = decoded
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(decoded, f)
            except Exception:
                pass
            return decoded

    return []

def search_libretro_boxarts(sys_code, query, max_results=12, allow_fetch=True):
    sys_folder = LIBRETRO_MAP.get(sys_code.upper())
    if not sys_folder:
        for k, v in LIBRETRO_MAP.items():
            if k in sys_code.upper():
                sys_folder = v
                break
    if not sys_folder:
        return []

    clean_q = re.sub(r'\(.*?\)|\[.*?\]', '', query).strip()
    words = [w.lower() for w in clean_q.split() if w]
    if not words:
        words = [w.lower() for w in query.strip().split() if w]
    if not words:
        return []

    sig_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    if not sig_words:
        sig_words = words

    def score(name):
        pts = len(name)
        if "(USA" in name or "(World" in name or "(En" in name:
            pts -= 50
        if "(Japan" in name and "japan" not in query.lower():
            pts += 40
        return pts

    candidates = []

    # Duyệt qua Named_Boxarts, nếu không có ảnh thì tìm tiếp trong Named_Snaps và Named_Titles
    for cat in ["Named_Boxarts", "Named_Snaps", "Named_Titles"]:
        files = get_libretro_file_list(sys_folder, category=cat, allow_fetch=allow_fetch)
        if not files:
            continue

        matches = [f for f in files if all(w in f.lower() for w in words)]
        if not matches and sig_words != words:
            matches = [f for f in files if all(w in f.lower() for w in sig_words)]

        if matches:
            matches.sort(key=score)
            cat_label = "Boxart" if cat == "Named_Boxarts" else ("Snap" if cat == "Named_Snaps" else "Title")
            for m in matches[:max_results]:
                boxart_url = f"http://thumbnails.libretro.com/{urllib.parse.quote(sys_folder)}/{cat}/{urllib.parse.quote(m)}"
                candidates.append({
                    "title": m[:-4],
                    "type": f"Libretro {cat_label}",
                    "url": boxart_url,
                    "verified": True
                })
            if candidates:
                break

    if not candidates:
        clean_name = query.replace("&", "_").replace("*", "_").replace("/", "_").replace(":", "_").replace("`", "_")
        for suffix in ["", " (USA)", " (World)", " (USA, Europe)", " (Europe)", " (Japan)"]:
            candidate_file = f"{clean_name}{suffix}.png"
            boxart_url = f"http://thumbnails.libretro.com/{urllib.parse.quote(sys_folder)}/Named_Boxarts/{urllib.parse.quote(candidate_file)}"
            candidates.append({
                "title": f"{clean_name}{suffix}",
                "type": "Libretro Boxart",
                "url": boxart_url,
                "verified": False
            })

    return candidates

def is_url_alive(url, timeout=1.5):
    """Kiểm tra nhanh xem URL ảnh có phản hồi 200/206/302 hay không (loại bỏ link chết, 404, 403 hotlink-block)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/*,*/*;q=0.8"
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        kwargs = {"timeout": timeout}
        if _SSL_CONTEXT:
            kwargs["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **kwargs) as resp:
            return resp.status in (200, 301, 302, 304)
    except Exception:
        try:
            req = urllib.request.Request(url, headers={**headers, "Range": "bytes=0-64"})
            kwargs = {"timeout": timeout}
            if _SSL_CONTEXT:
                kwargs["context"] = _SSL_CONTEXT
            with urllib.request.urlopen(req, **kwargs) as resp:
                return resp.status in (200, 206, 301, 302, 304)
        except Exception:
            return False

def search_web_images(query, max_results=8):
    """Tìm kiếm ảnh bìa trực tiếp từ Web Image Search (Bing), không bị chặn Captcha và không cần JS.
    Tự động kiểm tra song song và loại bỏ toàn bộ liên kết chết (404, 403, timeout) trước khi trả về."""
    try:
        url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)
        kwargs = {"timeout": 6}
        if _SSL_CONTEXT:
            kwargs["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **kwargs) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        items = []
        seen = set()
        matches = re.findall(r'&quot;murl&quot;:&quot;(https?://[^&]+)&quot;.*?&quot;t&quot;:&quot;([^&]+)&quot;', html)
        for img_url, title in matches:
            if img_url in seen:
                continue
            clean_title = re.sub(r'<.*?>', '', title).replace('&quot;', '"').replace('&amp;', '&').strip()
            seen.add(img_url)
            items.append({
                "title": clean_title[:60] if clean_title else "Ảnh Web",
                "type": "Web Search",
                "url": img_url
            })
            if len(items) >= max_results + 4:
                break

        # Lọc bỏ link chết / 404 / lỗi hotlink bằng đa luồng song song
        if items:
            with ThreadPoolExecutor(max_workers=min(len(items), 8)) as executor:
                alive_status = list(executor.map(lambda it: is_url_alive(it["url"]), items))
            items = [it for it, ok in zip(items, alive_status) if ok]

        return items[:max_results]
    except Exception as e:
        print(f"Error in search_web_images: {e}")
        return []

def clean_rom_title(filename):
    """Làm sạch tên file ROM để tối ưu từ khóa tìm kiếm ảnh bìa."""
    base = os.path.splitext(filename)[0]
    base = re.sub(r'[_\.\+]+', ' ', base)
    base = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]\s*', ' ', base)
    base = re.sub(r'\b(EUR|USA|JAP|JPN|PAL|NTSC|MULTi\d*|Goomba|Razor1911|Dump)\b', ' ', base, flags=re.IGNORECASE)
    base = re.sub(r'\b(PSP|PS1|PS2|GBA|NDS|SNES|NES|MD|GENESIS)\b', ' ', base, flags=re.IGNORECASE)
    base = re.sub(r'[-–—]+', ' ', base)
    return re.sub(r'\s+', ' ', base).strip()

def find_best_boxart(sys_code, clean_title, fast_only=False):
    """Tìm ảnh bìa phù hợp nhất theo thứ tự ưu tiên tốc độ:
    1. SQLite Catalog DB (siêu nhanh ~1ms, ảnh chất lượng cao / Việt hóa)
    2. Libretro CDN index cache (~5ms, ảnh chính thức từ thumbnails.libretro.com)
    3. Web Images (Bing) nếu 2 nguồn trên không có và fast_only=False (~1-3s)
    """
    # 1. SQLite Catalog DB
    try:
        db_res = search_catalog_db(sys_code, clean_title, max_results=1)
        if db_res and db_res[0].get("url"):
            return db_res[0]["url"], "Catalog DB"
    except Exception as e:
        print(f"find_best_boxart db error: {e}")

    # 2. Libretro CDN index cache
    try:
        lr_res = search_libretro_boxarts(sys_code, clean_title, max_results=3, allow_fetch=True)
        for it in lr_res:
            u = it.get("url")
            if not u:
                continue
            if it.get("verified"):
                return u, it.get("type", "Libretro")
            elif is_url_alive(u, timeout=1.0):
                return u, it.get("type", "Libretro")
    except Exception as e:
        print(f"find_best_boxart libretro error: {e}")

    # 3. Web Images Search (Bing)
    if not fast_only:
        try:
            web_q = f"{clean_title} {sys_code} boxart cover"
            web_res = search_web_images(web_q, max_results=2)
            if web_res and web_res[0].get("url"):
                return web_res[0]["url"], "Web Search"
        except Exception as e:
            print(f"find_best_boxart web error: {e}")

    return None, None

# Đuôi file ROM hợp lệ thường gặp
VALID_EXTS = {
    ".zip", ".7z", ".rar", ".chd", ".iso", ".cue", ".bin", ".pbp",
    ".gba", ".gbc", ".gb", ".nes", ".sfc", ".smc", ".md", ".smd", ".gen",
    ".n64", ".z64", ".v64", ".nds", ".cso", ".pce", ".ws", ".wsc",
    ".ngp", ".ngc", ".p8", ".png", ".jar", ".a26", ".a78", ".lnx"
}

def download_image_to_file(img_url, target_path, timeout=15):
    """Tải file ảnh từ URL (HTTP/HTTPS), bỏ qua lỗi kiểm tra SSL trên hệ máy cầm tay.
    Thử urllib với unverified SSL trước, nếu gặp lỗi thì fallback sang curl -k."""
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": img_url,
    }

    # 1. Thử urllib.request với unverified SSL context
    try:
        req = urllib.request.Request(img_url, headers=headers)
        kwargs = {"timeout": timeout}
        if _SSL_CONTEXT:
            kwargs["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **kwargs) as resp:
            if resp.status == 200:
                data = resp.read()
                if len(data) > 32:
                    with open(target_path, "wb") as f:
                        f.write(data)
                    return True, None
    except Exception:
        pass

    # 2. Fallback sang curl -k (hỗ trợ TLS, tự bỏ qua xác thực chứng chỉ CA)
    try:
        cmd = [
            "curl", "-k", "-s", "-L",
            "--max-time", str(timeout),
            "-A", headers["User-Agent"],
            "-o", target_path,
            img_url
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout + 2)
        if res.returncode == 0 and os.path.isfile(target_path) and os.path.getsize(target_path) > 32:
            return True, None
    except Exception:
        pass

    return False, "Không thể tải ảnh từ URL này (vui lòng kiểm tra lại đường dẫn ảnh hoặc kết nối Wi-Fi của máy)"

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def get_sd_storage():
    try:
        total, used, free = shutil.disk_usage(SDCARD_PATH)
        return {
            "total": format_size(total),
            "used": format_size(used),
            "free": format_size(free),
            "pct": int((used / total) * 100) if total > 0 else 0
        }
    except Exception:
        return {"total": "N/A", "used": "N/A", "free": "N/A", "pct": 0}

def list_all_systems():
    os.makedirs(ROMS_DIR, exist_ok=True)
    os.makedirs(IMGS_DIR, exist_ok=True)
    systems = []
    
    found_dirs = set()
    try:
        for entry in sorted(os.listdir(ROMS_DIR)):
            p = os.path.join(ROMS_DIR, entry)
            if os.path.isdir(p) and not entry.startswith("."):
                found_dirs.add(entry)
    except OSError:
        pass

    for code, name in SYSTEM_NAMES.items():
        if code in ("NES", "SNES", "GENESIS", "PS1"):
            continue
        code_upper = code.upper()
        matched_dir = code
        for d in found_dirs:
            if d.upper() == code_upper or f"({code_upper})" in d.upper():
                matched_dir = d
                break
        
        rom_path = os.path.join(ROMS_DIR, matched_dir)
        count = 0
        if os.path.isdir(rom_path):
            try:
                count = len([f for f in os.listdir(rom_path) if not f.startswith(".") and os.path.splitext(f)[1].lower() in VALID_EXTS])
            except OSError:
                count = 0

        systems.append({
            "code": code,
            "dir": matched_dir,
            "name": name,
            "count": count
        })
    
    known_matched = {s["dir"] for s in systems}
    for d in sorted(found_dirs):
        if d not in known_matched:
            rom_path = os.path.join(ROMS_DIR, d)
            cnt = 0
            try:
                cnt = len([f for f in os.listdir(rom_path) if not f.startswith(".") and os.path.splitext(f)[1].lower() in VALID_EXTS])
            except OSError:
                cnt = 0
            systems.append({
                "code": d,
                "dir": d,
                "name": d,
                "count": cnt
            })

    systems.sort(key=lambda s: (-1 if s["count"] > 0 else 1, s["name"]))
    return systems

def list_system_games(sys_dir):
    rom_path = os.path.join(ROMS_DIR, sys_dir)
    img_path = os.path.join(IMGS_DIR, sys_dir)
    os.makedirs(rom_path, exist_ok=True)
    os.makedirs(img_path, exist_ok=True)

    art_map = {}
    if os.path.isdir(img_path):
        try:
            for f in os.listdir(img_path):
                if not f.startswith(".") and os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                    base = os.path.splitext(f)[0].lower()
                    art_map[base] = f
        except OSError:
            pass

    games = []
    if os.path.isdir(rom_path):
        try:
            for fname in sorted(os.listdir(rom_path)):
                if fname.startswith("."):
                    continue
                full_p = os.path.join(rom_path, fname)
                if not os.path.isfile(full_p):
                    continue
                name, ext = os.path.splitext(fname)
                if ext.lower() not in VALID_EXTS:
                    continue
                
                try:
                    st = os.stat(full_p)
                    sz = st.st_size
                    mtime = st.st_mtime
                except OSError:
                    sz = 0
                    mtime = 0
                
                art_file = art_map.get(name.lower())
                has_art = bool(art_file)
                if has_art:
                    art_full_path = os.path.join(img_path, art_file)
                    try:
                        art_mtime = int(os.path.getmtime(art_full_path))
                    except OSError:
                        art_mtime = int(time.time())
                    art_url = f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(art_file)}?v={art_mtime}"
                else:
                    art_url = None

                games.append({
                    "filename": fname,
                    "name": name,
                    "ext": ext,
                    "size_str": format_size(sz),
                    "size_bytes": sz,
                    "mtime": mtime,
                    "has_art": has_art,
                    "art_name": art_file,
                    "art_url": art_url
                })
        except OSError as e:
            print(f"Error listing games for {sys_dir}: {e}")

    return games

def list_all_missing_art_games():
    """Liệt kê toàn bộ các game trên thẻ nhớ chưa có ảnh bìa (boxart)."""
    os.makedirs(ROMS_DIR, exist_ok=True)
    os.makedirs(IMGS_DIR, exist_ok=True)
    missing = []

    try:
        sys_dirs = sorted(os.listdir(ROMS_DIR))
    except Exception:
        sys_dirs = []

    for sys_d in sys_dirs:
        if sys_d.startswith("."):
            continue
        rom_p = os.path.join(ROMS_DIR, sys_d)
        if not os.path.isdir(rom_p):
            continue
        img_p = os.path.join(IMGS_DIR, sys_d)
        art_bases = set()
        if os.path.isdir(img_p):
            try:
                for f in os.listdir(img_p):
                    if not f.startswith(".") and os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                        art_bases.add(os.path.splitext(f)[0].lower())
            except Exception:
                pass

        try:
            for fname in sorted(os.listdir(rom_p)):
                if fname.startswith("."):
                    continue
                full_p = os.path.join(rom_p, fname)
                if not os.path.isfile(full_p):
                    continue
                name, ext = os.path.splitext(fname)
                if ext.lower() not in VALID_EXTS:
                    continue

                if name.lower() not in art_bases:
                    try:
                        st = os.stat(full_p)
                        sz = st.st_size
                        mtime = st.st_mtime
                    except OSError:
                        sz = 0
                        mtime = 0

                    missing.append({
                        "filename": fname,
                        "name": name,
                        "system": sys_d,
                        "system_name": SYSTEM_NAMES.get(sys_d.upper(), sys_d),
                        "ext": ext,
                        "size_str": format_size(sz),
                        "size_bytes": sz,
                        "mtime": mtime,
                        "has_art": False,
                        "art_name": None,
                        "art_url": None
                    })
        except Exception as e:
            print(f"Error scanning missing art in {sys_d}: {e}")

    return missing


class GameWebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/status":
            st = get_sd_storage()
            self.send_json({"ok": True, "storage": st})
            return

        if path == "/api/saves":
            self.send_json({
                "ok": True,
                "stats": get_saves_stats(),
                "backups": list_save_backups()
            })
            return

        if path == "/api/saves/download":
            fname = query.get("file", [""])[0]
            for b in list_save_backups():
                if b["filename"] == fname and os.path.isfile(b["filepath"]):
                    try:
                        with open(b["filepath"], "rb") as f:
                            data = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/zip")
                        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    except Exception as e:
                        print(f"Error downloading backup: {e}")
            self.send_response(404)
            self.end_headers()
            return

        if path == "/api/cheats/status":
            self.send_json({
                "ok": True,
                "status": get_cheats_status(),
                "runner": cheat_runner.get_state()
            })
            return

        if path == "/api/logs/download":
            try:
                rep_path = generate_debug_report()
                if os.path.isfile(rep_path):
                    with open(rep_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(rep_path)}"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            except Exception as e:
                print(f"Error generating debug report: {e}")
            self.send_response(404)
            self.end_headers()
            return

        if path == "/api/logs/status":
            dev_id = getattr(state, "device_id", "") or get_device_id()
            self.send_json({
                "ok": True,
                "enable_logging": getattr(state, "enable_logging", False),
                "device_id": dev_id,
                "log_size": get_log_size_str()
            })
            return

        if path == "/api/systems":
            systems = list_all_systems()
            no_art_games = list_all_missing_art_games()
            self.send_json({
                "ok": True,
                "systems": systems,
                "no_art_count": len(no_art_games)
            })
            return

        if path == "/api/games":
            sys_dir = query.get("system", [""])[0]
            if sys_dir == "__no_art__":
                games = list_all_missing_art_games()
                self.send_json({"ok": True, "system": "__no_art__", "games": games})
                return
            if not sys_dir:
                self.send_json({"ok": False, "error": "Missing system parameter"}, 400)
                return
            games = list_system_games(sys_dir)
            self.send_json({"ok": True, "system": sys_dir, "games": games})
            return

        if path.startswith("/art/"):
            parts = path.split("/", 3)
            if len(parts) >= 4:
                sys_dir = urllib.parse.unquote(parts[2])
                art_fname = urllib.parse.unquote(parts[3])
                art_full = os.path.join(IMGS_DIR, sys_dir, art_fname)
                if os.path.isfile(art_full):
                    ext = os.path.splitext(art_fname)[1].lower()
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    try:
                        with open(art_full, "rb") as f:
                            data = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", mime)
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Cache-Control", "no-cache, must-revalidate")
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    except Exception as e:
                        print(f"Error serving art: {e}")
            self.send_response(404)
            self.end_headers()
            return

        if path == "/api/scrape/search":
            sys_code = query.get("system", [""])[0].upper()
            q_name = query.get("query", [""])[0].strip()
            fast_mode = query.get("fast", ["0"])[0] in ("1", "true", "yes")
            if not q_name:
                self.send_json({"ok": False, "error": "Query required"}, 400)
                return

            candidates = []
            seen_urls = set()

            # 1. Tìm trong SQLite Catalog DB (ảnh bìa chất lượng cao / Việt hóa) (~1ms)
            db_results = search_catalog_db(sys_code, q_name, max_results=6)
            for item in db_results:
                if item["url"] not in seen_urls:
                    candidates.append(item)
                    seen_urls.add(item["url"])

            # 2. Tìm trong Libretro Thumbnails CDN chính thức (~5ms)
            allow_fetch = len(candidates) < 6
            libretro_results = search_libretro_boxarts(sys_code, q_name, max_results=8, allow_fetch=allow_fetch)
            for item in libretro_results:
                if item["url"] not in seen_urls:
                    candidates.append(item)
                    seen_urls.add(item["url"])

            # 3. Tìm kiếm Web Images (Bing) nếu không bật fast_mode hoặc DB/Libretro chưa có ảnh
            if not fast_mode or len(candidates) == 0:
                web_q = f"{q_name} {sys_code} boxart box art cover"
                web_results = search_web_images(web_q, max_results=8)
                for item in web_results:
                    if item["url"] not in seen_urls:
                        candidates.append(item)
                        seen_urls.add(item["url"])

            self.send_json({
                "ok": True,
                "system": sys_code,
                "query": q_name,
                "candidates": candidates
            })
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        content_len = int(self.headers.get("Content-Length", 0))

        if path == "/api/saves/backup":
            try:
                note = ""
                if content_len > 0:
                    try:
                        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                        note = payload.get("note", "")
                    except Exception:
                        pass
                ok, res, st = create_save_backup(note=note)
                if ok:
                    self.send_json({"ok": True, "message": "Đã tạo bản sao lưu thành công!", "backup": st})
                else:
                    self.send_json({"ok": False, "error": res}, 500)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/saves/restore":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                fname = payload.get("filename", "")
                found = None
                for b in list_save_backups():
                    if b["filename"] == fname:
                        found = b["filepath"]
                        break
                if not found:
                    self.send_json({"ok": False, "error": "Không tìm thấy file sao lưu"}, 404)
                    return
                ok, cnt, err = restore_save_backup(found)
                if ok:
                    self.send_json({"ok": True, "message": f"Khôi phục thành công {cnt} files save!"})
                else:
                    self.send_json({"ok": False, "error": err}, 500)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/saves/delete":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                fname = payload.get("filename", "")
                found = None
                for b in list_save_backups():
                    if b["filename"] == fname:
                        found = b["filepath"]
                        break
                if found:
                    delete_save_backup(found)
                    self.send_json({"ok": True, "message": "Đã xóa bản sao lưu!"})
                else:
                    self.send_json({"ok": False, "error": "File không tồn tại"}, 404)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/cheats/download":
            if cheat_runner.is_running():
                self.send_json({"ok": True, "message": "Đang tải kho Cheat..."})
            else:
                cheat_runner.start()
                self.send_json({"ok": True, "message": "Đã bắt đầu tải kho Cheat Libretro!"})
            return

        if path == "/api/cheats/stop":
            cheat_runner.request_stop()
            self.send_json({"ok": True, "message": "Đã gửi lệnh dừng tải!"})
            return

        if path == "/api/logs/send-telegram":
            try:
                payload = {}
                if content_len > 0:
                    try:
                        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                    except Exception:
                        payload = {}
                user_note = payload.get("note", "").strip() or "Gửi từ RetroHub Web Manager"
                ok, res = upload_log_to_telegram(note=user_note)
                if ok:
                    self.send_json({"ok": True, "message": "Đã gửi nhật ký thành công vào Telegram của tác giả!"})
                else:
                    self.send_json({"ok": False, "error": str(res)}, 500)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/logs/toggle":
            state.enable_logging = not getattr(state, "enable_logging", False)
            state.save_settings()
            self.send_json({
                "ok": True,
                "enable_logging": state.enable_logging,
                "message": "Đã BẬT ghi nhật ký" if state.enable_logging else "Đã TẮT ghi nhật ký"
            })
            return

        if path == "/api/logs/clear":
            clear_log()
            self.send_json({
                "ok": True,
                "log_size": get_log_size_str(),
                "message": "Đã làm sạch toàn bộ nhật ký!"
            })
            return

        if path == "/api/rename":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                sys_dir = payload.get("system", "").strip()
                old_f = payload.get("old_filename", "").strip()
                new_f = payload.get("new_filename", "").strip()
                
                if not sys_dir or not old_f or not new_f:
                    self.send_json({"ok": False, "error": "Thiếu thông tin tham số"}, 400)
                    return

                old_rom_path = os.path.join(ROMS_DIR, sys_dir, old_f)
                new_rom_path = os.path.join(ROMS_DIR, sys_dir, new_f)

                if not os.path.isfile(old_rom_path):
                    self.send_json({"ok": False, "error": f"Không tìm thấy file {old_f}"}, 404)
                    return
                if os.path.exists(new_rom_path) and old_rom_path != new_rom_path:
                    self.send_json({"ok": False, "error": f"Tên mới {new_f} đã tồn tại!"}, 400)
                    return

                os.rename(old_rom_path, new_rom_path)

                old_base = os.path.splitext(old_f)[0]
                new_base = os.path.splitext(new_f)[0]
                renamed_art = False
                img_dir = os.path.join(IMGS_DIR, sys_dir)
                if os.path.isdir(img_dir):
                    for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                        old_art = os.path.join(img_dir, old_base + ext)
                        if os.path.isfile(old_art):
                            new_art = os.path.join(img_dir, new_base + ext)
                            try:
                                os.rename(old_art, new_art)
                                renamed_art = True
                            except Exception as e:
                                print(f"Error renaming art: {e}")
                            break

                self.send_json({
                    "ok": True,
                    "message": f"Đã đổi tên thành công: {new_f}" + (" (kèm ảnh bìa)" if renamed_art else ""),
                    "renamed_art": renamed_art
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/move":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                from_sys = payload.get("from_system", "").strip()
                to_sys = payload.get("to_system", "").strip()
                fname = payload.get("filename", "").strip()

                if not from_sys or not to_sys or not fname:
                    self.send_json({"ok": False, "error": "Thiếu thông tin hệ máy hoặc tệp"}, 400)
                    return

                src_rom = os.path.join(ROMS_DIR, from_sys, fname)
                dst_dir = os.path.join(ROMS_DIR, to_sys)
                os.makedirs(dst_dir, exist_ok=True)
                dst_rom = os.path.join(dst_dir, fname)

                if not os.path.isfile(src_rom):
                    self.send_json({"ok": False, "error": f"Không tìm thấy file nguồn {fname}"}, 404)
                    return
                if os.path.exists(dst_rom):
                    self.send_json({"ok": False, "error": f"File {fname} đã tồn tại ở hệ máy đích!"}, 400)
                    return

                shutil.move(src_rom, dst_rom)

                moved_art = False
                base = os.path.splitext(fname)[0]
                src_img_dir = os.path.join(IMGS_DIR, from_sys)
                dst_img_dir = os.path.join(IMGS_DIR, to_sys)
                os.makedirs(dst_img_dir, exist_ok=True)
                for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                    src_art = os.path.join(src_img_dir, base + ext)
                    if os.path.isfile(src_art):
                        dst_art = os.path.join(dst_img_dir, base + ext)
                        try:
                            shutil.move(src_art, dst_art)
                            moved_art = True
                        except Exception as e:
                            print(f"Error moving art: {e}")
                        break

                self.send_json({
                    "ok": True,
                    "message": f"Đã chuyển {fname} sang {to_sys}" + (" (kèm ảnh bìa)" if moved_art else ""),
                    "moved_art": moved_art
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/delete":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                sys_dir = payload.get("system", "").strip()
                fname = payload.get("filename", "").strip()
                del_art = payload.get("delete_art", True)

                rom_p = os.path.join(ROMS_DIR, sys_dir, fname)
                if os.path.isfile(rom_p):
                    os.remove(rom_p)
                
                if del_art:
                    base = os.path.splitext(fname)[0]
                    img_d = os.path.join(IMGS_DIR, sys_dir)
                    for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                        art_p = os.path.join(img_d, base + ext)
                        if os.path.isfile(art_p):
                            try:
                                os.remove(art_p)
                            except Exception:
                                pass

                self.send_json({"ok": True, "message": f"Đã xóa {fname}"})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/scrape/auto":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                sys_dir = payload.get("system", "").strip()
                fname = payload.get("filename", "").strip()
                query_str = payload.get("query", "").strip()
                fast_only = payload.get("fast", True)

                if not sys_dir or not fname:
                    self.send_json({"ok": False, "error": "Thiếu dữ liệu cào ảnh (system hoặc filename)"}, 400)
                    return

                if not query_str:
                    query_str = clean_rom_title(fname)

                best_url, src_type = find_best_boxart(sys_dir, query_str, fast_only=fast_only)
                if not best_url:
                    self.send_json({"ok": False, "error": "Không tìm thấy ảnh bìa phù hợp", "not_found": True}, 404)
                    return

                base_name = os.path.splitext(fname)[0]
                target_img_dir = os.path.join(IMGS_DIR, sys_dir)
                os.makedirs(target_img_dir, exist_ok=True)
                target_art = os.path.join(target_img_dir, base_name + ".png")

                # Xóa các file ảnh định dạng cũ (.jpg, .jpeg, .webp, .bmp) nếu có
                for old_ext in (".jpg", ".jpeg", ".webp", ".bmp"):
                    old_f = os.path.join(target_img_dir, base_name + old_ext)
                    if os.path.isfile(old_f):
                        try:
                            os.remove(old_f)
                        except Exception:
                            pass

                success, err_msg = download_image_to_file(best_url, target_art, timeout=12)
                if success:
                    try:
                        os.utime(target_art, None)
                    except Exception:
                        pass
                    now_ts = int(time.time())
                    self.send_json({
                        "ok": True,
                        "source": src_type,
                        "image_url": best_url,
                        "art_url": f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?v={now_ts}"
                    })
                    return
                else:
                    self.send_json({"ok": False, "error": f"Lỗi tải ảnh: {err_msg}"}, 500)
                    return
            except Exception as e:
                self.send_json({"ok": False, "error": f"Lỗi xử lý cào ảnh tự động: {e}"}, 500)
            return

        if path == "/api/scrape/apply":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                sys_dir = payload.get("system", "").strip()
                fname = payload.get("filename", "").strip()
                img_url = payload.get("image_url", "").strip()

                if not sys_dir or not fname or not img_url:
                    self.send_json({"ok": False, "error": "Thiếu dữ liệu cào ảnh"}, 400)
                    return

                if img_url.startswith("//"):
                    img_url = "https:" + img_url

                base_name = os.path.splitext(fname)[0]
                target_img_dir = os.path.join(IMGS_DIR, sys_dir)
                os.makedirs(target_img_dir, exist_ok=True)
                target_art = os.path.join(target_img_dir, base_name + ".png")

                # Xóa các file ảnh định dạng cũ (.jpg, .jpeg, .webp, .bmp) nếu có
                for old_ext in (".jpg", ".jpeg", ".webp", ".bmp"):
                    old_f = os.path.join(target_img_dir, base_name + old_ext)
                    if os.path.isfile(old_f):
                        try:
                            os.remove(old_f)
                        except Exception:
                            pass

                success, err_msg = download_image_to_file(img_url, target_art, timeout=15)
                if success:
                    try:
                        os.utime(target_art, None)
                    except Exception:
                        pass
                    now_ts = int(time.time())
                    self.send_json({
                        "ok": True,
                        "message": f"Đã tải và gán ảnh bìa thành công cho {fname}!",
                        "art_url": f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?v={now_ts}"
                    })
                    return
                else:
                    self.send_json({"ok": False, "error": f"Lỗi tải ảnh: {err_msg}"}, 500)
                    return
            except Exception as e:
                self.send_json({"ok": False, "error": f"Lỗi tải ảnh: {e}"}, 500)
            return

        if path == "/api/upload_art":
            sys_dir = query.get("system", [""])[0]
            fname = query.get("filename", [""])[0]
            if not sys_dir or not fname:
                self.send_json({"ok": False, "error": "Missing system or filename"}, 400)
                return

            base_name = os.path.splitext(fname)[0]
            target_img_dir = os.path.join(IMGS_DIR, sys_dir)
            os.makedirs(target_img_dir, exist_ok=True)
            target_art = os.path.join(target_img_dir, base_name + ".png")

            # Xóa các file ảnh định dạng cũ (.jpg, .jpeg, .webp, .bmp) nếu có
            for old_ext in (".jpg", ".jpeg", ".webp", ".bmp"):
                old_f = os.path.join(target_img_dir, base_name + old_ext)
                if os.path.isfile(old_f):
                    try:
                        os.remove(old_f)
                    except Exception:
                        pass

            try:
                data = self.rfile.read(content_len)
                with open(target_art, "wb") as f:
                    f.write(data)
                try:
                    os.utime(target_art, None)
                except Exception:
                    pass
                now_ts = int(time.time())
                self.send_json({
                    "ok": True,
                    "message": "Đã tải lên ảnh bìa thành công!",
                    "art_url": f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?v={now_ts}"
                })
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/upload_rom":
            sys_dir = query.get("system", [""])[0]
            fname = query.get("filename", [""])[0]
            if not sys_dir or not fname:
                self.send_json({"ok": False, "error": "Missing system or filename"}, 400)
                return

            target_rom_dir = os.path.join(ROMS_DIR, sys_dir)
            os.makedirs(target_rom_dir, exist_ok=True)
            target_rom = os.path.join(target_rom_dir, fname)

            try:
                chunk_size = 65536
                remaining = content_len
                with open(target_rom, "wb") as f:
                    while remaining > 0:
                        to_read = min(chunk_size, remaining)
                        chunk = self.rfile.read(to_read)
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)
                self.send_json({"ok": True, "message": f"Đã tải lên game {fname} thành công!"})
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        self.send_response(404)
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RetroHub - Web Game Manager</title>
    <style>
        :root {
            --bg-main: #0b0f19;
            --bg-card: #151d2f;
            --bg-card-hover: #1e293b;
            --bg-sidebar: #0f172a;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --accent: #00d2ff;
            --accent-green: #10b981;
            --danger: #ef4444;
            --danger-hover: #dc2626;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --border: #334155;
            --radius: 10px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); display: flex; flex-direction: column; min-height: 100vh; }
        
        header {
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .logo-box { display: flex; align-items: center; gap: 12px; }
        .logo-box h1 { font-size: 20px; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .badge-device { background: #1e293b; color: #38bdf8; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid #0284c7; }
        .header-stats { display: flex; align-items: center; gap: 16px; font-size: 13px; color: var(--text-sub); }
        .stat-badge { background: #1e293b; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); }
        .stat-badge strong { color: #38bdf8; }

        .app-container { display: flex; flex: 1; overflow: hidden; }
        
        aside {
            width: 280px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
        .sidebar-header { padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-sub); letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
        .sys-item {
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            border-left: 3px solid transparent;
            transition: all 0.15s ease;
        }
        .sys-item:hover { background: #1e293b; }
        .sys-item.active { background: #1e293b; border-left-color: var(--primary); font-weight: 600; color: #38bdf8; }
        .sys-item .count { background: #334155; color: #cbd5e1; font-size: 11px; padding: 2px 7px; border-radius: 10px; font-weight: 600; }
        .sys-item.active .count { background: var(--primary); color: #fff; }

        main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 20px 24px; }
        
        .toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; gap: 16px; flex-wrap: wrap; }
        .search-box { position: relative; flex: 1; max-width: 400px; }
        .search-box input {
            width: 100%;
            background: #1e293b;
            border: 1px solid var(--border);
            padding: 10px 14px 10px 36px;
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            outline: none;
        }
        .search-box input:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(59,130,246,0.25); }
        .search-icon { position: absolute; left: 12px; top: 12px; color: var(--text-sub); }

        .btn {
            background: var(--primary);
            color: #fff;
            border: none;
            padding: 9px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: background 0.15s;
        }
        .btn:hover { background: var(--primary-hover); }
        .btn-green { background: var(--accent-green); }
        .btn-green:hover { background: #059669; }
        .btn-danger { background: var(--danger); }
        .btn-danger:hover { background: var(--danger-hover); }
        .btn-secondary { background: #334155; color: #e2e8f0; }
        .btn-secondary:hover { background: #475569; }
        .btn-sm { padding: 6px 10px; font-size: 12px; border-radius: 6px; }

        .games-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 16px;
        }
        .game-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.15s, border-color 0.15s;
        }
        .game-card:hover { transform: translateY(-3px); border-color: #475569; background: var(--bg-card-hover); }
        
        .art-box {
            width: 100%;
            height: 200px;
            background: #090d16;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-bottom: 1px solid rgba(51, 65, 85, 0.4);
            cursor: pointer;
        }
        .art-img {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            margin: auto;
            padding: 6px;
            border-radius: 4px;
            transition: transform 0.2s ease;
        }
        .art-box:hover .art-img {
            transform: scale(1.03);
        }
        .art-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            color: #64748b;
            text-align: center;
            user-select: none;
        }
        .art-sys-svg {
            width: 54px;
            height: 54px;
            filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.4));
            transition: transform 0.2s, filter 0.2s;
        }
        .art-box:hover .art-sys-svg {
            transform: scale(1.08);
            filter: drop-shadow(0 6px 14px rgba(56, 189, 248, 0.25));
        }
        .btn-action-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        .btn-action-icon svg {
            flex-shrink: 0;
            display: inline-block;
            vertical-align: middle;
        }
        .art-btn-overlay {
            position: absolute;
            inset: 0;
            background: rgba(11, 15, 25, 0.75);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            opacity: 0;
            transition: opacity 0.15s;
        }
        .art-box:hover .art-btn-overlay { opacity: 1; }

        .game-info { padding: 12px; display: flex; flex-direction: column; flex: 1; justify-content: space-between; gap: 8px; }
        .game-title { font-size: 13px; font-weight: 600; line-height: 1.35; color: #f1f5f9; word-break: break-word; }
        .game-meta { display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: var(--text-sub); }
        .game-actions { display: flex; gap: 6px; margin-top: 6px; border-top: 1px solid #1e293b; padding-top: 8px; }

        .modal-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 200;
            padding: 16px;
        }
        .modal-box {
            background: #1e293b;
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 100%;
            max-width: 540px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }
        .modal-header { display: flex; align-items: center; justify-content: space-between; }
        .modal-header h3 { font-size: 17px; font-weight: 700; color: #38bdf8; }
        .modal-close { background: none; border: none; font-size: 20px; color: var(--text-sub); cursor: pointer; }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        .form-group label { font-size: 12px; font-weight: 600; color: var(--text-sub); }
        .form-group input, .form-group select {
            background: #0f172a;
            border: 1px solid var(--border);
            color: #fff;
            padding: 10px 12px;
            border-radius: 6px;
            font-size: 14px;
            outline: none;
        }
        .form-group input:focus, .form-group select:focus { border-color: var(--primary); }

        .scrape-candidates {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 10px;
            max-height: 310px;
            overflow-y: auto;
            padding: 4px;
        }
        .scrape-card {
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 6px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            background: #0f172a;
            cursor: pointer;
            transition: all 0.15s ease;
            position: relative;
        }
        .scrape-card:hover {
            border-color: var(--primary);
            background: #1e293b;
            transform: translateY(-2px);
        }
        .scrape-img {
            width: 100%;
            height: 125px;
            object-fit: contain;
            background: #020617;
            border-radius: 4px;
        }
        .scrape-title {
            font-size: 11px;
            font-weight: 500;
            text-align: center;
            color: #e2e8f0;
            width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .scrape-tag {
            font-size: 10px;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            padding: 2px 6px;
            border-radius: 4px;
            text-align: center;
        }

        .sys-item-special {
            background: rgba(245, 158, 11, 0.08);
            border-left-color: #f59e0b !important;
            font-weight: 600;
        }
        .sys-item-special:hover {
            background: rgba(245, 158, 11, 0.16);
        }
        .sys-item-special.active {
            background: rgba(245, 158, 11, 0.25) !important;
            border-left-color: #f59e0b !important;
        }
        .count-warn {
            background: rgba(245, 158, 11, 0.25) !important;
            color: #fbbf24 !important;
            font-weight: 700;
        }
        .btn-batch {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #fff;
            font-weight: 600;
            border: none;
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
        }
        .btn-batch:hover {
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
        }
        .badge-sys-pill {
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
            display: inline-block;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .progress-bar-bg {
            width: 100%;
            height: 10px;
            background: #0b0f19;
            border-radius: 5px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #f59e0b 0%, #10b981 100%);
            width: 0%;
            transition: width 0.2s ease;
        }
        .batch-log-item {
            font-size: 11px;
            padding: 5px 8px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .game-card.is-scraping {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 14px rgba(56, 189, 248, 0.4);
            transform: translateY(-2px);
        }
        .game-card.is-success {
            border-color: #10b981 !important;
            box-shadow: 0 0 14px rgba(16, 185, 129, 0.4);
        }
        @keyframes pulseScrape {
            0% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.18); opacity: 1; }
            100% { transform: scale(1); opacity: 0.8; }
        }
        .scrape-spinner {
            display: inline-block;
            animation: pulseScrape 0.9s infinite;
        }

        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            color: #fff;
            border: 1px solid var(--primary);
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            font-size: 13px;
            font-weight: 600;
            display: none;
            z-index: 300;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

        @media (max-width: 768px) {
            .app-container { flex-direction: column; }
            aside { width: 100%; height: 60px; flex-direction: row; border-right: none; border-bottom: 1px solid var(--border); }
            .sys-item { border-left: none; border-bottom: 3px solid transparent; white-space: nowrap; }
            .sys-item.active { border-bottom-color: var(--primary); border-left-color: transparent; }
            .sidebar-header { display: none; }
            .scrape-candidates { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-box">
            <h1>RetroHub</h1>
            <span class="badge-device">Web Manager</span>
        </div>
        <div class="header-stats">
            <div class="stat-badge" id="storage-stat">Bộ nhớ: <strong>Đang đọc...</strong></div>
            <button class="btn btn-sm btn-secondary" onclick="openSavesCheatsModal('saves')">Save & Cheats</button>
            <button class="btn btn-sm btn-secondary" onclick="loadSystems(true)">Nạp lại</button>
        </div>
    </header>

    <div class="app-container">
        <aside id="sidebar">
            <div class="sidebar-header">Hệ máy trên thẻ nhớ</div>
            <div id="systems-list"></div>
        </aside>

        <main>
            <div class="toolbar">
                <div class="search-box">
                    <span class="search-icon"></span>
                    <input type="text" id="search-input" placeholder="Tìm game trong hệ..." oninput="filterGames()">
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <input type="file" id="rom-file-input-direct" multiple style="display:none" onchange="handleDirectRomFiles(event)">
                    <button id="btn-batch-scrape-top" class="btn btn-batch" style="display:none;" onclick="toggleDirectBatchScrape()">Cào toàn bộ ảnh</button>
                    <button class="btn btn-green" onclick="handleUploadRomClick()">+ Tải ROM lên</button>
                </div>
            </div>

            <div id="batch-inline-bar" style="display:none; background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; align-items: center; justify-content: space-between; gap: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <div style="flex:1; min-width:0;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:6px;">
                        <span id="batch-inline-status" style="color:#38bdf8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Đang tự động cào ảnh...</span>
                        <span id="batch-inline-pct" style="color:#10b981; font-weight:700;">0%</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 8px;">
                        <div id="batch-inline-fill" class="progress-bar-fill" style="width:0%;"></div>
                    </div>
                </div>
                <button class="btn btn-sm btn-secondary" onclick="stopDirectBatchScrape()">Dừng cào</button>
            </div>

            <div id="games-container" class="games-grid"></div>
            <div id="empty-state" style="display:none; text-align:center; padding: 60px 20px; color: var(--text-sub);">
                <div style="font-size: 16px; margin-bottom: 12px; font-weight: 600;">(Trống)</div>
                <p>Không có game nào trong hệ máy này hoặc chưa tìm thấy tệp phù hợp.</p>
            </div>
        </main>
    </div>

    <div class="modal-backdrop" id="modal-rename">
        <div class="modal-box">
            <div class="modal-header">
                <h3>Đổi tên game</h3>
                <button class="modal-close" onclick="closeModal('modal-rename')">&times;</button>
            </div>
            <div class="form-group">
                <label>Tên file cũ</label>
                <input type="text" id="rename-old" disabled>
            </div>
            <div class="form-group">
                <label>Tên file mới (Tự động đổi cả file ảnh bìa)</label>
                <input type="text" id="rename-new">
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-rename')">Hủy</button>
                <button class="btn" onclick="submitRename()">Lưu tên mới</button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="modal-move">
        <div class="modal-box">
            <div class="modal-header">
                <h3>Chuyển hệ máy</h3>
                <button class="modal-close" onclick="closeModal('modal-move')">&times;</button>
            </div>
            <div class="form-group">
                <label>Game cần chuyển</label>
                <input type="text" id="move-game" disabled>
            </div>
            <div class="form-group">
                <label>Chọn hệ máy đích</label>
                <select id="move-target-sys"></select>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-move')">Hủy</button>
                <button class="btn" onclick="submitMove()">Xác nhận chuyển</button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="modal-scrape">
        <div class="modal-box" style="max-width: 680px; width: 92vw;">
            <div class="modal-header">
                <h3>Cào ảnh bìa (Boxart)</h3>
                <button class="modal-close" onclick="closeModal('modal-scrape')">&times;</button>
            </div>
            <div style="display: flex; gap: 8px;">
                <input type="text" id="scrape-query" style="flex:1; background:#0f172a; border:1px solid var(--border); color:#fff; padding:8px 12px; border-radius:6px; font-size:14px;" placeholder="Nhập từ khóa tìm kiếm ảnh..." onkeydown="if(event.key==='Enter') executeScrapeSearch()">
                <button class="btn btn-sm" onclick="executeScrapeSearch()">Tìm ảnh</button>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-sub); margin-top: 2px;">
                <span>Nguồn: RetroHub Catalog DB & Libretro Thumbnails CDN</span>
                <button type="button" class="btn btn-secondary" style="padding: 2px 8px; font-size: 11px; cursor: pointer;" onclick="openGoogleImageSearch()">Mở Google Images</button>
            </div>
            
            <div id="scrape-results" class="scrape-candidates"></div>

            <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed var(--border); border-radius: 6px; padding: 10px; margin-top: 6px;">
                <div style="font-size: 11px; color: var(--text-sub); margin-bottom: 6px; font-weight: 600;">Dán ảnh trực tiếp từ Clipboard (Ctrl+V) hoặc dán link:</div>
                <div style="display: flex; gap: 8px;">
                    <input type="text" id="scrape-direct-url" style="flex:1; background:#0b0f19; border:1px solid var(--border); color:#fff; padding:6px 10px; border-radius:6px; font-size:12px;" placeholder="Nhấn Ctrl+V để dán ảnh đã copy, hoặc dán link https://..." onkeydown="if(event.key==='Enter') submitDirectArtUrl()">
                    <button class="btn btn-sm btn-green" onclick="submitDirectArtUrl()">Gán link</button>
                    <button class="btn btn-sm btn-secondary" onclick="pasteAndApplyArt()" title="Dán ảnh hoặc link từ Clipboard">Dán từ Clipboard</button>
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 5px;">
                    <em>Bạn có thể click chuột phải vào bất kỳ ảnh nào chọn <strong>"Sao chép hình ảnh" (Copy Image)</strong> hoặc chụp màn hình rồi bấm <strong>Ctrl+V</strong> vào đây để gán ngay!</em>
                </div>
            </div>

            <div style="border-top:1px solid var(--border); padding-top:12px; display:flex; justify-content:space-between; align-items:center;">
                <label class="btn btn-sm btn-secondary" style="margin:0; cursor:pointer;">
                    Tải ảnh từ máy
                    <input type="file" id="art-file-input" accept="image/*" style="display:none" onchange="uploadCustomArt(event)">
                </label>
                <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-scrape')">Đóng</button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="modal-select-upload-sys">
        <div class="modal-box" style="max-width: 440px; width: 92vw;">
            <div class="modal-header">
                <h3>Chọn hệ máy để tải ROM</h3>
                <button class="modal-close" onclick="closeModal('modal-select-upload-sys')">&times;</button>
            </div>
            <div class="form-group">
                <label>Bạn đang ở tab tổng hợp, vui lòng chọn hệ máy đích:</label>
                <select id="modal-upload-sys-select"></select>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-select-upload-sys')">Hủy</button>
                <button class="btn btn-green" onclick="confirmSystemAndBrowseFiles()">Chọn tệp ROM -></button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="modal-upload-progress">
        <div class="modal-box" style="max-width: 560px; width: 92vw;">
            <div class="modal-header">
                <h3 id="upload-prog-title">Đang tải ROM lên thiết bị</h3>
                <button class="modal-close" onclick="cancelOrCloseUpload()">&times;</button>
            </div>

            <div style="font-size: 13px; color: var(--text-sub); margin-bottom: 12px;" id="upload-prog-sub">
                Hệ máy đích: <strong id="upload-target-name" style="color:#38bdf8;"></strong>
            </div>

            <div style="background: #0f172a; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:6px;">
                    <span id="upload-current-fname" style="color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:70%;">Chuẩn bị tải lên...</span>
                    <span id="upload-current-pct" style="color:#38bdf8; font-weight:700;">0%</span>
                </div>
                <div class="progress-bar-bg" style="height: 12px; margin-bottom: 6px;">
                    <div id="upload-file-progress-bar" class="progress-bar-fill" style="width:0%;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-sub);">
                    <span id="upload-file-size-info">0 / 0 MB</span>
                    <span id="upload-batch-count-info">Tệp 1 / 1</span>
                </div>
            </div>

            <div id="upload-overall-box" style="margin-bottom: 12px; display:none;">
                <div style="display:flex; justify-content:space-between; font-size:11px; font-weight:600; margin-bottom:4px;">
                    <span style="color:var(--text-sub);">Tổng tiến độ các tệp:</span>
                    <span id="upload-overall-pct" style="color:#10b981; font-weight:700;">0%</span>
                </div>
                <div class="progress-bar-bg" style="height: 6px;">
                    <div id="upload-overall-progress-bar" class="progress-bar-fill" style="width:0%; background: #10b981;"></div>
                </div>
            </div>

            <div style="font-size: 12px; font-weight: 600; margin-bottom: 4px;">Danh sách tệp tải lên:</div>
            <div id="upload-file-list" style="max-height: 160px; overflow-y: auto; background: #0b0f19; border: 1px solid var(--border); border-radius: 6px; padding: 4px;"></div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px;">
                <div style="font-size: 11px; color: #94a3b8;" id="upload-status-footer">
                    Vui lòng không tắt trình duyệt khi đang tải file lớn.
                </div>
                <button class="btn btn-secondary" id="btn-upload-cancel" onclick="cancelOrCloseUpload()">Hủy bỏ</button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="modal-preview-art" onclick="if(event.target===this) closeModal('modal-preview-art')">
        <div class="modal-box" style="max-width: 600px; width: auto; max-height: 92vh; padding: 14px; background: rgba(15, 23, 42, 0.98); border: 1px solid var(--border);">
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 8px;">
                <h4 id="preview-art-title" style="font-size: 13px; font-weight:600; color: #f1f5f9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 85%;">Boxart</h4>
                <button class="modal-close" onclick="closeModal('modal-preview-art')">&times;</button>
            </div>
            <div style="display: flex; align-items: center; justify-content: center; max-height: 75vh; overflow: hidden; border-radius: 6px; background: #070a12; padding: 4px;">
                <img id="preview-art-img" src="" alt="Full Boxart" style="max-width: 100%; max-height: 70vh; object-fit: contain; border-radius: 4px;">
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 10px;">
                <a id="preview-art-link" href="" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 11px;">Mở ảnh gốc trong tab mới ↗</a>
                <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-preview-art')">Đóng</button>
            </div>
        </div>
    </div>

    <!-- Modal Quản lý Save Game & Cheat Code -->
    <div class="modal-backdrop" id="modal-saves-cheats">
        <div class="modal-box" style="max-width: 720px; width: 92vw;">
            <div class="modal-header">
                <h3>Quản lý Save Game & Kho Cheat Code</h3>
                <button class="modal-close" onclick="closeModal('modal-saves-cheats')">&times;</button>
            </div>

            <!-- Tabs -->
            <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 16px; padding-bottom: 8px;">
                <button id="tab-btn-saves" class="btn btn-sm" onclick="switchSavesCheatsTab('saves')">Sao lưu & Khôi phục Save</button>
                <button id="tab-btn-cheats" class="btn btn-sm btn-secondary" onclick="switchSavesCheatsTab('cheats')">Kho Cheat Code (Libretro)</button>
                <button id="tab-btn-logs" class="btn btn-sm btn-secondary" onclick="switchSavesCheatsTab('logs')">Gửi Log & Chẩn đoán</button>
            </div>

            <!-- Tab 1: Saves -->
            <div id="tab-content-saves">
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 16px;">
                    <div>
                        <div style="font-size: 13px; font-weight: 700; color: #fff;">File Save trên thẻ nhớ</div>
                        <div style="font-size: 11px; color: var(--text-sub); margin-top: 2px;" id="saves-summary-text">Đang quét save...</div>
                    </div>
                    <button class="btn btn-sm btn-green" onclick="createSaveBackupWeb()">+ Tạo bản sao lưu (.zip)</button>
                </div>

                <div style="font-size: 12px; font-weight: 700; margin-bottom: 8px; color: #38bdf8;">Các bản sao lưu đã tạo:</div>
                <div id="backups-list-table" style="max-height: 240px; overflow-y: auto; background: #0b0f19; border: 1px solid var(--border); border-radius: 8px; padding: 6px;"></div>
            </div>

            <!-- Tab 2: Cheats -->
            <div id="tab-content-cheats" style="display: none;">
                <div style="background: #0f172a; padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 14px; font-weight: 700; color: #fff;">Kho Cheat Code Libretro Official</div>
                            <div style="font-size: 12px; color: #38bdf8; margin-top: 3px;" id="cheats-status-text">Đang kiểm tra trạng thái...</div>
                        </div>
                        <button id="btn-cheats-action" class="btn btn-sm btn-batch" onclick="startCheatsDownloadWeb()">Tải trọn bộ Cheat (~37MB)</button>
                    </div>

                    <div id="cheats-progress-box" style="display:none; margin-top: 14px;">
                        <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:6px;">
                            <span id="cheats-prog-status" style="color:#38bdf8;">Đang tải gói Cheat...</span>
                            <span id="cheats-prog-pct" style="color:#10b981; font-weight:700;">0%</span>
                        </div>
                        <div class="progress-bar-bg" style="height: 10px; margin-bottom: 8px;">
                            <div id="cheats-prog-fill" class="progress-bar-fill" style="width:0%;"></div>
                        </div>
                        <div style="display: flex; justify-content: flex-end;">
                            <button class="btn btn-sm btn-secondary" onclick="stopCheatsDownloadWeb()">Dừng tải</button>
                        </div>
                    </div>
                </div>

                <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed var(--border); border-radius: 8px; padding: 12px;">
                    <div style="font-size: 12px; font-weight: 700; color: #fbbf24; margin-bottom: 6px;">Hướng dẫn bật Cheat khi đang chơi game:</div>
                    <ul style="font-size: 11px; color: #cbd5e1; line-height: 1.8; margin-left: 20px;">
                        <li>Khi đang trong game, bấm nút <strong>Menu</strong> (hoặc tổ hợp <strong>Select + X</strong>) để mở Quick Menu của RetroArch.</li>
                        <li>Vào mục <strong>Cheats</strong> -> Chọn <strong>Load Cheat File (Replace)</strong>.</li>
                        <li>Chọn hệ máy tương ứng và chọn tệp Cheat của game đang chơi.</li>
                        <li>Bật <em>(Enabled)</em> các mã muốn dùng (Bất tử máu, Max Tiền, Đi xuyên tường...) rồi chọn <strong>Apply Changes</strong>.</li>
                    </ul>
                </div>
            </div>

            <!-- Tab 3: Logs -->
            <div id="tab-content-logs" style="display: none;">
                <div style="background: #0f172a; padding: 14px 16px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <div style="font-size: 14px; font-weight: 700; color: #38bdf8;">Nhật ký & Chẩn đoán Hệ thống</div>
                            <div style="font-size: 11px; color: var(--text-sub); margin-top: 2px;">Tự động thu thập thông số phần cứng & lỗi crash để hỗ trợ kỹ thuật</div>
                        </div>
                        <div style="background: #1e293b; border: 1px solid #0284c7; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; color: #38bdf8;">
                            Mã máy: <span id="web-log-device-id" style="color: #34d399;">...</span>
                        </div>
                    </div>

                    <!-- Toggle & Clear Section -->
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #0b0f19; padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border); margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <div style="font-size: 12px; font-weight: 600; color: #fff;">
                                Trạng thái ghi log: <span id="web-log-status-badge" style="color: #10b981; font-weight: 700;">ĐANG BẬT</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-sub); margin-top: 2px;">
                                Dung lượng tệp log: <span id="web-log-size" style="color: #f59e0b; font-weight: 600;">0 KB</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button id="btn-toggle-log-web" class="btn btn-sm btn-secondary" onclick="toggleLoggingWeb()">Tắt ghi log</button>
                            <button id="btn-clear-log-web" class="btn btn-sm btn-secondary" style="color: #f87171;" onclick="clearLogWeb()">Làm sạch log</button>
                        </div>
                    </div>

                    <div style="margin-bottom: 12px;">
                        <label style="font-size: 12px; font-weight: 600; color: #94a3b8; display: block; margin-bottom: 4px;">Ghi chú sự cố bạn đang gặp phải (tùy chọn):</label>
                        <input type="text" id="log-user-note" placeholder="Ví dụ: Game PS1 không có âm thanh, hoặc lỗi văng game..." style="width: 100%; padding: 8px 12px; background: #0b0f19; border: 1px solid var(--border); border-radius: 6px; color: #fff; font-size: 12px; outline: none; box-sizing: border-box;">
                    </div>

                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <button id="btn-send-log-tg" class="btn btn-sm btn-batch" onclick="sendLogTelegramWeb()">Gửi Log vào Telegram tác giả</button>
                        <a href="/api/logs/download" class="btn btn-sm btn-secondary" style="font-size: 11px;" download>Tải file báo cáo (.txt) về máy</a>
                    </div>

                    <div id="log-send-status-box" style="display: none; margin-top: 12px; padding: 10px 14px; border-radius: 6px; font-size: 12px;"></div>
                </div>

                <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed var(--border); border-radius: 8px; padding: 12px;">
                    <div style="font-size: 12px; font-weight: 700; color: #34d399; margin-bottom: 4px;">Bảo mật & Riêng tư:</div>
                    <div style="font-size: 11px; color: #94a3b8; line-height: 1.6;">
                        Báo cáo này cũng được tự động lưu dự phòng tại <code>/mnt/SDCARD/RetroHub_Debug_Report.txt</code>. Nhật ký hoàn toàn KHÔNG chứa mật khẩu Wi-Fi hoặc thông tin cá nhân của bạn.
                    </div>
                </div>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
                <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-saves-cheats')">Đóng</button>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        let allSystems = [];
        let currentSystem = null;
        let currentGames = [];
        let selectedGame = null;
        let selectedGameSystem = null;
        let selectedCardIdx = null;
        let noArtTotalCount = 0;

        const ICONS = {
            palette: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"></circle><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"></circle><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"></circle><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"></circle><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.992 6.844 17.5 2 12 2z"></path></svg>`,
            edit: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>`,
            move: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path><line x1="12" y1="11" x2="12" y2="17"></line><polyline points="9 14 12 11 15 14"></polyline></svg>`,
            trash: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`,
            spinner: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="scrape-spinner"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>`,
            alert: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`
        };

        function getPlaceholderSvg(sys) {
            const s = (sys || '').toUpperCase();
            if (['GBA', 'GBC', 'GB', 'WS', 'WSC', 'NGP', 'GG'].includes(s)) {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <rect x="14" y="6" width="36" height="52" rx="6" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <rect x="19" y="12" width="26" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
                    <rect x="22" y="14" width="20" height="16" rx="1" fill="#1e293b" opacity="0.6"/>
                    <path d="M21 41h8m-4-4v8" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
                    <circle cx="42" cy="39" r="2.2" fill="#ef4444"/>
                    <circle cx="37" cy="44" r="2.2" fill="#ef4444"/>
                    <line x1="38" y1="51" x2="42" y2="48" stroke="#475569" stroke-width="1.5"/>
                    <line x1="41" y1="53" x2="45" y2="50" stroke="#475569" stroke-width="1.5"/>
                </svg>`;
            }
            if (['FC', 'NES'].includes(s)) {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <rect x="8" y="18" width="48" height="28" rx="3" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <rect x="12" y="22" width="40" height="20" rx="1" fill="#0f172a"/>
                    <path d="M16 32h8m-4-4v8" stroke="#94a3b8" stroke-width="3" stroke-linecap="square"/>
                    <rect x="27" y="33" width="3.5" height="1.5" fill="#ef4444"/>
                    <rect x="32" y="33" width="3.5" height="1.5" fill="#ef4444"/>
                    <circle cx="42" cy="32" r="2.5" fill="#ef4444"/>
                    <circle cx="48" cy="32" r="2.5" fill="#ef4444"/>
                </svg>`;
            }
            if (['SFC', 'SNES'].includes(s)) {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <rect x="8" y="20" width="48" height="24" rx="12" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <path d="M15 32h8m-4-4v8" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
                    <line x1="27" y1="34" x2="30" y2="31" stroke="#64748b" stroke-width="1.8"/>
                    <line x1="32" y1="34" x2="35" y2="31" stroke="#64748b" stroke-width="1.8"/>
                    <circle cx="46" cy="27" r="2" fill="#3b82f6"/>
                    <circle cx="41" cy="32" r="2" fill="#eab308"/>
                    <circle cx="51" cy="32" r="2" fill="#ef4444"/>
                    <circle cx="46" cy="37" r="2" fill="#22c55e"/>
                </svg>`;
            }
            if (['PS', 'PS1', 'PSP'].includes(s)) {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <path d="M14 20c-5 0-8 4-8 12 0 7 3 14 7 14 3 0 4-5 6-9h16c2 4 3 9 6 9 4 0 7-7 7-14 0-8-3-12-8-12-3 0-5 2-8 2h-4c-3 0-5-2-8-2z" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <circle cx="15" cy="28" r="1.5" fill="#94a3b8"/><circle cx="11" cy="32" r="1.5" fill="#94a3b8"/>
                    <circle cx="19" cy="32" r="1.5" fill="#94a3b8"/><circle cx="15" cy="36" r="1.5" fill="#94a3b8"/>
                    <circle cx="49" cy="28" r="1.5" fill="#10b981"/><circle cx="45" cy="32" r="1.5" fill="#ec4899"/>
                    <circle cx="53" cy="32" r="1.5" fill="#ef4444"/><circle cx="49" cy="36" r="1.5" fill="#3b82f6"/>
                    <circle cx="25" cy="38" r="3.5" fill="#0f172a" stroke="#334155"/>
                    <circle cx="39" cy="38" r="3.5" fill="#0f172a" stroke="#334155"/>
                </svg>`;
            }
            if (['MAME', 'ARCADE', 'CPS1', 'CPS2', 'CPS3', 'NEOGEO'].includes(s)) {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <path d="M14 6h36l-4 44H18L14 6z" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <path d="M14 6h36v8H14z" fill="#0f172a" stroke="#475569" stroke-width="1.5"/>
                    <line x1="20" y1="10" x2="44" y2="10" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/>
                    <rect x="18" y="17" width="28" height="18" rx="2" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
                    <polygon points="15,41 49,41 51,54 13,54" fill="#0f172a" stroke="#475569" stroke-width="1.5"/>
                    <line x1="23" y1="46" x2="23" y2="50" stroke="#94a3b8" stroke-width="2"/>
                    <circle cx="23" cy="45" r="2.8" fill="#ef4444"/>
                    <circle cx="33" cy="46" r="1.4" fill="#3b82f6"/><circle cx="38" cy="46" r="1.4" fill="#ef4444"/><circle cx="43" cy="46" r="1.4" fill="#eab308"/>
                    <circle cx="33" cy="50" r="1.4" fill="#3b82f6"/><circle cx="38" cy="50" r="1.4" fill="#ef4444"/><circle cx="43" cy="50" r="1.4" fill="#eab308"/>
                </svg>`;
            }
            if (['MD', 'GENESIS', 'SEGACD', 'MS', 'SS', 'DC'].includes(s)) {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <path d="M8 26c0-9 8-16 24-16s24 7 24 16c0 10-6 16-12 16-5 0-7-4-12-4s-7 4-12 4c-6 0-12-6-12-16z" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <circle cx="19" cy="27" r="7" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
                    <path d="M15 27h8m-4-4v8" stroke="#94a3b8" stroke-width="2.5" stroke-linecap="round"/>
                    <circle cx="40" cy="31" r="2.2" fill="#64748b"/>
                    <circle cx="45" cy="28" r="2.2" fill="#64748b"/>
                    <circle cx="49" cy="24" r="2.2" fill="#64748b"/>
                </svg>`;
            }
            if (s === 'NDS') {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <rect x="16" y="8" width="32" height="22" rx="3" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <rect x="21" y="12" width="22" height="14" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
                    <line x1="16" y1="32" x2="48" y2="32" stroke="#334155" stroke-width="2"/>
                    <rect x="16" y="34" width="32" height="22" rx="3" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <rect x="21" y="38" width="22" height="14" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
                </svg>`;
            }
            if (s === 'JAVA') {
                return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                    <rect x="18" y="6" width="28" height="52" rx="5" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                    <line x1="28" y1="10" x2="36" y2="10" stroke="#64748b" stroke-width="1.5" stroke-linecap="round"/>
                    <rect x="22" y="14" width="20" height="17" rx="2" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
                    <rect x="28" y="34" width="8" height="6" rx="2" fill="#334155" stroke="#64748b" stroke-width="1"/>
                    <circle cx="32" cy="37" r="1" fill="#38bdf8"/>
                    <circle cx="24" cy="44" r="1" fill="#64748b"/><circle cx="32" cy="44" r="1" fill="#64748b"/><circle cx="40" cy="44" r="1" fill="#64748b"/>
                    <circle cx="24" cy="49" r="1" fill="#64748b"/><circle cx="32" cy="49" r="1" fill="#64748b"/><circle cx="40" cy="49" r="1" fill="#64748b"/>
                    <circle cx="24" cy="53" r="1" fill="#64748b"/><circle cx="32" cy="53" r="1" fill="#64748b"/><circle cx="40" cy="53" r="1" fill="#64748b"/>
                </svg>`;
            }
            return `<svg class="art-sys-svg" viewBox="0 0 64 64" fill="none">
                <rect x="8" y="16" width="48" height="30" rx="8" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                <rect x="12" y="20" width="40" height="22" rx="4" fill="#0f172a" stroke="#334155" stroke-width="1.2"/>
                <path d="M16 31h8m-4-4v8" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
                <rect x="28" y="33" width="3" height="1.5" rx="0.5" fill="#64748b"/>
                <rect x="33" y="33" width="3" height="1.5" rx="0.5" fill="#64748b"/>
                <circle cx="44" cy="27" r="1.8" fill="#ef4444"/>
                <circle cx="40" cy="31" r="1.8" fill="#3b82f6"/>
                <circle cx="48" cy="31" r="1.8" fill="#22c55e"/>
                <circle cx="44" cy="35" r="1.8" fill="#eab308"/>
            </svg>`;
        }

        function showToast(msg, isErr=false) {
            const t = document.getElementById("toast");
            t.innerText = msg;
            t.style.borderColor = isErr ? "var(--danger)" : "var(--primary)";
            t.style.display = "block";
            setTimeout(() => { t.style.display = "none"; }, 3500);
        }

        function closeModal(id) {
            document.getElementById(id).style.display = "none";
        }

        function openArtPreview(url, title) {
            if (!url) return;
            document.getElementById("preview-art-img").src = url;
            document.getElementById("preview-art-title").innerText = title || "Xem Boxart";
            document.getElementById("preview-art-link").href = url;
            document.getElementById("modal-preview-art").style.display = "flex";
        }

        async function loadStatus() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();
                if (data.ok) {
                    document.getElementById("storage-stat").innerHTML = `Thẻ nhớ: <strong>${data.storage.free}</strong> trống / ${data.storage.total} (${data.storage.pct}% dùng)`;
                }
            } catch (e) {
                console.error("Status error:", e);
            }
        }

        function updateNoArtBadge() {
            const badgeEl = document.getElementById("no-art-count-badge");
            if (badgeEl) {
                badgeEl.innerText = noArtTotalCount;
                if (noArtTotalCount <= 0) {
                    badgeEl.classList.remove("count-warn");
                } else {
                    badgeEl.classList.add("count-warn");
                }
            }
            const topBtn = document.getElementById("btn-batch-scrape-top");
            if (topBtn && !isBatchScraping) {
                if (currentSystem === '__no_art__') {
                    if (noArtTotalCount > 0) {
                        topBtn.style.display = "inline-flex";
                        topBtn.innerText = `Cào toàn bộ (${noArtTotalCount})`;
                        topBtn.className = "btn btn-batch";
                    } else {
                        topBtn.style.display = "none";
                    }
                } else {
                    const remainingInSys = currentGames.filter(g => !g.has_art).length;
                    if (remainingInSys > 0) {
                        topBtn.style.display = "inline-flex";
                        topBtn.innerText = `Cào toàn bộ (${remainingInSys})`;
                        topBtn.className = "btn btn-batch";
                    } else {
                        topBtn.style.display = "none";
                    }
                }
            }
        }

        async function loadSystems(refresh=false) {
            try {
                const res = await fetch("/api/systems?_t=" + Date.now());
                const data = await res.json();
                if (data.ok) {
                    allSystems = data.systems;
                    noArtTotalCount = data.no_art_count || 0;
                    renderSystems();
                    if (!currentSystem) {
                        if (allSystems.length > 0) {
                            selectSystem(allSystems[0].dir);
                        }
                    } else if (refresh) {
                        selectSystem(currentSystem);
                    }
                }
            } catch (e) {
                showToast("Lỗi kết nối tới RetroHub Web Server!", true);
            }
            loadStatus();
        }

        function renderSystems() {
            const listEl = document.getElementById("systems-list");
            let html = `
                <div class="sys-item sys-item-special ${currentSystem === '__no_art__' ? 'active' : ''}" onclick="selectSystem('__no_art__')">
                    <span>Chưa có Boxart</span>
                    <span id="no-art-count-badge" class="count ${noArtTotalCount > 0 ? 'count-warn' : ''}">${noArtTotalCount}</span>
                </div>
            `;
            html += allSystems.map(s => `
                <div class="sys-item ${currentSystem === s.dir ? 'active' : ''}" onclick="selectSystem('${s.dir}')">
                    <span>${s.name}</span>
                    <span class="count">${s.count}</span>
                </div>
            `).join('');
            listEl.innerHTML = html;
        }

        async function selectSystem(sysDir) {
            currentSystem = sysDir;
            renderSystems();
            document.getElementById("search-input").value = "";
            const cont = document.getElementById("games-container");
            cont.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-sub);">Đang tải danh sách game...</div>`;
            document.getElementById("empty-state").style.display = "none";

            const inlineBar = document.getElementById("batch-inline-bar");
            if (inlineBar && !isBatchScraping) {
                inlineBar.style.display = "none";
            }

            try {
                const res = await fetch(`/api/games?system=${encodeURIComponent(sysDir)}&_t=${Date.now()}`);
                const data = await res.json();
                if (data.ok) {
                    currentGames = data.games;
                    if (sysDir === "__no_art__") {
                        noArtTotalCount = currentGames.length;
                    }
                    renderGames(currentGames);
                    updateNoArtBadge();
                }
            } catch (e) {
                showToast("Lỗi tải danh sách game!", true);
            }
        }

        function renderGames(games) {
            const cont = document.getElementById("games-container");
            const emptyEl = document.getElementById("empty-state");
            if (games.length === 0) {
                cont.innerHTML = "";
                emptyEl.style.display = "block";
                return;
            }
            emptyEl.style.display = "none";
            const isNoArtView = currentSystem === "__no_art__";
            cont.innerHTML = games.map((g, idx) => {
                const gSys = g.system || currentSystem;
                return `
                <div class="game-card" id="game-card-${idx}">
                    <div class="art-box" id="art-box-${idx}">
                        ${g.has_art ? `<img class="art-img" src="${g.art_url}" loading="lazy" alt="${g.name}" onclick="openArtPreview('${g.art_url}', '${escapeJs(g.name)}')" title="Nhấp để xem ảnh đầy đủ">` : `
                            <div class="art-placeholder" onclick="openScrapeModal('${escapeJs(g.filename)}', '${gSys}', ${idx})" title="Nhấp để cào ảnh">
                                ${getPlaceholderSvg(gSys)}
                                <span style="font-size:11px; font-weight:500;">Chưa có ảnh bìa</span>
                            </div>
                        `}
                        <div class="art-btn-overlay">
                            <button class="btn btn-sm btn-green btn-action-icon" onclick="event.stopPropagation(); openScrapeModal('${escapeJs(g.filename)}', '${gSys}', ${idx})">${ICONS.palette} <span>Cào Art</span></button>
                        </div>
                    </div>
                    <div class="game-info">
                        <div>
                            <div class="game-title" title="${g.filename}">${g.name}</div>
                            ${isNoArtView ? `
                                <div style="margin-top: 4px;">
                                    <span class="badge-sys-pill" title="${g.system_name || gSys}">${g.system_name || gSys}</span>
                                </div>
                            ` : ''}
                            <div class="game-meta" style="margin-top: 6px;">
                                <span>${g.ext.toUpperCase()}</span>
                                <span>${g.size_str}</span>
                            </div>
                        </div>
                        <div class="game-actions">
                            <button class="btn btn-secondary btn-sm btn-action-icon" style="flex:1" onclick="openRenameModal('${escapeJs(g.filename)}', '${gSys}')">${ICONS.edit} <span>Sửa</span></button>
                            <button class="btn btn-secondary btn-sm btn-action-icon" style="flex:1" onclick="openMoveModal('${escapeJs(g.filename)}', '${gSys}')">${ICONS.move} <span>Chuyển</span></button>
                            <button class="btn btn-danger btn-sm btn-action-icon" onclick="deleteGame('${escapeJs(g.filename)}', '${gSys}')" title="Xóa game">${ICONS.trash}</button>
                        </div>
                    </div>
                </div>
            `}).join('');
        }

        function filterGames() {
            const q = document.getElementById("search-input").value.toLowerCase().trim();
            if (!q) {
                renderGames(currentGames);
                return;
            }
            const filtered = currentGames.filter(g => g.name.toLowerCase().includes(q) || g.filename.toLowerCase().includes(q));
            renderGames(filtered);
        }

        function escapeJs(str) {
            return str.replace(/'/g, "\\'").replace(/"/g, "&quot;");
        }

        function openRenameModal(filename, gameSystem) {
            selectedGame = filename;
            selectedGameSystem = gameSystem || currentSystem;
            document.getElementById("rename-old").value = filename;
            document.getElementById("rename-new").value = filename;
            document.getElementById("modal-rename").style.display = "flex";
            document.getElementById("rename-new").focus();
        }

        async function submitRename() {
            const newName = document.getElementById("rename-new").value.trim();
            if (!newName || newName === selectedGame) {
                closeModal("modal-rename");
                return;
            }
            const targetSys = selectedGameSystem || currentSystem;
            try {
                const res = await fetch("/api/rename", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        system: targetSys,
                        old_filename: selectedGame,
                        new_filename: newName
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-rename");
                    if (currentSystem === "__no_art__") {
                        loadSystems(true);
                    } else {
                        selectSystem(currentSystem);
                    }
                } else {
                    showToast(data.error, true);
                }
            } catch (e) {
                showToast("Lỗi khi đổi tên game!", true);
            }
        }

        function openMoveModal(filename, gameSystem) {
            selectedGame = filename;
            selectedGameSystem = gameSystem || currentSystem;
            document.getElementById("move-game").value = filename;
            const sel = document.getElementById("move-target-sys");
            sel.innerHTML = allSystems.filter(s => s.dir !== selectedGameSystem).map(s => `
                <option value="${s.dir}">${s.name} (${s.dir})</option>
            `).join('');
            document.getElementById("modal-move").style.display = "flex";
        }

        async function submitMove() {
            const targetSys = document.getElementById("move-target-sys").value;
            if (!targetSys) return;
            const fromSys = selectedGameSystem || currentSystem;
            try {
                const res = await fetch("/api/move", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        from_system: fromSys,
                        to_system: targetSys,
                        filename: selectedGame
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-move");
                    loadSystems(true);
                } else {
                    showToast(data.error, true);
                }
            } catch (e) {
                showToast("Lỗi khi chuyển hệ máy!", true);
            }
        }

        async function deleteGame(filename, gameSystem) {
            if (!confirm(`Bạn có chắc chắn muốn xóa game "${filename}" khỏi thẻ nhớ không?`)) return;
            const targetSys = gameSystem || selectedGameSystem || currentSystem;
            try {
                const res = await fetch("/api/delete", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        system: targetSys,
                        filename: filename,
                        delete_art: true
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    loadSystems(true);
                } else {
                    showToast(data.error, true);
                }
            } catch (e) {
                showToast("Lỗi khi xóa game!", true);
            }
        }

        function cleanGameQuery(filename) {
            let base = filename.replace(/\.[^/.]+$/, "");
            base = base.replace(/[_\.\+]+/g, " ");
            base = base.replace(/\s*[\(\[][^\)\]]*[\)\]]\s*/g, " ");
            base = base.replace(/\b(EUR|USA|JAP|JPN|PAL|NTSC|MULTi\d*|Goomba|Razor1911|Dump)\b/gi, " ");
            base = base.replace(/[-–—]\s*[a-zA-Z0-9]+$/g, " ");
            base = base.replace(/\b(PSP|PS1|PS2|GBA|NDS|SNES|NES|MD|GENESIS)\b/gi, " ");
            base = base.replace(/[-–—]+/g, " ");
            return base.replace(/\s+/g, " ").trim();
        }

        function openScrapeModal(filename, gameSystem, cardIdx=null) {
            selectedGame = filename;
            selectedGameSystem = gameSystem || currentSystem;
            selectedCardIdx = cardIdx;
            const cleanName = cleanGameQuery(filename);
            document.getElementById("scrape-query").value = cleanName;
            document.getElementById("scrape-direct-url").value = "";
            document.getElementById("scrape-results").innerHTML = "";
            document.getElementById("modal-scrape").style.display = "flex";
            executeScrapeSearch();
        }

        function updateCardArtSuccess(idx, filename, gSys, newArtUrl) {
            if (idx === null || idx === undefined) return;
            const cardEl = document.getElementById(`game-card-${idx}`);
            const artBoxEl = document.getElementById(`art-box-${idx}`);
            if (artBoxEl) {
                artBoxEl.innerHTML = `
                    <img class="art-img" src="${newArtUrl}" loading="lazy" alt="${filename}" onclick="openArtPreview('${newArtUrl}', '${escapeJs(filename)}')" title="Nhấp để xem ảnh đầy đủ">
                    <div class="art-btn-overlay">
                        <button class="btn btn-sm btn-green btn-action-icon" onclick="event.stopPropagation(); openScrapeModal('${escapeJs(filename)}', '${gSys}', ${idx})">${ICONS.palette} <span>Cào Art</span></button>
                    </div>
                `;
            }
            if (cardEl) {
                cardEl.classList.remove("is-scraping");
                cardEl.classList.add("is-success");
            }
            if (currentGames[idx]) {
                currentGames[idx].has_art = true;
                currentGames[idx].art_url = newArtUrl;
            }
            if (noArtTotalCount > 0) {
                noArtTotalCount--;
                updateNoArtBadge();
            }
        }

        function openGoogleImageSearch() {
            const q = document.getElementById("scrape-query").value.trim();
            const targetSys = selectedGameSystem || currentSystem || '';
            const url = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(q + ' ' + targetSys + ' box art cover')}`;
            window.open(url, '_blank');
        }

        async function submitDirectArtUrl() {
            const url = document.getElementById("scrape-direct-url").value.trim();
            if (!url) {
                showToast("Vui lòng dán đường dẫn ảnh hợp lệ!", true);
                return;
            }
            await applyScrapedArt(url);
        }

        async function uploadBlobArt(fileOrBlob) {
            const targetSys = selectedGameSystem || currentSystem;
            try {
                showToast("Đang tải ảnh từ Clipboard lên máy...");
                const res = await fetch(`/api/upload_art?system=${encodeURIComponent(targetSys)}&filename=${encodeURIComponent(selectedGame)}`, {
                    method: "POST",
                    headers: {"Content-Type": fileOrBlob.type || "image/png"},
                    body: fileOrBlob
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || "Đã lưu ảnh bìa từ Clipboard thành công!");
                    closeModal("modal-scrape");
                    const newArtUrl = `/art/${encodeURIComponent(targetSys)}/${encodeURIComponent(selectedGame.replace(/\.[^/.]+$/, "") + '.png')}?v=${Date.now()}`;
                    if (selectedCardIdx !== null) {
                        updateCardArtSuccess(selectedCardIdx, selectedGame, targetSys, newArtUrl);
                    } else {
                        if (currentSystem === "__no_art__") {
                            loadSystems(true);
                        } else {
                            selectSystem(currentSystem);
                        }
                    }
                } else {
                    showToast(data.error || "Lỗi tải ảnh lên!", true);
                }
            } catch (err) {
                showToast("Lỗi khi tải ảnh từ Clipboard lên máy!", true);
            }
        }

        async function pasteAndApplyArt() {
            try {
                if (navigator.clipboard && navigator.clipboard.read) {
                    try {
                        const items = await navigator.clipboard.read();
                        for (const item of items) {
                            for (const type of item.types) {
                                if (type.startsWith("image/")) {
                                    const blob = await item.getType(type);
                                    showToast("Đã đọc được ảnh từ Clipboard! Đang lưu...");
                                    await uploadBlobArt(blob);
                                    return;
                                }
                            }
                        }
                    } catch (readErr) {}
                }

                if (navigator.clipboard && navigator.clipboard.readText) {
                    try {
                        const text = await navigator.clipboard.readText();
                        const trimmed = (text || "").trim();
                        if (trimmed && (trimmed.startsWith("http://") || trimmed.startsWith("https://"))) {
                            document.getElementById("scrape-direct-url").value = trimmed;
                            showToast("Đã lấy link ảnh từ Clipboard, đang tải...");
                            await applyScrapedArt(trimmed);
                            return;
                        }
                    } catch (textErr) {}
                }

                const inputEl = document.getElementById("scrape-direct-url");
                if (inputEl) {
                    inputEl.focus();
                    inputEl.select();
                }
                showToast("Nhấn phím Ctrl+V ngay trên bàn phím để dán trực tiếp ảnh vào đây!", false);
            } catch (e) {
                showToast("Nhấn phím Ctrl+V để dán trực tiếp ảnh từ Clipboard!", false);
            }
        }

        window.addEventListener("paste", async (e) => {
            const modal = document.getElementById("modal-scrape");
            if (modal && modal.style.display === "flex") {
                const activeEl = document.activeElement;
                if (activeEl && activeEl.id === "scrape-query") return;

                const clipboardData = e.clipboardData || window.clipboardData;
                if (!clipboardData) return;

                const items = clipboardData.items;
                if (items && items.length > 0) {
                    for (let i = 0; i < items.length; i++) {
                        if (items[i].type && items[i].type.startsWith("image/")) {
                            const file = items[i].getAsFile();
                            if (file) {
                                e.preventDefault();
                                showToast("Đã nhận ảnh trực tiếp từ Clipboard! Đang lưu...");
                                await uploadBlobArt(file);
                                return;
                            }
                        }
                    }
                }

                const text = clipboardData.getData("text")?.trim() || "";
                if (text && (text.startsWith("http://") || text.startsWith("https://"))) {
                    e.preventDefault();
                    document.getElementById("scrape-direct-url").value = text;
                    showToast("Đã nhận link ảnh từ Clipboard! Đang tải...");
                    applyScrapedArt(text);
                }
            }
        });

        window.addEventListener("dragover", (e) => {
            const modal = document.getElementById("modal-scrape");
            if (modal && modal.style.display === "flex") {
                e.preventDefault();
            }
        });
        window.addEventListener("drop", async (e) => {
            const modal = document.getElementById("modal-scrape");
            if (modal && modal.style.display === "flex") {
                e.preventDefault();
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    const file = e.dataTransfer.files[0];
                    if (file && file.type && file.type.startsWith("image/")) {
                        showToast("Đã nhận ảnh kéo thả! Đang lưu...");
                        await uploadBlobArt(file);
                    }
                }
            }
        });

        async function executeScrapeSearch() {
            const q = document.getElementById("scrape-query").value.trim();
            if (!q) return;
            const targetSys = selectedGameSystem || currentSystem;
            const resBox = document.getElementById("scrape-results");
            resBox.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:25px; color:var(--text-sub);">Đang tìm ảnh trong kho dữ liệu...</div>`;

            try {
                const res = await fetch(`/api/scrape/search?system=${encodeURIComponent(targetSys)}&query=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.ok && data.candidates && data.candidates.length > 0) {
                    resBox.innerHTML = data.candidates.map((c, idx) => `
                        <div class="scrape-card" onclick="applyScrapedArt('${escapeJs(c.url)}')">
                            <img class="scrape-img" src="${c.url}" loading="lazy" onerror="handleScrapeImgError(this)" alt="${c.title}">
                            <span class="scrape-title" title="${c.title}">${c.title}</span>
                            <span class="scrape-tag">${c.type}</span>
                        </div>
                    `).join('');
                } else {
                    resBox.innerHTML = `
                        <div style="grid-column:1/-1; text-align:center; padding:25px; color:var(--text-sub);">
                            <div style="margin-bottom:8px; font-size:13px;">Chưa tìm thấy ảnh phù hợp với từ khóa này.</div>
                            <div style="font-size:12px;">Bạn có thể chỉnh từ khóa ngắn gọn hơn, bấm <strong>"Mở Google Images"</strong> hoặc <strong>"Tải ảnh từ máy"</strong>!</div>
                        </div>
                    `;
                }
            } catch (e) {
                resBox.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:25px; color:var(--danger);">Lỗi khi tìm ảnh bìa! Vui lòng thử lại.</div>`;
            }
        }

        function handleScrapeImgError(img) {
            const card = img.closest('.scrape-card');
            if (card) {
                card.remove();
            }
        }

        async function applyScrapedArt(url) {
            const targetSys = selectedGameSystem || currentSystem;
            try {
                const res = await fetch("/api/scrape/apply", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        system: targetSys,
                        filename: selectedGame,
                        image_url: url
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-scrape");
                    const newArtUrl = `/art/${encodeURIComponent(targetSys)}/${encodeURIComponent(selectedGame.replace(/\.[^/.]+$/, "") + '.png')}?v=${Date.now()}`;
                    if (selectedCardIdx !== null) {
                        updateCardArtSuccess(selectedCardIdx, selectedGame, targetSys, newArtUrl);
                    } else {
                        if (currentSystem === "__no_art__") {
                            loadSystems(true);
                        } else {
                            selectSystem(currentSystem);
                        }
                    }
                } else {
                    showToast(data.error, true);
                }
            } catch (e) {
                showToast("Lỗi khi áp dụng ảnh bìa!", true);
            }
        }

        async function uploadCustomArt(e) {
            const file = e.target.files[0];
            if (!file) return;
            const targetSys = selectedGameSystem || currentSystem;
            try {
                const res = await fetch(`/api/upload_art?system=${encodeURIComponent(targetSys)}&filename=${encodeURIComponent(selectedGame)}`, {
                    method: "POST",
                    headers: {"Content-Type": file.type || "application/octet-stream"},
                    body: file
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-scrape");
                    const newArtUrl = `/art/${encodeURIComponent(targetSys)}/${encodeURIComponent(selectedGame.replace(/\.[^/.]+$/, "") + '.png')}?v=${Date.now()}`;
                    if (selectedCardIdx !== null) {
                        updateCardArtSuccess(selectedCardIdx, selectedGame, targetSys, newArtUrl);
                    } else {
                        if (currentSystem === "__no_art__") {
                            loadSystems(true);
                        } else {
                            selectSystem(currentSystem);
                        }
                    }
                } else {
                    showToast(data.error, true);
                }
            } catch (err) {
                showToast("Lỗi tải ảnh lên!", true);
            }
        }

        // ==========================================
        // TÍNH NĂNG CÀO TOÀN BỘ TRỰC TIẾP (KHÔNG MODAL - UPDATE LIVE LIST)
        // ==========================================
        let isBatchScraping = false;
        let stopBatchRequested = false;

        async function toggleDirectBatchScrape() {
            if (isBatchScraping) {
                stopDirectBatchScrape();
                return;
            }
            startDirectBatchScrape();
        }

        function stopDirectBatchScrape() {
            if (isBatchScraping) {
                stopBatchRequested = true;
                const statusEl = document.getElementById("batch-inline-status");
                if (statusEl) statusEl.innerText = "Đang dừng cào...";
                const topBtn = document.getElementById("btn-batch-scrape-top");
                if (topBtn) topBtn.innerText = "Đang dừng...";
            }
        }

        function updateCardArtFailure(idx, filename, gSys, reason="Không tìm thấy") {
            if (idx === null || idx === undefined) return;
            const cardEl = document.getElementById(`game-card-${idx}`);
            const artBoxEl = document.getElementById(`art-box-${idx}`);
            if (cardEl) {
                cardEl.classList.remove("is-scraping");
            }
            if (artBoxEl) {
                artBoxEl.innerHTML = `
                    <div class="art-placeholder" onclick="openScrapeModal('${escapeJs(filename)}', '${gSys}', ${idx})" title="Nhấp để cào ảnh">
                        ${ICONS.alert}
                        <span style="font-size:11px; color:#f59e0b;">${reason}</span>
                    </div>
                    <div class="art-btn-overlay">
                        <button class="btn btn-sm btn-green btn-action-icon" onclick="event.stopPropagation(); openScrapeModal('${escapeJs(filename)}', '${gSys}', ${idx})">${ICONS.palette} <span>Cào Art</span></button>
                    </div>
                `;
            }
        }

        function setCardArtScraping(idx, label="Đang cào ảnh...") {
            if (idx === null || idx === undefined) return;
            const cardEl = document.getElementById(`game-card-${idx}`);
            const artBoxEl = document.getElementById(`art-box-${idx}`);
            if (cardEl) {
                cardEl.classList.add("is-scraping");
            }
            if (artBoxEl) {
                artBoxEl.innerHTML = `
                    <div class="art-placeholder" style="color:#38bdf8;">
                        ${ICONS.spinner}
                        <span style="font-size:11px;">${label}</span>
                    </div>
                `;
            }
        }

        async function startDirectBatchScrape() {
            const targets = [];
            for (let i = 0; i < currentGames.length; i++) {
                if (!currentGames[i].has_art) {
                    targets.push({ game: currentGames[i], index: i });
                }
            }

            if (targets.length === 0) {
                showToast("Tất cả game trong danh sách hiện tại đều đã có ảnh bìa!");
                return;
            }

            isBatchScraping = true;
            stopBatchRequested = false;

            const inlineBar = document.getElementById("batch-inline-bar");
            inlineBar.style.display = "flex";
            const statusText = document.getElementById("batch-inline-status");
            const pctText = document.getElementById("batch-inline-pct");
            const fillBar = document.getElementById("batch-inline-fill");
            const topBtn = document.getElementById("btn-batch-scrape-top");

            if (topBtn) {
                topBtn.innerText = `Dừng cào (${targets.length})`;
                topBtn.className = "btn btn-danger";
            }

            const total = targets.length;
            let completedCount = 0;
            let successCount = 0;

            function renderProgress(titleName, gSysName) {
                const pct = Math.round((completedCount / total) * 100);
                pctText.innerText = `${pct}%`;
                fillBar.style.width = `${pct}%`;
                if (titleName) {
                    statusText.innerHTML = `[${completedCount}/${total}] Đang xử lý: <strong>${titleName}</strong> (${gSysName}) &bull; <span style="color:#10b981; font-weight:600;">Đã xong ${successCount} ảnh</span>`;
                } else {
                    statusText.innerHTML = `[${completedCount}/${total}] Đang xử lý... &bull; <span style="color:#10b981; font-weight:600;">Đã xong ${successCount} ảnh</span>`;
                }
            }

            // Giai đoạn 1: Tốc độ cao (Catalog DB & CDN Libretro) - 4 workers song song
            const fastQueue = [...targets];
            const notFoundList = [];
            const CONCURRENCY = 4;

            async function fastWorker() {
                while (fastQueue.length > 0 && !stopBatchRequested) {
                    const item = fastQueue.shift();
                    const { game: g, index: idx } = item;
                    const gSys = g.system || currentSystem;
                    const gSysName = g.system_name || gSys;
                    const cleanTitle = cleanGameQuery(g.filename);

                    setCardArtScraping(idx, "Đang cào nhanh...");
                    renderProgress(g.name, gSysName);

                    try {
                        const res = await fetch("/api/scrape/auto", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                                system: gSys,
                                filename: g.filename,
                                query: cleanTitle,
                                fast: true
                            })
                        });
                        const data = await res.json();
                        if (data.ok && data.art_url) {
                            successCount++;
                            updateCardArtSuccess(idx, g.filename, gSys, data.art_url);
                        } else {
                            notFoundList.push(item);
                        }
                    } catch (err) {
                        console.error("Fast worker error:", err);
                        notFoundList.push(item);
                    }

                    completedCount++;
                    renderProgress(g.name, gSysName);
                }
            }

            const fastWorkers = [];
            const numWorkers = Math.min(CONCURRENCY, fastQueue.length);
            for (let w = 0; w < numWorkers; w++) {
                fastWorkers.push(fastWorker());
            }
            await Promise.all(fastWorkers);

            // Giai đoạn 2: Web Search cho các game còn lại chưa tìm thấy
            if (!stopBatchRequested && notFoundList.length > 0) {
                statusText.innerHTML = `Tìm kiếm Web sâu cho ${notFoundList.length} game còn lại... &bull; <span style="color:#10b981; font-weight:600;">Đã xong ${successCount}/${total}</span>`;
                const deepQueue = [...notFoundList];
                notFoundList.length = 0;

                async function deepWorker() {
                    while (deepQueue.length > 0 && !stopBatchRequested) {
                        const item = deepQueue.shift();
                        const { game: g, index: idx } = item;
                        const gSys = g.system || currentSystem;
                        const gSysName = g.system_name || gSys;
                        const cleanTitle = cleanGameQuery(g.filename);

                        setCardArtScraping(idx, "Đang tìm Web...");
                        statusText.innerHTML = `Tìm Web: <strong>${g.name}</strong> (${gSysName})... &bull; <span style="color:#10b981; font-weight:600;">Đã xong ${successCount}/${total}</span>`;

                        try {
                            const res = await fetch("/api/scrape/auto", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    system: gSys,
                                    filename: g.filename,
                                    query: cleanTitle,
                                    fast: false
                                })
                            });
                            const data = await res.json();
                            if (data.ok && data.art_url) {
                                successCount++;
                                updateCardArtSuccess(idx, g.filename, gSys, data.art_url);
                            } else {
                                updateCardArtFailure(idx, g.filename, gSys, "Không tìm thấy");
                            }
                        } catch (err) {
                            updateCardArtFailure(idx, g.filename, gSys, "Lỗi cào ảnh");
                        }
                    }
                }

                const deepWorkers = [];
                const numDeepWorkers = Math.min(2, deepQueue.length);
                for (let w = 0; w < numDeepWorkers; w++) {
                    deepWorkers.push(deepWorker());
                }
                await Promise.all(deepWorkers);
            } else if (notFoundList.length > 0) {
                for (const item of notFoundList) {
                    const gSys = item.game.system || currentSystem;
                    updateCardArtFailure(item.index, item.game.filename, gSys, "Chưa có ảnh");
                }
            }

            fillBar.style.width = "100%";
            pctText.innerText = "100%";
            isBatchScraping = false;

            if (topBtn) {
                topBtn.innerText = "Cào toàn bộ ảnh";
                topBtn.className = "btn btn-batch";
            }

            if (stopBatchRequested) {
                statusText.innerText = `Đã dừng. Cập nhật thành công ${successCount}/${total} ảnh bìa.`;
                showToast(`Đã dừng: Cập nhật thành công ${successCount} ảnh!`);
            } else {
                statusText.innerText = `Hoàn tất! Đã cập nhật ${successCount}/${total} ảnh bìa vào danh sách.`;
                showToast(`Hoàn tất: Đã cào xong ${successCount}/${total} ảnh bìa!`);
            }

            updateNoArtBadge();

            setTimeout(() => {
                if (!isBatchScraping) {
                    inlineBar.style.display = "none";
                }
            }, 5000);
        }

        // ==========================================
        // TÍNH NĂNG TẢI ROM LÊN (CHỌN FILE LUÔN & SHOW TIẾN ĐỘ)
        // ==========================================
        let pendingUploadSystem = null;
        let currentUploadXhr = null;
        let isUploadingRom = false;

        function formatBytes(bytes) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        function handleUploadRomClick() {
            if (!currentSystem || currentSystem === '__no_art__') {
                const sel = document.getElementById("modal-upload-sys-select");
                sel.innerHTML = allSystems.map(s => `
                    <option value="${s.dir}">${s.name} (${s.dir})</option>
                `).join('');
                document.getElementById("modal-select-upload-sys").style.display = "flex";
            } else {
                pendingUploadSystem = currentSystem;
                document.getElementById("rom-file-input-direct").click();
            }
        }

        function confirmSystemAndBrowseFiles() {
            const sel = document.getElementById("modal-upload-sys-select");
            pendingUploadSystem = sel.value;
            closeModal("modal-select-upload-sys");
            document.getElementById("rom-file-input-direct").click();
        }

        function cancelOrCloseUpload() {
            if (isUploadingRom) {
                if (!confirm("Đang tải tệp lên thiết bị. Bạn có chắc muốn hủy bỏ không?")) {
                    return;
                }
                isUploadingRom = false;
                if (currentUploadXhr) {
                    currentUploadXhr.abort();
                }
            }
            document.getElementById("modal-upload-progress").style.display = "none";
            loadSystems(true);
        }

        function uploadSingleRomFile(file, targetSys, onProgress) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                currentUploadXhr = xhr;
                xhr.open("POST", `/api/upload_rom?system=${encodeURIComponent(targetSys)}&filename=${encodeURIComponent(file.name)}`, true);
                xhr.setRequestHeader("Content-Type", "application/octet-stream");

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        onProgress(e.loaded, e.total);
                    }
                };

                xhr.onload = () => {
                    currentUploadXhr = null;
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const res = JSON.parse(xhr.responseText);
                            resolve(res);
                        } catch (err) {
                            resolve({ok: true});
                        }
                    } else {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                };

                xhr.onerror = () => {
                    currentUploadXhr = null;
                    reject(new Error("Lỗi mạng khi tải lên!"));
                };

                xhr.onabort = () => {
                    currentUploadXhr = null;
                    reject(new Error("Đã hủy tải"));
                };

                xhr.send(file);
            });
        }

        async function handleDirectRomFiles(e) {
            const files = Array.from(e.target.files);
            e.target.value = '';
            if (files.length === 0) return;

            const targetSys = pendingUploadSystem || currentSystem;
            if (!targetSys || targetSys === '__no_art__') {
                showToast("Vui lòng chọn hệ máy đích!", true);
                return;
            }

            const sysObj = allSystems.find(s => s.dir === targetSys);
            const sysName = sysObj ? sysObj.name : targetSys;

            // Mở modal hiển thị tiến độ
            document.getElementById("upload-target-name").innerText = `${sysName} (${targetSys})`;
            document.getElementById("upload-prog-title").innerText = `Đang tải ${files.length} ROM lên thiết bị`;
            document.getElementById("btn-upload-cancel").innerText = "Hủy bỏ";
            document.getElementById("btn-upload-cancel").className = "btn btn-secondary";
            document.getElementById("upload-status-footer").innerText = "Vui lòng không tắt trình duyệt khi đang tải file lớn.";
            
            const overallBox = document.getElementById("upload-overall-box");
            if (files.length > 1) {
                overallBox.style.display = "block";
                document.getElementById("upload-overall-pct").innerText = "0%";
                document.getElementById("upload-overall-progress-bar").style.width = "0%";
            } else {
                overallBox.style.display = "none";
            }

            // Render danh sách file ban đầu
            const fileListEl = document.getElementById("upload-file-list");
            fileListEl.innerHTML = files.map((f, i) => `
                <div id="upload-item-${i}" class="batch-log-item">
                    <span id="upload-item-icon-${i}" style="width:20px; text-align:center;">[ ]</span>
                    <span style="color:#e2e8f0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${f.name}">${f.name}</span>
                    <span style="color:var(--text-sub); font-size:10px;">${formatBytes(f.size)}</span>
                    <span id="upload-item-status-${i}" style="color:var(--text-sub); font-size:10px; width:65px; text-align:right;">Chờ...</span>
                </div>
            `).join('');

            document.getElementById("modal-upload-progress").style.display = "flex";
            isUploadingRom = true;

            let successCount = 0;
            for (let i = 0; i < files.length; i++) {
                if (!isUploadingRom) break;
                const f = files[i];

                // Cập nhật thông tin file hiện tại
                document.getElementById("upload-current-fname").innerText = f.name;
                document.getElementById("upload-current-pct").innerText = "0%";
                document.getElementById("upload-file-progress-bar").style.width = "0%";
                document.getElementById("upload-file-size-info").innerText = `0 / ${formatBytes(f.size)}`;
                document.getElementById("upload-batch-count-info").innerText = `Tệp ${i + 1} / ${files.length}`;

                const itemIcon = document.getElementById(`upload-item-icon-${i}`);
                const itemStatus = document.getElementById(`upload-item-status-${i}`);
                if (itemIcon) itemIcon.innerText = "...";
                if (itemStatus) {
                    itemStatus.innerText = "0%";
                    itemStatus.style.color = "#38bdf8";
                }

                try {
                    await uploadSingleRomFile(f, targetSys, (loaded, total) => {
                        const pct = Math.round((loaded / total) * 100);
                        document.getElementById("upload-current-pct").innerText = `${pct}%`;
                        document.getElementById("upload-file-progress-bar").style.width = `${pct}%`;
                        document.getElementById("upload-file-size-info").innerText = `${formatBytes(loaded)} / ${formatBytes(total)}`;
                        if (itemStatus) itemStatus.innerText = `${pct}%`;
                    });

                    successCount++;
                    if (itemIcon) itemIcon.innerHTML = `<span style="color:#10b981; font-weight:bold;">OK</span>`;
                    if (itemStatus) {
                        itemStatus.innerText = "Xong";
                        itemStatus.style.color = "#10b981";
                    }
                } catch (err) {
                    if (itemIcon) itemIcon.innerHTML = `<span style="color:#ef4444; font-weight:bold;">ERR</span>`;
                    if (itemStatus) {
                        itemStatus.innerText = "Lỗi";
                        itemStatus.style.color = "#ef4444";
                    }
                }

                if (files.length > 1) {
                    const overallPct = Math.round(((i + 1) / files.length) * 100);
                    document.getElementById("upload-overall-pct").innerText = `${overallPct}%`;
                    document.getElementById("upload-overall-progress-bar").style.width = `${overallPct}%`;
                }
            }

            isUploadingRom = false;
            document.getElementById("upload-current-pct").innerText = "100%";
            document.getElementById("upload-file-progress-bar").style.width = "100%";
            document.getElementById("btn-upload-cancel").innerText = "Đóng";
            document.getElementById("btn-upload-cancel").className = "btn btn-green";
            document.getElementById("upload-prog-title").innerText = `Hoàn tất tải lên (${successCount}/${files.length} ROM)`;
            document.getElementById("upload-status-footer").innerText = `Đã tải lên ${successCount} tệp thành công vào hệ máy ${sysName}.`;
            showToast(`Đã tải lên ${successCount} tệp ROM thành công!`);

            if (currentSystem === targetSys) {
                selectSystem(currentSystem);
            } else {
                loadSystems(true);
            }
        }

        // -------------------------------------------------------------
        // SAVE GAMES & CHEATS MANAGER WEB JS
        // -------------------------------------------------------------
        let cheatsPollTimer = null;

        function openSavesCheatsModal(tab = 'saves') {
            document.getElementById('modal-saves-cheats').classList.add('active');
            switchSavesCheatsTab(tab);
        }

        function switchSavesCheatsTab(tab) {
            const tabBtnSaves = document.getElementById('tab-btn-saves');
            const tabBtnCheats = document.getElementById('tab-btn-cheats');
            const tabBtnLogs = document.getElementById('tab-btn-logs');
            const contentSaves = document.getElementById('tab-content-saves');
            const contentCheats = document.getElementById('tab-content-cheats');
            const contentLogs = document.getElementById('tab-content-logs');

            tabBtnSaves.className = (tab === 'saves') ? 'btn btn-sm' : 'btn btn-sm btn-secondary';
            tabBtnCheats.className = (tab === 'cheats') ? 'btn btn-sm' : 'btn btn-sm btn-secondary';
            tabBtnLogs.className = (tab === 'logs') ? 'btn btn-sm' : 'btn btn-sm btn-secondary';

            contentSaves.style.display = (tab === 'saves') ? 'block' : 'none';
            contentCheats.style.display = (tab === 'cheats') ? 'block' : 'none';
            contentLogs.style.display = (tab === 'logs') ? 'block' : 'none';

            if (tab === 'saves') {
                loadSavesData();
            } else if (tab === 'cheats') {
                loadCheatsData();
            } else if (tab === 'logs') {
                loadLogsData();
            }
        }

        async function loadSavesData() {
            try {
                const res = await fetch('/api/saves');
                const data = await res.json();
                if (data.ok) {
                    const st = data.stats || {};
                    const totFiles = st.total_files || 0;
                    const totMb = ((st.total_bytes || 0) / (1024 * 1024)).toFixed(2);
                    document.getElementById('saves-summary-text').innerText = `${totFiles} file save (${totMb} MB) — ${st.types?.srm || 0} .srm / ${st.types?.state || 0} states`;

                    const backups = data.backups || [];
                    const tableBox = document.getElementById('backups-list-table');
                    if (backups.length === 0) {
                        tableBox.innerHTML = '<div style="text-align:center; padding: 24px; color: var(--text-sub); font-size:12px;">Chưa có bản sao lưu nào. Hãy bấm "+ Tạo bản sao lưu" ở trên!</div>';
                        return;
                    }

                    let html = '';
                    for (const b of backups) {
                        const mb = (b.size / (1024 * 1024)).toFixed(2);
                        const sizeStr = mb >= 1.0 ? `${mb} MB` : `${(b.size / 1024).toFixed(1)} KB`;
                        html += `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 12px;">
                            <div style="min-width: 0; flex: 1;">
                                <div style="font-weight: 600; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${b.filename}</div>
                                <div style="font-size: 11px; color: var(--text-sub);">${b.date_str} • ${b.file_count} files • ${sizeStr}</div>
                            </div>
                            <div style="display: flex; gap: 6px; align-items: center; margin-left: 10px;">
                                <a href="/api/saves/download?file=${encodeURIComponent(b.filename)}" class="btn btn-sm btn-secondary" style="font-size: 11px;" download>Tải zip</a>
                                <button class="btn btn-sm btn-green" style="font-size: 11px;" onclick="restoreSaveBackupWeb('${b.filename}')">Khôi phục</button>
                                <button class="btn btn-sm btn-secondary" style="font-size: 11px; color: #ef4444;" onclick="deleteSaveBackupWeb('${b.filename}')">Xóa</button>
                            </div>
                        </div>`;
                    }
                    tableBox.innerHTML = html;
                }
            } catch (e) {
                console.error('Error loading saves:', e);
            }
        }

        async function createSaveBackupWeb() {
            try {
                showToast('Đang nén file sao lưu save game...');
                const res = await fetch('/api/saves/backup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({note: 'Web Backup'})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã tạo bản sao lưu save thành công!');
                    loadSavesData();
                } else {
                    alert('Lỗi: ' + (data.error || 'Không thể tạo sao lưu'));
                }
            } catch (e) {
                alert('Lỗi mạng: ' + e);
            }
        }

        async function restoreSaveBackupWeb(filename) {
            if (!confirm(`Bạn có chắc muốn khôi phục bản sao lưu "${filename}" về thẻ nhớ?`)) return;
            try {
                showToast('Đang khôi phục save game...');
                const res = await fetch('/api/saves/restore', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: filename})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã khôi phục save thành công!');
                } else {
                    alert('Lỗi: ' + (data.error || 'Không thể khôi phục'));
                }
            } catch (e) {
                alert('Lỗi mạng: ' + e);
            }
        }

        async function deleteSaveBackupWeb(filename) {
            if (!confirm(`Xóa bản sao lưu "${filename}"?`)) return;
            try {
                const res = await fetch('/api/saves/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: filename})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã xóa bản sao lưu');
                    loadSavesData();
                }
            } catch (e) {
                alert('Lỗi mạng: ' + e);
            }
        }

        async function loadCheatsData() {
            try {
                const res = await fetch('/api/cheats/status');
                const data = await res.json();
                if (data.ok) {
                    const st = data.status || {};
                    const runner = data.runner || {};
                    const btn = document.getElementById('btn-cheats-action');
                    const progBox = document.getElementById('cheats-progress-box');

                    if (st.installed) {
                        document.getElementById('cheats-status-text').innerText = `Đã cài đặt: ${st.count} mã Cheat (.cht) trong RetroArch.`;
                        btn.innerText = 'Cập nhật / Tải lại Cheat';
                    } else {
                        document.getElementById('cheats-status-text').innerText = 'Chưa có mã Cheat nào trên máy.';
                        btn.innerText = 'Tải trọn bộ Cheat (~37MB)';
                    }

                    if (runner.running) {
                        progBox.style.display = 'block';
                        document.getElementById('cheats-prog-pct').innerText = `${runner.progress_pct}%`;
                        document.getElementById('cheats-prog-fill').style.width = `${runner.progress_pct}%`;
                        document.getElementById('cheats-prog-status').innerText = runner.status_msg || 'Đang tải...';

                        if (!cheatsPollTimer) {
                            cheatsPollTimer = setInterval(loadCheatsData, 1000);
                        }
                    } else {
                        progBox.style.display = 'none';
                        if (cheatsPollTimer) {
                            clearInterval(cheatsPollTimer);
                            cheatsPollTimer = null;
                        }
                    }
                }
            } catch (e) {
                console.error('Error loading cheats:', e);
            }
        }

        async function startCheatsDownloadWeb() {
            try {
                const res = await fetch('/api/cheats/download', {method: 'POST'});
                const data = await res.json();
                showToast(data.message || 'Bắt đầu tải kho Cheat...');
                loadCheatsData();
            } catch (e) {
                alert('Lỗi: ' + e);
            }
        }

        async function stopCheatsDownloadWeb() {
            try {
                await fetch('/api/cheats/stop', {method: 'POST'});
                showToast('Đã dừng tải Cheat');
                loadCheatsData();
            } catch (e) {
                alert('Lỗi: ' + e);
            }
        }

        async function loadLogsData() {
            try {
                const res = await fetch('/api/logs/status');
                const data = await res.json();
                if (data.ok) {
                    const devEl = document.getElementById('web-log-device-id');
                    const sizeEl = document.getElementById('web-log-size');
                    const badgeEl = document.getElementById('web-log-status-badge');
                    const btnToggle = document.getElementById('btn-toggle-log-web');

                    if (devEl) devEl.innerText = data.device_id || 'RH-0000';
                    if (sizeEl) sizeEl.innerText = data.log_size || '0 B';

                    if (data.enable_logging) {
                        if (badgeEl) {
                            badgeEl.innerText = 'ĐANG BẬT';
                            badgeEl.style.color = '#10b981';
                        }
                        if (btnToggle) {
                            btnToggle.innerText = 'Tắt ghi log';
                            btnToggle.className = 'btn btn-sm btn-secondary';
                        }
                    } else {
                        if (badgeEl) {
                            badgeEl.innerText = 'ĐÃ TẮT';
                            badgeEl.style.color = '#ef4444';
                        }
                        if (btnToggle) {
                            btnToggle.innerText = 'Bật ghi log';
                            btnToggle.className = 'btn btn-sm btn-green';
                        }
                    }
                }
            } catch (e) {
                console.error('Error loading logs data:', e);
            }
        }

        async function toggleLoggingWeb() {
            try {
                const res = await fetch('/api/logs/toggle', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã thay đổi trạng thái ghi log');
                    loadLogsData();
                }
            } catch (e) {
                alert('Lỗi: ' + e);
            }
        }

        async function clearLogWeb() {
            if (!confirm('Bạn có chắc muốn làm sạch toàn bộ tệp nhật ký trên máy?')) return;
            try {
                const res = await fetch('/api/logs/clear', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã làm sạch nhật ký thành công!');
                    loadLogsData();
                }
            } catch (e) {
                alert('Lỗi: ' + e);
            }
        }

        async function sendLogTelegramWeb() {
            const btn = document.getElementById('btn-send-log-tg');
            const statusBox = document.getElementById('log-send-status-box');
            const noteInput = document.getElementById('log-user-note');
            const note = (noteInput ? noteInput.value : '').trim();

            btn.disabled = true;
            btn.innerText = 'Đang gửi nhật ký...';
            statusBox.style.display = 'block';
            statusBox.style.background = '#1e293b';
            statusBox.style.color = '#38bdf8';
            statusBox.style.border = '1px solid #0284c7';
            statusBox.innerText = 'Đang đóng gói dữ liệu chẩn đoán và tải lên Telegram bot... Vui lòng đợi vài giây.';

            try {
                const res = await fetch('/api/logs/send-telegram', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({note: note})
                });
                const data = await res.json();
                if (data.ok) {
                    statusBox.style.background = '#064e3b';
                    statusBox.style.color = '#34d399';
                    statusBox.style.border = '1px solid #059669';
                    statusBox.innerText = (data.message || 'Đã gửi nhật ký thành công!');
                    showToast('Gửi log lên Telegram thành công!');
                } else {
                    statusBox.style.background = '#450a0a';
                    statusBox.style.color = '#f87171';
                    statusBox.style.border = '1px solid #dc2626';
                    statusBox.innerText = 'Lỗi: ' + (data.error || 'Không thể gửi log');
                }
            } catch (err) {
                statusBox.style.background = '#450a0a';
                statusBox.style.color = '#f87171';
                statusBox.style.border = '1px solid #dc2626';
                statusBox.innerText = 'Lỗi kết nối máy chủ: ' + err;
            } finally {
                btn.disabled = false;
                btn.innerText = 'Gửi Log vào Telegram tác giả';
            }
        }

        loadSystems();
    </script>
</body>
</html>
"""

def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadedHTTPServer(server_address, GameWebHandler)
    print(f"[*] RetroHub Web Game Manager running at http://0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
