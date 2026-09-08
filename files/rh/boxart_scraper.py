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
    base = os.path.splitext(filename)[0]
    base = re.sub(r'[_\.\+]+', ' ', base)
    base = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]\s*', ' ', base)
    base = re.sub(r'\b(EUR|USA|JAP|JPN|PAL|NTSC|MULTi\d*|Goomba|Razor1911|Dump)\b', ' ', base, flags=re.IGNORECASE)
    base = re.sub(r'\b(PSP|PS1|PS2|GBA|NDS|SNES|NES|MD|GENESIS)\b', ' ', base, flags=re.IGNORECASE)
    base = re.sub(r'[-–—]+', ' ', base)
    return re.sub(r'\s+', ' ', base).strip()


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


def search_catalog_db(sys_code, query, max_results=1):
    """Tra cứu nhanh ảnh bìa trong Catalog DB SQLite (~1ms)."""
    db_p = get_catalog_db_path()
    if not db_p:
        return []
    conn = None
    try:
        conn = _get_sqlite_conn(db_p)
        if not conn:
            return []
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
            if conn and hasattr(conn, "close"):
                conn.close()
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

        rows = execute_query(words)
        if not rows and len(words) > 1:
            sig_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]
            if sig_words and sig_words != words:
                rows = execute_query(sig_words)

        if conn and hasattr(conn, "close"):
            try:
                conn.close()
            except Exception:
                pass
        results = []
        for title, img_url in rows:
            results.append({
                "title": title,
                "type": "Catalog DB",
                "url": img_url
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

    return candidates


def download_image_to_file(img_url, target_path, timeout=12):
    """Tải file ảnh từ URL về đường dẫn target_path."""
    if not img_url:
        return False, "Empty URL"
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": img_url,
    }

    try:
        req = urllib.request.Request(img_url, headers=headers)
        kwargs = {"timeout": timeout}
        if _SSL_CONTEXT:
            kwargs["context"] = _SSL_CONTEXT
        with urllib.request.urlopen(req, **kwargs) as resp:
            if resp.status in (200, 206):
                data = resp.read()
                if len(data) > 32:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, "wb") as f:
                        f.write(data)
                    return True, None
    except Exception:
        pass

    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
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

    return False, "Download failed"


def find_best_boxart(sys_code, clean_title, fast_only=True):
    """Tìm ảnh bìa phù hợp nhất theo thứ tự tốc độ."""
    try:
        db_res = search_catalog_db(sys_code, clean_title, max_results=1)
        if db_res and db_res[0].get("url"):
            return db_res[0]["url"], "Catalog DB"
    except Exception:
        pass

    try:
        lr_res = search_libretro_boxarts(sys_code, clean_title, max_results=3, allow_fetch=True)
        for it in lr_res:
            u = it.get("url")
            if u and it.get("verified"):
                return u, it.get("type", "Libretro")
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

        best_url, src_type = find_best_boxart(sys_code, clean_title, fast_only=True)
        success = False

        if best_url:
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
