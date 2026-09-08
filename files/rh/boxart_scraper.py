# -*- coding: utf-8 -*-
"""Boxart Scraper for handheld device: scan ROMs without boxarts, scrape from
SQLite Catalog DB and Libretro Thumbnails CDN, and save directly to Imgs/.
Runs with concurrency (4 workers) for high performance.
"""

import os
import re
import ssl
import json
import time
import subprocess
import threading
import urllib.request
import urllib.parse
import shutil

from .paths import SDCARD_PATH, APP_DIR, is_nextui
from .catalog import scan_all_downloaded_games, VALID_EXTS
from .boxart import is_real_boxart_url
from .media import save_boxart_png

try:
    _SSL_CONTEXT = ssl.create_default_context()
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CONTEXT = None

_LIBRETRO_INDEX_CACHE = {}
_CACHE_LOCK = threading.Lock()

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

STOP_WORDS = {
    'of', 'the', 'a', 'an', 'and', 'in', 'on', 'to', 'for', 'at', 'by', 'from',
    'with', 'de', 'der', 'die', 'das', 'le', 'la', 'les',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
}


def get_catalog_db_path():
    """Tìm database sqlite3 trên thẻ nhớ hoặc /tmp."""
    candidates = [
        os.path.join(SDCARD_PATH, "Apps", "RetroHub", "catalog", "roms_store.sqlite3"),
        os.path.join(SDCARD_PATH, "RetroHub", "catalog", "roms_store.sqlite3"),
        os.path.join(APP_DIR, "catalog", "roms_store.sqlite3"),
        "/tmp/roms_store.sqlite3",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.path.getsize(c) > 1000000:
            return c

    gz_candidates = [
        os.path.join(SDCARD_PATH, "Apps", "RetroHub", "catalog", "roms_store.sqlite3.gz"),
        os.path.join(SDCARD_PATH, "RetroHub", "catalog", "roms_store.sqlite3.gz"),
        os.path.join(APP_DIR, "catalog", "roms_store.sqlite3.gz"),
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
            except Exception:
                pass
    return None


def clean_rom_title(filename):
    """Làm sạch tên file ROM để tối ưu từ khóa tìm kiếm ảnh bìa."""
    base = os.path.splitext(filename)[0] if "." in filename else filename
    # Loại bỏ số thứ tự đánh dấu release ở đầu: ví dụ "0032 - ", "0247 - ", "4. "
    base = re.sub(r'^\s*\d{1,4}\s*[\.\-]+\s*', '', base)
    # Loại bỏ các tag đóng mở ngoặc: (USA), [!], (E)(Eurasia), (Topo shop), [Gamefall21]
    base = re.sub(r'\[.*?\]|\(.*?\)', ' ', base)
    # Chuẩn hóa dấu phân cách thành dấu cách trước khi lọc từ khóa
    base = re.sub(r'[_\.\+]+', ' ', base)
    base = re.sub(r'[-–—]+', ' ', base)
    # Loại bỏ các mã ID game PSP/PSX: ví dụ UCUS98653, ULES12345, SLUS, SLES, SCUS, NPUB, NPUZ...
    base = re.sub(r'\b[A-Za-z]{3,4}\d{4,5}\b', ' ', base)
    # Loại bỏ các mã CRC/hash 8 ký tự hex: ví dụ 7F746677, 864E835C
    base = re.sub(r'\b[0-9A-Fa-f]{8}\b', ' ', base)
    # Loại bỏ các tag nhóm dịch / scene / hack
    base = re.sub(r'\b(viet[\s\-_]*hoa|vh|vie|aowvn|gamefall\d*|topo[\s\-_]*shop|4fun|eur|usa|jap|jpn|pal|ntsc|multi\d*|goomba|razor1911|dump)\b', ' ', base, flags=re.IGNORECASE)
    # Tách các từ viết dính liền phổ biến
    base = re.sub(r'\bGodofWar\b', 'God of War', base, flags=re.IGNORECASE)
    base = re.sub(r'\bChainsofOlympus\b', 'Chains of Olympus', base, flags=re.IGNORECASE)
    base = re.sub(r'\bGhostofSparta\b', 'Ghost of Sparta', base, flags=re.IGNORECASE)
    base = re.sub(r'\bPrinceofPersia\b', 'Prince of Persia', base, flags=re.IGNORECASE)
    base = re.sub(r'\bMetalSlug\b', 'Metal Slug', base, flags=re.IGNORECASE)
    base = re.sub(r'\b(PSP|PS1|PS2|GBA|NDS|SNES|NES|MD|GENESIS)\b', ' ', base, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', base).strip()


def extract_jar_icon(jar_path, target_png):
    """Trích xuất icon gốc từ file .jar của game Java J2ME."""
    if not jar_path or not os.path.isfile(jar_path):
        return False
    try:
        import zipfile
        with zipfile.ZipFile(jar_path, 'r') as z:
            icon_name = None
            if 'META-INF/MANIFEST.MF' in z.namelist():
                try:
                    mf = z.read('META-INF/MANIFEST.MF').decode('utf-8', errors='ignore')
                    for line in mf.splitlines():
                        if 'MIDlet-' in line and '.png' in line.lower():
                            parts = [p.strip().lstrip('/') for p in line.split(',') if '.png' in p.lower()]
                            if parts and parts[0] in z.namelist():
                                icon_name = parts[0]
                                break
                except Exception:
                    pass
            if not icon_name:
                for n in ('icon.png', 'i.png', 'res/icon.png', 'icons/icon.png'):
                    if n in z.namelist():
                        icon_name = n
                        break
            if not icon_name:
                for n in z.namelist():
                    if 'icon' in n.lower() and n.lower().endswith('.png'):
                        icon_name = n
                        break
            if icon_name:
                raw_bytes = z.read(icon_name)
                if raw_bytes and len(raw_bytes) > 32:
                    os.makedirs(os.path.dirname(target_png), exist_ok=True)
                    save_boxart_png(raw_bytes, target_png)
                    return True
    except Exception:
        pass
    return False


def _get_sqlite_conn(db_path):
    """Mở kết nối SQLite an toàn: tự động fallback sang CTypes SQLite nếu thiếu C-extension _sqlite3."""
    if not db_path or not os.path.isfile(db_path):
        return None
    try:
        import sqlite3
        return sqlite3.connect(db_path, timeout=5)
    except Exception:
        pass
    try:
        import sys
        _app_d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _app_d not in sys.path:
            sys.path.insert(0, _app_d)
        import db
        if hasattr(db, "CTypesSQLiteConnection"):
            return db.CTypesSQLiteConnection(db_path)
    except Exception:
        pass
    return None


def search_catalog_db(sys_code, query, filename="", max_results=1):
    """Tra cứu nhanh ảnh bìa trong Catalog DB SQLite (~1ms).
    Ưu tiên 1: Tìm kiếm chính xác theo filename trong bảng game_sources (cực kỳ hiệu quả cho game Arcade/MAME/NEOGEO/DC).
    Ưu tiên 2: Tìm kiếm tiêu đề theo sys_code và các từ khóa trong games table.
    Ưu tiên 3: Tìm kiếm xuyên hệ máy cho các hệ liên quan (Arcade/MAME/FBNeo/NEOGEO).
    """
    db_p = get_catalog_db_path()
    if not db_p:
        return []
    conn = None
    try:
        conn = _get_sqlite_conn(db_p)
        if not conn:
            return []
        cur = conn.cursor()

        # 1. Tra cứu trực tiếp theo tên file ROM trong game_sources
        if filename:
            try:
                cur.execute(
                    "SELECT g.title, g.img_url FROM game_sources s "
                    "JOIN games g ON s.game_id = g.id "
                    "WHERE s.filename = ? AND g.img_url IS NOT NULL AND g.img_url != '' LIMIT 1",
                    (filename,)
                )
                r = cur.fetchone()
                if r and r[1] and "no-image" not in r[1].lower():
                    if conn and hasattr(conn, "close"):
                        try: conn.close()
                        except Exception: pass
                    return [{"title": r[0], "type": "Catalog DB", "url": r[1]}]
            except Exception:
                pass

        sys_aliases = [sys_code.upper()]
        if sys_code.upper() in ("NES", "FC"):
            sys_aliases = ["FC", "NES"]
        elif sys_code.upper() in ("SNES", "SFC"):
            sys_aliases = ["SFC", "SNES"]
        elif sys_code.upper() in ("GENESIS", "MD"):
            sys_aliases = ["MD", "GENESIS"]
        elif sys_code.upper() in ("PS1", "PS"):
            sys_aliases = ["PS", "PS1"]
        elif sys_code.upper() in ("MAME", "ARCADE", "FBNEO", "NEOGEO", "CPS1", "CPS2", "CPS3"):
            sys_aliases = ["MAME", "FBNEO", "ARCADE", "NEOGEO", "CPS1", "CPS2", "CPS3"]

        clean_q = re.sub(r'\(.*?\)|\[.*?\]', '', query).strip()
        words = [w.lower() for w in clean_q.split() if w]
        if not words:
            words = [w.lower() for w in query.strip().split() if w]
        if not words:
            if conn and hasattr(conn, "close"):
                conn.close()
            return []

        sig_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
        if not sig_words:
            sig_words = words

        placeholders = ",".join("?" * len(sys_aliases))

        def execute_query(w_list, use_sys=True):
            if use_sys:
                sql = f"SELECT title, img_url FROM games WHERE sys_code IN ({placeholders}) AND img_url IS NOT NULL AND img_url != ''"
                params = list(sys_aliases)
            else:
                sql = "SELECT title, img_url FROM games WHERE img_url IS NOT NULL AND img_url != ''"
                params = []
            for w in w_list[:4]:
                sql += " AND lower(title) LIKE ?"
                params.append(f"%{w}%")
            sql += f" LIMIT {max_results}"
            cur.execute(sql, params)
            return [r for r in cur.fetchall() if r[1] and "no-image" not in r[1].lower()]

        rows = execute_query(sig_words, use_sys=True)
        if not rows and len(sig_words) > 1:
            rows = execute_query(sig_words[:2], use_sys=True)

        # Thử tìm xuyên hệ máy nếu là game Arcade
        if not rows and sys_code.upper() in ("MAME", "ARCADE", "FBNEO", "NEOGEO", "CPS1", "CPS2", "CPS3", "DC"):
            rows = execute_query(sig_words[:2], use_sys=False)

        if conn and hasattr(conn, "close"):
            try:
                conn.close()
            except Exception:
                pass

        results = []
        for r in rows:
            results.append({
                "title": r[0],
                "type": "Catalog DB",
                "url": r[1]
            })
        return results
    except Exception:
        if conn and hasattr(conn, "close"):
            try:
                conn.close()
            except Exception:
                pass
        return []


def get_libretro_file_list(sys_folder, category="Named_Boxarts", allow_fetch=True):
    """Tải và cache danh sách file PNG từ Libretro Thumbnails CDN."""
    cache_key = f"{sys_folder}#{category}"
    with _CACHE_LOCK:
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
                        with _CACHE_LOCK:
                            _LIBRETRO_INDEX_CACHE[cache_key] = data
                        return data
        except Exception:
            pass

    if not allow_fetch:
        return []

    url = f"http://thumbnails.libretro.com/{urllib.parse.quote(sys_folder)}/{category}/"
    html = ""
    try:
        res = subprocess.run(["curl", "-s", "-k", "--max-time", "15", url], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=16)
        if res.returncode == 0 and res.stdout:
            html = res.stdout.decode("utf-8", errors="ignore")
    except Exception:
        pass

    if not html:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Connection": "close"})
            kwargs = {"timeout": 15}
            if _SSL_CONTEXT:
                kwargs["context"] = _SSL_CONTEXT
            with urllib.request.urlopen(req, **kwargs) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            pass

    if html:
        pattern = re.compile(r'href=\"([^\"/]+\.png)\"')
        files = pattern.findall(html)
        decoded = [urllib.parse.unquote(f) for f in files]
        if decoded:
            with _CACHE_LOCK:
                _LIBRETRO_INDEX_CACHE[cache_key] = decoded
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(decoded, f)
            except Exception:
                pass
            return decoded

    return []


def search_libretro_boxarts(sys_code, query, max_results=3, allow_fetch=True):
    """Tìm kiếm ảnh bìa trong Libretro Thumbnails CDN cache (~2ms)."""
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
    for cat in ["Named_Boxarts", "Named_Titles"]:
        files = get_libretro_file_list(sys_folder, category=cat, allow_fetch=allow_fetch)
        if not files:
            continue

        matches = [f for f in files if all(w in f.lower() for w in words)]
        if not matches and sig_words != words:
            matches = [f for f in files if all(w in f.lower() for w in sig_words)]

        if matches:
            matches.sort(key=score)
            cat_label = "Boxart" if cat == "Named_Boxarts" else "Title"
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

    return candidates


def search_web_bing(query):
    """Tìm kiếm ảnh bìa trực tiếp từ Bing Images (không bị chặn Captcha, timeout 5s)."""
    try:
        url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(query)
        cmd = [
            "curl", "-k", "-s", "--max-time", "5",
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            url
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=6)
        if res.returncode == 0 and res.stdout:
            html = res.stdout.decode("utf-8", errors="ignore")
            matches = re.findall(r'&quot;murl&quot;:&quot;(https?://[^&]+)&quot;', html)
            for m in matches:
                m_clean = m.split("?")[0].lower()
                if m_clean.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    return m
            if matches:
                return matches[0]
    except Exception:
        pass
    return None


def download_image_to_file(img_url, target_path, timeout=12):
    """Tải file ảnh từ URL về target_path và chuyển đổi chuẩn sang PNG."""
    if not img_url:
        return False, "Empty URL"
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": img_url,
    }

    raw_data = None
    try:
        req = urllib.request.Request(img_url, headers=headers)
        kwargs = {"timeout": timeout}
        if _SSL_CONTEXT:
            kwargs["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **kwargs) as resp:
            if resp.status in (200, 206):
                data = resp.read()
                if len(data) > 32:
                    raw_data = data
    except Exception:
        pass

    if not raw_data:
        try:
            cmd = [
                "curl", "-k", "-s", "-L",
                "--max-time", str(timeout),
                "-A", headers["User-Agent"],
                img_url
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout + 2)
            if res.returncode == 0 and res.stdout and len(res.stdout) > 32:
                raw_data = res.stdout
        except Exception:
            pass

    if raw_data:
        try:
            save_boxart_png(raw_data, target_path)
            return True, None
        except Exception:
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(raw_data)
                return True, None
            except Exception as e:
                return False, str(e)

    return False, "Download failed"


def find_best_boxart(sys_code, clean_title, filename="", fast_only=False):
    """Tìm ảnh bìa phù hợp nhất theo thứ tự tốc độ:
    1. SQLite Catalog DB: tra theo tên file ROM và tiêu đề đã làm sạch (~1ms)
    2. Libretro CDN index cache (~2ms)
    3. Bing Web Image Search nếu 2 nguồn trên không có (~0.5s)
    """
    # 1. Tra cứu Catalog DB
    try:
        db_res = search_catalog_db(sys_code, clean_title, filename=filename, max_results=1)
        if db_res and db_res[0].get("url"):
            return db_res[0]["url"], "Catalog DB"
    except Exception:
        pass

    # 2. Tra cứu Libretro CDN
    try:
        lr_res = search_libretro_boxarts(sys_code, clean_title, max_results=3, allow_fetch=True)
        for it in lr_res:
            u = it.get("url")
            if u and it.get("verified"):
                return u, it.get("type", "Libretro")
    except Exception:
        pass

    # 3. Tra cứu Bing Web Image Search (fallback cho bản dịch tiếng Việt, ROM hack, homebrew)
    if not fast_only:
        try:
            q = f"{clean_title} {sys_code} boxart cover"
            web_url = search_web_bing(q)
            if web_url:
                return web_url, "Web Search"
        except Exception:
            pass

    return None, None


def cleanup_rom_directory_images(base_sd=None):
    """
    Dọn dẹp sạch sẽ toàn bộ các file ảnh (.png, .jpg, .jpeg, .bmp, .webp) và thư mục .media
    đang vô tình nằm trong các thư mục ROMs (/mnt/SDCARD/Roms/).
    Tránh tình trạng trình quản lý game nhận nhầm file ảnh thành ROM game làm loạn danh sách.
    """
    sd = base_sd or SDCARD_PATH
    roms_dir = os.path.join(sd, "Roms")
    imgs_dir = os.path.join(sd, "Imgs")
    if not os.path.isdir(roms_dir):
        return 0

    cleaned_count = 0
    img_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    try:
        for sys_entry in os.listdir(roms_dir):
            sys_path = os.path.join(roms_dir, sys_entry)
            if not os.path.isdir(sys_path) or sys_entry.startswith("."):
                continue

            sys_code = sys_entry.upper()
            if "(" in sys_entry and sys_entry.endswith(")"):
                sys_code = sys_entry[sys_entry.rfind("(") + 1:-1].strip().upper()

            # PICO-8 sử dụng file .p8.png hoặc .png làm cart game, không dọn dẹp hệ này
            if sys_code == "PICO8":
                continue

            target_sys_imgs = os.path.join(imgs_dir, sys_entry)
            if not os.path.isdir(target_sys_imgs) and os.path.isdir(os.path.join(imgs_dir, sys_code)):
                target_sys_imgs = os.path.join(imgs_dir, sys_code)

            # Quét đệ quy toàn bộ thư mục của hệ máy này từ dưới lên
            for root, dirs, files in os.walk(sys_path, topdown=False):
                # 1. Dọn dẹp các file ảnh lạc trong thư mục ROM
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in img_exts:
                        full_p = os.path.join(root, f)
                        if not os.path.isdir(target_sys_imgs):
                            try:
                                os.makedirs(target_sys_imgs, exist_ok=True)
                            except Exception:
                                pass
                        dest_img = os.path.join(target_sys_imgs, f)
                        # Nếu trong Imgs chưa có ảnh này, copy sang trước khi xóa ở Roms
                        if not os.path.isfile(dest_img):
                            try:
                                shutil.copyfile(full_p, dest_img)
                            except Exception:
                                pass
                        try:
                            os.remove(full_p)
                            cleaned_count += 1
                        except Exception:
                            pass

                # 2. Xóa các thư mục .media nếu có
                for d in list(dirs):
                    if d == ".media":
                        media_dir = os.path.join(root, d)
                        try:
                            shutil.rmtree(media_dir, ignore_errors=True)
                            cleaned_count += 1
                        except Exception:
                            pass
    except Exception:
        pass

    return cleaned_count


def scan_missing_boxarts():
    """Quét toàn bộ game trên thẻ nhớ và trả về danh sách các game CHƯA có ảnh bìa."""
    cleanup_rom_directory_images()
    all_games = scan_all_downloaded_games()
    missing = []
    for g in all_games:
        img_p = g.get("img_path")
        if not img_p or not os.path.isfile(img_p):
            missing.append(g)
    return missing


def count_missing_boxarts():
    """Đếm nhanh số lượng game chưa có ảnh bìa."""
    try:
        return len(scan_missing_boxarts())
    except Exception:
        return 0


class BoxartScraperRunner:
    """Điều phối cào ảnh đa luồng song song (4 workers) chạy nền cho máy cầm tay."""

    def __init__(self):
        self.active = False
        self.done = False
        self.stop_requested = False
        self.total = 0
        self.completed = 0
        self.success_count = 0
        self.fail_count = 0
        self.progress_pct = 0
        self.current_title = ""
        self.current_sys = ""
        self.status_msg = ""
        self.worker_threads = []
        self._lock = threading.Lock()

    def is_running(self):
        return self.active and not self.done

    def get_state(self):
        with self._lock:
            return {
                "active": self.active,
                "running": self.is_running(),
                "done": self.done,
                "stop_requested": self.stop_requested,
                "total": self.total,
                "completed": self.completed,
                "success_count": self.success_count,
                "fail_count": self.fail_count,
                "progress_pct": self.progress_pct,
                "current_title": self.current_title,
                "current_sys": self.current_sys,
                "status_msg": self.status_msg,
            }

    def request_stop(self):
        self.stop_requested = True
        with self._lock:
            self.status_msg = "Đang dừng cào ảnh..."

    def start(self, items=None):
        if self.active and not self.done:
            return False

        if items is None:
            items = scan_missing_boxarts()

        if not items:
            return False

        self.active = True
        self.done = False
        self.stop_requested = False
        self.total = len(items)
        self.completed = 0
        self.success_count = 0
        self.fail_count = 0
        self.progress_pct = 0
        self.current_title = items[0].get("title", "")
        self.current_sys = items[0].get("sys_code", "")
        self.status_msg = "Bắt đầu cào ảnh tốc độ cao..."

        t = threading.Thread(target=self._run_batch, args=(items,), daemon=True)
        t.start()
        return True

    def _process_one(self, item):
        if self.stop_requested:
            return False

        sys_code = item.get("sys_code") or ""
        fname = item.get("filename") or ""
        base_name = item.get("title") or os.path.splitext(fname)[0]
        rom_path = item.get("rom_path") or ""

        clean_title = clean_rom_title(fname) or base_name

        with self._lock:
            self.current_title = base_name
            self.current_sys = sys_code
            self.status_msg = f"Đang tìm: {base_name} [{sys_code}]"

        success = False
        target_img_dir = os.path.join(SDCARD_PATH, "Imgs", sys_code)
        if rom_path:
            parts = rom_path.replace("\\", "/").split("/")
            if "Roms" in parts:
                idx = parts.index("Roms")
                if idx + 1 < len(parts):
                    sys_folder = parts[idx + 1]
                    candidate = os.path.join(SDCARD_PATH, "Imgs", sys_folder)
                    if os.path.isdir(candidate) or not os.path.isdir(target_img_dir):
                        target_img_dir = candidate

        os.makedirs(target_img_dir, exist_ok=True)
        target_art = os.path.join(target_img_dir, f"{base_name}.png")

        # 1. Trích xuất trực tiếp icon từ file .jar nếu là game Java J2ME
        if ((rom_path and rom_path.lower().endswith(".jar")) or sys_code.upper() == "JAVA") and rom_path:
            if extract_jar_icon(rom_path, target_art):
                success = True

        # 2. Nếu chưa có, tìm ảnh bìa online
        if not success:
            best_url, src_type = find_best_boxart(sys_code, clean_title, filename=fname, fast_only=False)
            if best_url:
                # Xóa các file ảnh định dạng cũ
                for old_ext in (".jpg", ".jpeg", ".webp", ".bmp"):
                    old_f = os.path.join(target_img_dir, f"{base_name}{old_ext}")
                    if os.path.isfile(old_f):
                        try:
                            os.remove(old_f)
                        except Exception:
                            pass

                ok, _ = download_image_to_file(best_url, target_art, timeout=10)
                if ok:
                    success = True

        with self._lock:
            self.completed += 1
            if self.total > 0:
                self.progress_pct = int((self.completed / self.total) * 100)
            if success:
                self.success_count += 1
            else:
                self.fail_count += 1

        return success

    def _run_batch(self, items):
        queue = list(items)
        q_lock = threading.Lock()

        def worker():
            while True:
                if self.stop_requested:
                    break
                with q_lock:
                    if not queue:
                        break
                    item = queue.pop(0)
                self._process_one(item)

        threads = []
        concurrency = min(4, len(items))
        for _ in range(concurrency):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        with self._lock:
            self.done = True
            self.active = False
            self.progress_pct = 100
            if self.stop_requested:
                self.status_msg = f"Đã dừng! Đã tải thành công {self.success_count}/{self.total} ảnh bìa."
            else:
                self.status_msg = f"Hoàn tất! Đã cập nhật thành công {self.success_count}/{self.total} ảnh bìa."


scraper_runner = BoxartScraperRunner()
