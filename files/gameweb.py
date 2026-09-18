#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# RETROHUB - WEB GAME MANAGER & MEDIA CENTER (PORT 8090)
# 1. Quản lý game: Đổi tên, Chuyển hệ, Xóa ROM, Cào ảnh Box Art, Sao lưu Save, Cheat Code, Logs
# 2. Tải game online: Kho 40,000+ ROMs từ Catalog DB, lọc hệ máy / danh mục, tải trực tiếp về thẻ nhớ
# 3. Quản lý playlist YouTube: Quản lý danh sách phát / chủ đề tìm kiếm, video Yêu thích, tìm kiếm video online
# Hoàn toàn thuần Python stdlib - Zero external dependencies - Siêu nhẹ, mượt mà
# ==============================================================================

import os
import sys
import re
import time
import json
import shutil
import signal
import atexit
import subprocess
import urllib.request
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

try:
    _SSL_CONTEXT = None
    
    
except Exception:
    _SSL_CONTEXT = None

PORT = 8888

_cur_d = os.path.dirname(os.path.abspath(__file__))
if _cur_d not in sys.path:
    sys.path.insert(0, _cur_d)

try:
    from rh import state, yt
    from rh.paths import (
        SDCARD_PATH,
        ROMS_DIR,
        IMGS_DIR,
        EMUS_DIR,
        APP_DIR,
        WEB_DIR,
        resolve_rom_dir,
        YT_HISTORY_FILE,
        YT_FAVORITES_FILE,
        get_yt_cache_dir,
    )
    from rh.save_manager import (
        scan_all_saves,
        get_saves_stats,
        create_save_backup,
        list_save_backups,
        restore_save_backup,
        delete_save_backup,
    )
    from rh.cheat_manager import (
        get_cheats_status,
        count_cheats,
        cheat_runner,
        check_or_download_single_cheat,
    )
    from rh.logger import (
        upload_log_to_telegram,
        generate_debug_report,
        LOG_FILE,
        clear_log,
        get_log_size_str,
        get_device_id,
        sync_retroarch_logging,
    )
    from rh.boxart_scraper import cleanup_rom_directory_images
    from rh.media import save_boxart_png
    from rh.theme_manager import (
        load_themes_catalog,
        install_theme,
        uninstall_theme,
        get_theme_preview_path,
    )
    from rh.icon_manager import (
        load_icons_catalog,
        install_icon_pack,
        restore_stock_icons,
        get_icon_preview_path,
        has_stock_backup,
    )
    from rh.emulator_store import (
        get_emus_status,
        install_emu,
        uninstall_emu,
    )
    import db
except ImportError:
    # Standalone mock fallbacks
    try:
        from rh.theme_manager import (
            load_themes_catalog,
            install_theme,
            uninstall_theme,
            get_theme_preview_path,
        )
        from rh.icon_manager import (
            load_icons_catalog,
            install_icon_pack,
            restore_stock_icons,
            get_icon_preview_path,
            has_stock_backup,
        )
    except Exception:
        def load_themes_catalog(): return []
        def install_theme(t): return False, "Not supported"
        def uninstall_theme(t): return False, "Not supported"
        def get_theme_preview_path(t): return None
        def load_icons_catalog(): return []
        def install_icon_pack(t): return False, "Not supported"
        def restore_stock_icons(): return False, "Not supported"
        def get_icon_preview_path(t): return None
        def has_stock_backup(): return False
    SDCARD_PATH = os.environ.get("SDCARD_PATH") or (
        "/mnt/SDCARD"
        if os.path.isdir("/mnt/SDCARD")
        else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "_mock_sdcard",
        )
    )
    ROMS_DIR = os.path.join(SDCARD_PATH, "Roms")
    IMGS_DIR = os.path.join(SDCARD_PATH, "Imgs")
    EMUS_DIR = os.path.join(SDCARD_PATH, "Emus")
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    WEB_DIR = os.path.join(APP_DIR, "web")
    YT_HISTORY_FILE = os.path.join(APP_DIR, "yt_history.json")
    YT_FAVORITES_FILE = os.path.join(
        SDCARD_PATH, ".retrohub", "yt_favorites.json"
    )

    def resolve_rom_dir(sys_code):
        return os.path.join(ROMS_DIR, sys_code)

    def get_yt_cache_dir():
        return os.path.join(SDCARD_PATH, ".retrohub", "cache", "yt_thumbs")

    import db

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
    "FC": "Nintendo - Nintendo Entertainment System",
    "NES": "Nintendo - Nintendo Entertainment System",
    "SFC": "Nintendo - Super Nintendo Entertainment System",
    "SNES": "Nintendo - Super Nintendo Entertainment System",
    "GBA": "Nintendo - Game Boy Advance",
    "GBC": "Nintendo - Game Boy Color",
    "GB": "Nintendo - Game Boy",
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
    "MAME": "FBNeo - Arcade Games",
    "ARCADE": "FBNeo - Arcade Games",
    "CPS1": "Capcom - CP System I",
    "CPS2": "Capcom - CP System II",
    "CPS3": "Capcom - CP System III",
    "NEOGEO": "SNK - Neo Geo",
    "ATARI2600": "Atari - 2600",
    "ATARI7800": "Atari - 7800",
    "LYNX": "Atari - Lynx",
}

# Đuôi file ROM hợp lệ thường gặp
VALID_EXTS = {
    ".zip",
    ".7z",
    ".rar",
    ".chd",
    ".iso",
    ".cue",
    ".bin",
    ".pbp",
    ".gba",
    ".gbc",
    ".gb",
    ".nes",
    ".sfc",
    ".smc",
    ".md",
    ".smd",
    ".gen",
    ".n64",
    ".z64",
    ".v64",
    ".nds",
    ".cso",
    ".pce",
    ".ws",
    ".wsc",
    ".ngp",
    ".ngc",
    ".p8",
    ".jar",
    ".a26",
    ".a78",
    ".lnx",
}


def get_catalog_db_path():
  candidates = [
      os.path.join(
          SDCARD_PATH, "Apps", "RetroHub", "catalog", "roms_store.sqlite3"
      ),
      os.path.join(SDCARD_PATH, "RetroHub", "catalog", "roms_store.sqlite3"),
      os.path.join(
          os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
          "catalog",
          "roms_store.sqlite3",
      ),
      os.path.join(
          os.path.dirname(os.path.abspath(__file__)),
          "catalog",
          "roms_store.sqlite3",
      ),
  ]
  for p in candidates:
    if os.path.isfile(p):
      return p

  ensure_catalog_extracted()
  for p in candidates:
    if os.path.isfile(p):
      return p
  return None


def ensure_catalog_extracted():
  gz_candidates = [
      os.path.join(
          SDCARD_PATH, "Apps", "RetroHub", "catalog", "roms_store.sqlite3.gz"
      ),
      os.path.join(SDCARD_PATH, "RetroHub", "catalog", "roms_store.sqlite3.gz"),
      os.path.join(
          os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
          "catalog",
          "roms_store.sqlite3.gz",
      ),
      os.path.join(
          os.path.dirname(os.path.abspath(__file__)),
          "catalog",
          "roms_store.sqlite3.gz",
      ),
  ]
  for gz_p in gz_candidates:
    if os.path.isfile(gz_p):
      out_db = gz_p[:-3]
      if not os.path.isfile(out_db) or os.path.getsize(out_db) < 1000:
        try:
          import gzip

          print(f"[*] Đang giải nén database từ {gz_p}...")
          with gzip.open(gz_p, "rb") as f_in, open(out_db, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
          print(f"[+] Đã giải nén database thành công: {out_db}")
          return out_db
        except Exception as e:
          print(f"[-] Lỗi giải nén catalog db: {e}")
  return None


def search_catalog_db(sys_code, query, filename="", max_results=8):
  db_p = get_catalog_db_path()
  if not db_p or not os.path.isfile(db_p):
    return []

  candidates = []
  clean_q = re.sub(r"[^\w\s]", " ", query).strip()

  try:
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT title, img_url FROM games WHERE sys_code = ? AND (clean_title"
        " LIKE ? OR title LIKE ?) AND img_url IS NOT NULL AND img_url != ''"
        " LIMIT ?",
        (sys_code, f"%{clean_q}%", f"%{query}%", max_results),
    )
    rows = cur.fetchall()
    for r in rows:
      if r["img_url"]:
        candidates.append({
            "title": r["title"],
            "url": r["img_url"],
            "type": "Catalog DB",
        })

    if filename and len(candidates) < max_results:
      cur.execute(
          "SELECT g.title, g.img_url FROM games g JOIN game_sources s ON"
          " s.game_id = g.id WHERE g.sys_code = ? AND s.filename LIKE ? AND"
          " g.img_url IS NOT NULL AND g.img_url != '' LIMIT ?",
          (sys_code, f"%{filename}%", max_results - len(candidates)),
      )
      rows = cur.fetchall()
      for r in rows:
        if r["img_url"]:
          candidates.append({
              "title": r["title"],
              "url": r["img_url"],
              "type": "Catalog DB",
          })
    conn.close()
  except Exception as e:
    print(f"Error querying catalog db: {e}")

  return candidates


# Quản lý Background Download cho Online Store
STORE_DOWNLOADS = {}
STORE_DOWNLOADS_LOCK = threading.Lock()


def background_download_store_game(
    dl_id, sys_code, game_title, rom_url, filename, img_url
):
  with STORE_DOWNLOADS_LOCK:
    STORE_DOWNLOADS[dl_id] = {
        "id": dl_id,
        "title": game_title,
        "sys_code": sys_code,
        "filename": filename,
        "status": "downloading",
        "progress_pct": 0,
        "speed_str": "0 KB/s",
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "error_msg": "",
    }

  try:
    target_rom_dir = resolve_rom_dir(sys_code)
  except Exception:
    target_rom_dir = os.path.join(ROMS_DIR, sys_code)
  os.makedirs(target_rom_dir, exist_ok=True)
  target_rom_path = os.path.join(target_rom_dir, filename)

  target_img_dir = os.path.join(IMGS_DIR, sys_code)
  os.makedirs(target_img_dir, exist_ok=True)
  base_name = os.path.splitext(filename)[0]
  target_img_path = os.path.join(target_img_dir, base_name + ".png")

  # 1. Tải ảnh Box Art (nếu có)
  if img_url:
    try:
      download_image_to_file(img_url, target_img_path, timeout=10)
    except Exception as e:
      print(f"Store download boxart error: {e}")

  # 2. Tải ROM game bằng curl với theo dõi dung lượng và tốc độ thực tế
  temp_rom_path = target_rom_path + ".tmp_dl"
  if os.path.exists(temp_rom_path):
    try:
      os.remove(temp_rom_path)
    except Exception:
      pass

  try:
    # Lấy kích thước Content-Length trước qua curl HEAD
    total_sz = 0
    try:
      head_cmd = [
          "curl", "-s", "-I", "-k", "-L", "--max-time", "6",
          "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          "-e", rom_url,
          rom_url
      ]
      head_res = subprocess.run(head_cmd, capture_output=True, text=True)
      for line in head_res.stdout.splitlines():
        if line.lower().startswith("content-length:"):
          total_sz = int(line.split(":", 1)[1].strip())
    except Exception:
      total_sz = 0

    with STORE_DOWNLOADS_LOCK:
      STORE_DOWNLOADS[dl_id]["total_bytes"] = total_sz

    # Chạy tiến trình curl tải ROM
    dl_cmd = [
        "curl", "-s", "-k", "-L",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-e", rom_url,
        "-o", temp_rom_path,
        rom_url
    ]
    proc = subprocess.Popen(dl_cmd)

    t_last = time.time()
    b_last = 0

    # Vòng lặp theo dõi tiến độ ghi file vào thẻ nhớ
    while proc.poll() is None:
      time.sleep(0.3)
      if os.path.exists(temp_rom_path):
        cur_sz = os.path.getsize(temp_rom_path)
        now = time.time()
        elapsed = max(0.001, now - t_last)
        if elapsed >= 0.4:
          speed = (cur_sz - b_last) / elapsed
          speed_str = (
              f"{speed / (1024*1024):.1f} MB/s"
              if speed > 1024 * 1024
              else f"{int(speed / 1024)} KB/s"
          )
          pct = int((cur_sz / total_sz) * 100) if total_sz > 0 else min(95, int(cur_sz / (1024*1024) * 8))
          with STORE_DOWNLOADS_LOCK:
            STORE_DOWNLOADS[dl_id]["progress_pct"] = max(1, min(99, pct))
            STORE_DOWNLOADS[dl_id]["downloaded_bytes"] = cur_sz
            STORE_DOWNLOADS[dl_id]["speed_str"] = speed_str
          t_last = now
          b_last = cur_sz

    ret_code = proc.wait()
    if ret_code != 0:
      raise RuntimeError(f"Lỗi mạng khi tải (Curl exit code: {ret_code})")

    final_sz = os.path.getsize(temp_rom_path) if os.path.exists(temp_rom_path) else 0
    if final_sz < 64:
      raise RuntimeError("File tải về rỗng hoặc lỗi kết nối máy chủ")

    if os.path.exists(temp_rom_path):
      os.replace(temp_rom_path, target_rom_path)

    with STORE_DOWNLOADS_LOCK:
      STORE_DOWNLOADS[dl_id]["status"] = "completed"
      STORE_DOWNLOADS[dl_id]["progress_pct"] = 100
      STORE_DOWNLOADS[dl_id]["downloaded_bytes"] = final_sz
      STORE_DOWNLOADS[dl_id]["speed_str"] = "Xong"

  except Exception as e:
    print(f"Store download ROM error: {e}")
    if os.path.exists(temp_rom_path):
      try:
        os.remove(temp_rom_path)
      except Exception:
        pass
    with STORE_DOWNLOADS_LOCK:
      STORE_DOWNLOADS[dl_id]["status"] = "error"
      STORE_DOWNLOADS[dl_id]["error_msg"] = str(e)


# Helper kiểm tra dung lượng thẻ nhớ
def get_sd_storage():
  try:
    st = shutil.disk_usage(SDCARD_PATH)
    free_gb = st.free / (1024**3)
    total_gb = st.total / (1024**3)
    used_gb = st.used / (1024**3)
    return {
        "free_gb": f"{free_gb:.2f} GB",
        "total_gb": f"{total_gb:.2f} GB",
        "used_gb": f"{used_gb:.2f} GB",
        "pct_used": int((st.used / st.total) * 100),
    }
  except Exception:
    return {
        "free_gb": "N/A",
        "total_gb": "N/A",
        "used_gb": "N/A",
        "pct_used": 0,
    }


def clean_rom_title(fname):
  base = os.path.splitext(fname)[0]
  base = re.sub(r"^\d+\s*[-–—.]\s*", "", base)
  cleaned = re.sub(r"\(.*?\)|\[.*?\]", "", base).strip()
  return cleaned if cleaned else base


def search_libretro_boxarts(
    sys_code, clean_title, max_results=8, allow_fetch=True
):
  libretro_sys = LIBRETRO_MAP.get(sys_code)
  if not libretro_sys:
    return []
  enc_sys = urllib.parse.quote(libretro_sys)
  enc_title = urllib.parse.quote(clean_title)
  url = f"https://thumbnails.libretro.com/{enc_sys}/Named_Boxarts/{enc_title}.png"
  return [{
      "title": f"{clean_title} (Libretro)",
      "url": url,
      "type": "Libretro CDN",
      "verified": False,
  }]


def search_web_images(query, max_results=8):
  results = []
  try:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    url = (
        "https://www.bing.com/images/search?q="
        + urllib.parse.quote(query)
        + "&FORM=HDRSC2"
    )
    req = urllib.request.Request(url, headers=headers)
    kwargs = {"timeout": 6}
    if _SSL_CONTEXT:
      kwargs["context"] = _SSL_CONTEXT

    with urllib.request.urlopen(req, **kwargs) as resp:
      html_doc = resp.read().decode("utf-8", "ignore")

    matches = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html_doc)
    for m in matches:
      if m not in [r["url"] for r in results]:
        results.append({"title": query, "url": m, "type": "Web Search"})
        if len(results) >= max_results:
          break
  except Exception as e:
    print(f"Web image search error: {e}")
  return results


def find_best_boxart(sys_code, clean_title, filename="", fast_only=False):
  # 1. SQLite Catalog DB
  try:
    db_res = search_catalog_db(
        sys_code, clean_title, filename=filename, max_results=1
    )
    if db_res and db_res[0].get("url"):
      return db_res[0]["url"], "Catalog DB"
  except Exception as e:
    print(f"find_best_boxart db error: {e}")

  # 2. Libretro CDN index cache
  try:
    lr_res = search_libretro_boxarts(
        sys_code, clean_title, max_results=3, allow_fetch=True
    )
    if lr_res and lr_res[0].get("url"):
      return lr_res[0]["url"], "Libretro CDN"
  except Exception as e:
    print(f"find_best_boxart libretro error: {e}")

  # 3. Web Images Search
  if not fast_only:
    try:
      web_q = f"{clean_title} {sys_code} boxart cover"
      web_res = search_web_images(web_q, max_results=2)
      if web_res and web_res[0].get("url"):
        return web_res[0]["url"], "Web Search"
    except Exception as e:
      print(f"find_best_boxart web error: {e}")

  return None, None


def is_valid_rom_file(fname, sys_dir=""):
  name, ext = os.path.splitext(fname)
  ext_l = ext.lower()
  if ext_l in VALID_EXTS:
    return True
  if ext_l == ".png":
    sys_code = sys_dir.upper()
    if "(" in sys_code and sys_code.endswith(")"):
      sys_code = sys_code[sys_code.rfind("(") + 1 : -1].strip().upper()
    return sys_code == "PICO8"
  return False


def download_image_to_file(img_url, target_path, timeout=15):
  if img_url.startswith("//"):
    img_url = "https:" + img_url

  raw_data = None
  try:
    cmd = [
        "curl", "-s", "-L", "-k", "--max-time", str(timeout),
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-e", img_url,
        img_url
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and len(res.stdout) > 64:
      raw_data = res.stdout
  except Exception:
    pass

  if not raw_data or len(raw_data) < 64:
    return False, "Empty or invalid image data"

  try:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    save_boxart_png(raw_data, target_path)
    return True, ""
  except Exception as e:
    try:
      with open(target_path, "wb") as f:
        f.write(raw_data)
      return True, ""
    except Exception as e2:
      return False, str(e2)


def extract_jar_icon(jar_path, target_png):
  try:
    import zipfile

    with zipfile.ZipFile(jar_path, "r") as z:
      icon_name = None
      for n in ("icon.png", "i.png", "res/icon.png", "icons/icon.png"):
        if n in z.namelist():
          icon_name = n
          break
      if not icon_name:
        for n in z.namelist():
          if "icon" in n.lower() and n.lower().endswith(".png"):
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


def list_all_systems():
  systems = []
  if not os.path.isdir(ROMS_DIR):
    return systems

  try:
    dirs = sorted(os.listdir(ROMS_DIR))
  except OSError:
    dirs = []

  for d in dirs:
    if d.startswith("."):
      continue
    full_p = os.path.join(ROMS_DIR, d)
    if os.path.isdir(full_p):
      tag = d
      if "(" in d and d.endswith(")"):
        extracted = d[d.rfind("(") + 1 : -1].strip().upper()
        if extracted:
          tag = extracted
      tag_u = tag.upper()

      rom_count = 0
      has_art_count = 0
      img_d = os.path.join(IMGS_DIR, d)

      scan_dirs = [full_p]
      try:
        for sub in sorted(os.listdir(full_p)):
          sub_p = os.path.join(full_p, sub)
          if os.path.isdir(sub_p) and not sub.startswith("."):
            scan_dirs.append(sub_p)
      except Exception:
        pass

      for s_dir in scan_dirs:
        try:
          for f in os.listdir(s_dir):
            if is_valid_rom_file(f, d):
              rom_count += 1
              base = os.path.splitext(f)[0]
              art_found = False
              if os.path.isdir(img_d):
                for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                  if os.path.isfile(os.path.join(img_d, base + ext)):
                    art_found = True
                    break
              if not art_found:
                sub_media = os.path.join(s_dir, ".media", base + ".png")
                if os.path.isfile(sub_media):
                  art_found = True
              if art_found:
                has_art_count += 1
        except Exception:
          pass

      name_display = SYSTEM_NAMES.get(tag_u, d)
      systems.append({
          "dir": d,
          "tag": tag_u,
          "name": name_display,
          "count": rom_count,
          "has_art_count": has_art_count,
          "no_art_count": max(0, rom_count - has_art_count),
      })
  return systems


def list_system_games(sys_dir):
  games = []
  rom_dir = os.path.join(ROMS_DIR, sys_dir)
  img_dir = os.path.join(IMGS_DIR, sys_dir)

  if not os.path.isdir(rom_dir):
    return games

  scan_dirs = [rom_dir]
  try:
    for sub in sorted(os.listdir(rom_dir)):
      sub_p = os.path.join(rom_dir, sub)
      if os.path.isdir(sub_p) and not sub.startswith("."):
        scan_dirs.append(sub_p)
  except Exception:
    pass

  for s_dir in scan_dirs:
    try:
      files = sorted(os.listdir(s_dir))
    except Exception:
      files = []

    for f in files:
      if not is_valid_rom_file(f, sys_dir):
        continue
      full_f = os.path.join(s_dir, f)
      try:
        sz = os.path.getsize(full_f)
      except Exception:
        sz = 0
      sz_str = (
          f"{sz / (1024*1024):.1f} MB"
          if sz > 1024 * 1024
          else f"{sz // 1024} KB"
      )

      base = os.path.splitext(f)[0]
      art_url = ""
      has_art = False

      if os.path.isdir(img_dir):
        for ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
          art_file = os.path.join(img_dir, base + ext)
          if os.path.isfile(art_file):
            has_art = True
            art_url = f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base + ext)}?v={int(os.path.getmtime(art_file))}"
            break

      if not has_art:
        sub_media = os.path.join(s_dir, ".media", base + ".png")
        if os.path.isfile(sub_media):
          has_art = True
          art_url = f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base + '.png')}?v={int(os.path.getmtime(sub_media))}"

      games.append({
          "filename": f,
          "title": clean_rom_title(f),
          "size_str": sz_str,
          "has_art": has_art,
          "art_url": art_url,
          "system": sys_dir,
      })
  return games


def list_all_missing_art_games():
  missing = []
  systems = list_all_systems()
  for sys_info in systems:
    s_dir = sys_info["dir"]
    g_list = list_system_games(s_dir)
    for g in g_list:
      if not g["has_art"]:
        missing.append(g)
  return missing


# ==============================================================================
# HTTP HANDLER
# ==============================================================================
class GameWebHandler(BaseHTTPRequestHandler):

  def send_json(self, data, status_code=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    self.send_response(status_code)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(body)

  def do_OPTIONS(self):
    self.send_response(200)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header(
        "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
    )
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.end_headers()

  def do_GET(self):
    parsed = urllib.parse.urlparse(self.path)
    path = parsed.path
    query = urllib.parse.parse_qs(parsed.query)

    if path in ("/", "/index.html", "/style.css", "/app.js"):
      file_map = {
          "/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "application/javascript; charset=utf-8"),
      }
      rel_f, ctype = file_map.get(path, ("index.html", "text/html; charset=utf-8"))
      target_file = os.path.join(WEB_DIR, rel_f)
      if os.path.isfile(target_file):
        try:
          with open(target_file, "rb") as sf:
            body = sf.read()
          self.send_response(200)
          self.send_header("Content-Type", ctype)
          self.send_header("Content-Length", str(len(body)))
          self.send_header("Cache-Control", "no-cache")
          self.end_headers()
          self.wfile.write(body)
          return
        except Exception as e:
          print(f"Error serving {rel_f}: {e}")
      self.send_response(404)
      self.end_headers()
      return

    if path == "/api/status":
      st = get_sd_storage()
      self.send_json({"ok": True, "storage": st})
      return

    if path == "/api/themes":
      themes = load_themes_catalog()
      self.send_json({"ok": True, "themes": themes, "total": len(themes)})
      return

    if path == "/api/themes/preview":
      name = query.get("name", [""])[0] or query.get("folder", [""])[0]
      if name:
        prev_p = get_theme_preview_path(name)
        if prev_p and os.path.isfile(prev_p):
          try:
            with open(prev_p, "rb") as pf:
              img_data = pf.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(img_data)))
            self.end_headers()
            self.wfile.write(img_data)
            return
          except Exception as e:
            print(f"Error streaming theme preview: {e}")
      self.send_response(404)
      self.end_headers()
      return

    if path == "/api/icons":
      icons = load_icons_catalog()
      self.send_json({"ok": True, "icons": icons, "total": len(icons), "has_backup": has_stock_backup()})
      return

    if path == "/api/icons/preview":
      name = query.get("name", [""])[0] or query.get("folder", [""])[0]
      if name:
        prev_p = get_icon_preview_path(name)
        if prev_p and os.path.isfile(prev_p):
          try:
            with open(prev_p, "rb") as pf:
              img_data = pf.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("Content-Length", str(len(img_data)))
            self.end_headers()
            self.wfile.write(img_data)
            return
          except Exception as e:
            print(f"Error streaming icon preview: {e}")
      self.send_response(404)
      self.end_headers()
      return

    if path == "/api/emus":
      try:
        emus = get_emus_status()
        installed_count = sum(1 for e in emus if e.get("installed"))
        self.send_json({
            "ok": True,
            "emus": emus,
            "total": len(emus),
            "installed_count": installed_count,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/saves":
      self.send_json({
          "ok": True,
          "stats": get_saves_stats(),
          "backups": list_save_backups(),
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
            self.send_header(
                "Content-Disposition", f'attachment; filename="{fname}"'
            )
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
          "runner": cheat_runner.get_state(),
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
          self.send_header(
              "Content-Disposition",
              f'attachment; filename="{os.path.basename(rep_path)}"',
          )
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
          "log_size": get_log_size_str(),
      })
      return

    if path == "/api/systems":
      systems = list_all_systems()
      no_art_games = list_all_missing_art_games()
      self.send_json(
          {"ok": True, "systems": systems, "no_art_count": len(no_art_games)}
      )
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

      db_results = search_catalog_db(sys_code, q_name, max_results=6)
      for item in db_results:
        if item["url"] not in seen_urls:
          candidates.append(item)
          seen_urls.add(item["url"])

      allow_fetch = len(candidates) < 6
      libretro_results = search_libretro_boxarts(
          sys_code, q_name, max_results=8, allow_fetch=allow_fetch
      )
      for item in libretro_results:
        if item["url"] not in seen_urls:
          candidates.append(item)
          seen_urls.add(item["url"])

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
          "candidates": candidates,
      })
      return

    # ==================== STORE API ====================
    if path == "/api/store/categories":
      ensure_catalog_extracted()
      counts = []
      try:
        counts = db.get_source_systems_counts("ALL")
      except Exception as e:
        print(f"Error get_source_systems_counts: {e}")

      systems_data = []
      for code, cnt in counts:
        if code == "ALL":
          continue
        name = SYSTEM_NAMES.get(code, code)
        systems_data.append({"code": code, "name": name, "count": cnt})

      self.send_json({
          "ok": True,
          "categories": [
              {
                  "id": "HITS",
                  "name": "Top 100 game hay nhất",
                  "icon": "🌟",
                  "desc": "Tuyển tập 100 game kinh điển nhiều lượt chơi nhất",
              },
              {
                  "id": "VIET",
                  "name": "Game Việt hóa",
                  "icon": "🇻🇳",
                  "desc": "Các bản dịch Tiếng Việt chất lượng cao",
              },
              {
                  "id": "HACK",
                  "name": "Kho game hack",
                  "icon": "⚡",
                  "desc": "Pokemon Custom, Mario Hacks, Romhacks",
              },
              {
                  "id": "JAVA",
                  "name": "Game Java (J2ME)",
                  "icon": "📱",
                  "desc": "2,800+ Game điện thoại di động Nokia cổ",
              },
              {
                  "id": "RETROSTIC",
                  "name": "Kho game RETROSTIC",
                  "icon": "🕹️",
                  "desc": "Kho tổng hợp đa hệ máy phong phú",
              },
              {
                  "id": "ARCHIVE",
                  "name": "Kho Archive.org",
                  "icon": "🏛️",
                  "desc": "Kho lưu trữ Internet Archive bảo tồn game",
              },
          ],
          "systems": systems_data,
      })
      return

    if path == "/api/store/games":
      source_type = query.get("source_type", ["ALL"])[0]
      sys_code = query.get("system", ["ALL"])[0]
      query_str = query.get("query", [""])[0].strip()
      sort_by = query.get("sort", ["downloads"])[0]
      try:
        page = int(query.get("page", ["1"])[0])
        limit = int(query.get("limit", ["40"])[0])
      except ValueError:
        page = 1
        limit = 40
      offset = (page - 1) * limit

      ensure_catalog_extracted()
      games = []
      try:
        if query_str:
          eff_source = "ALL" if source_type in ("HITS", "ALL", "") else source_type
          games = db.search_games_fts(
              query_str,
              sys_code=sys_code,
              limit=limit,
              source_type=eff_source,
              offset=offset,
          )
        else:
          games = db.get_games_page(
              source_type=source_type,
              sys_code=sys_code,
              sort_by=sort_by,
              limit=limit,
              offset=offset,
          )
      except Exception as e:
        print(f"Error get store games: {e}")
        games = []

      for g in games:
        g_sys = g.get("sys_code", "")
        g_fn = g.get("filename", "")
        is_installed = False
        if g_sys and g_fn:
          try:
            r_dir = resolve_rom_dir(g_sys)
            if os.path.isfile(os.path.join(r_dir, g_fn)):
              is_installed = True
          except Exception:
            pass
        g["is_installed"] = is_installed

      self.send_json({
          "ok": True,
          "page": page,
          "limit": limit,
          "games": games,
          "count": len(games),
      })
      return

    if path == "/api/store/download/status":
      with STORE_DOWNLOADS_LOCK:
        active_list = list(STORE_DOWNLOADS.values())
      self.send_json({"ok": True, "downloads": active_list})
      return

    # ==================== YOUTUBE API ====================
    if path == "/api/youtube/playlists":
      history = []
      favorites = []
      try:
        history = yt.load_search_history() or []
      except Exception as e:
        print(f"Error loading yt history: {e}")
      try:
        favorites = yt.load_favorites() or []
      except Exception as e:
        print(f"Error loading yt favorites: {e}")

      self.send_json({
          "ok": True,
          "playlists": history,
          "favorites": favorites,
          "favorites_count": len(favorites),
      })
      return

    if path == "/api/youtube/favorites":
      favorites = []
      try:
        favorites = yt.load_favorites() or []
      except Exception as e:
        print(f"Error loading yt favorites: {e}")
      self.send_json(
          {"ok": True, "favorites": favorites, "count": len(favorites)}
      )
      return

    if path == "/api/youtube/search":
      q = query.get("q", [""])[0].strip()
      try:
        limit = int(query.get("limit", ["24"])[0])
      except ValueError:
        limit = 24

      videos = []
      if q.lower() in ("trending", "thịnh hành", "top"):
        videos = yt.get_trending(limit=limit) or []
      elif q:
        cached, _ = yt.load_feed_cache(q)
        if cached:
          videos = cached
        else:
          videos = yt.search_youtube(q, limit=limit) or []

      self.send_json(
          {"ok": True, "query": q, "videos": videos, "count": len(videos)}
      )
      return

    self.send_response(404)
    self.end_headers()

  def do_POST(self):
    parsed = urllib.parse.urlparse(self.path)
    path = parsed.path
    query = urllib.parse.parse_qs(parsed.query)
    content_len = int(self.headers.get("Content-Length", 0))

    if path == "/api/themes/install":
      try:
        payload = {}
        if content_len > 0:
          payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        folder = payload.get("folder") or payload.get("id") or query.get("folder", [""])[0]
        if not folder:
          self.send_json({"ok": False, "error": "Thiếu tên thư mục theme!"}, 400)
          return
        ok, msg = install_theme({"folder": folder})
        if ok:
          self.send_json({"ok": True, "message": msg})
        else:
          self.send_json({"ok": False, "error": msg}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/themes/restore":
      self.send_json({"ok": True, "message": "Tính năng backup/khôi phục theme đã được thay thế bằng tải trực tiếp từ Theme Store."})
      return

    if path == "/api/themes/delete":
      try:
        payload = {}
        if content_len > 0:
          payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        folder = payload.get("folder") or payload.get("id") or query.get("folder", [""])[0]
        if not folder:
          self.send_json({"ok": False, "error": "Thiếu tên thư mục theme!"}, 400)
          return
        ok, msg = uninstall_theme(folder)
        if ok:
          self.send_json({"ok": True, "message": msg})
        else:
          self.send_json({"ok": False, "error": msg}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/icons/install":
      try:
        payload = {}
        if content_len > 0:
          payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        folder = payload.get("folder") or payload.get("id") or query.get("folder", [""])[0]
        if not folder:
          self.send_json({"ok": False, "error": "Thiếu tên thư mục icon pack!"}, 400)
          return
        ok, msg = install_icon_pack({"folder": folder})
        if ok:
          self.send_json({"ok": True, "message": msg})
        else:
          self.send_json({"ok": False, "error": msg}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/icons/restore":
      try:
        ok, msg = restore_stock_icons()
        if ok:
          self.send_json({"ok": True, "message": msg})
        else:
          self.send_json({"ok": False, "error": msg}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/emus/install":
      try:
        payload = {}
        if content_len > 0:
          payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        sys_id = payload.get("sys_id") or payload.get("id") or query.get("sys_id", [""])[0]
        if not sys_id:
          self.send_json({"ok": False, "error": "Thiếu mã hệ máy sys_id!"}, 400)
          return
        res = install_emu(sys_id)
        if res.get("success"):
          self.send_json({"ok": True, "message": res.get("message"), "data": res})
        else:
          self.send_json({"ok": False, "error": res.get("error", "Cài đặt thất bại")}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/emus/uninstall":
      try:
        payload = {}
        if content_len > 0:
          payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        sys_id = payload.get("sys_id") or payload.get("id") or query.get("sys_id", [""])[0]
        if not sys_id:
          self.send_json({"ok": False, "error": "Thiếu mã hệ máy sys_id!"}, 400)
          return
        res = uninstall_emu(sys_id)
        if res.get("success"):
          self.send_json({"ok": True, "message": res.get("message"), "data": res})
        else:
          self.send_json({"ok": False, "error": res.get("error", "Gỡ bỏ thất bại")}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

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
          self.send_json({
              "ok": True,
              "message": "Đã tạo bản sao lưu thành công!",
              "backup": st,
          })
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
          self.send_json(
              {"ok": False, "error": "Không tìm thấy file sao lưu"}, 404
          )
          return
        ok, cnt, err = restore_save_backup(found)
        if ok:
          self.send_json(
              {"ok": True, "message": f"Khôi phục thành công {cnt} files save!"}
          )
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
      mode = "installed"
      if "mode" in query:
        mode = query.get("mode", ["installed"])[0]
      elif content_len > 0:
        try:
          payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
          mode = payload.get("mode", "installed")
        except Exception:
          pass
      if mode not in ("installed", "all"):
        mode = "installed"

      if cheat_runner.is_running():
        self.send_json({"ok": True, "message": "Đang xử lý tải kho Cheat..."})
      else:
        cheat_runner.start(mode=mode)
        if mode == "installed":
          msg = "Đã bắt đầu tải Cheat cho các game đang có trên thẻ nhớ!"
        else:
          msg = "Đã bắt đầu tải toàn bộ kho Cheat Libretro (~37MB)!"
        self.send_json({"ok": True, "message": msg})
      return

    if path == "/api/cheats/single":
      try:
        payload = {}
        if content_len > 0:
          try:
            payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
          except Exception:
            payload = {}
        system = payload.get("system") or query.get("system", [""])[0]
        filename = payload.get("filename") or query.get("filename", [""])[0]
        if not system or not filename:
          self.send_json(
              {"ok": False, "error": "Thiếu thông tin system hoặc filename"},
              400,
          )
          return
        res = check_or_download_single_cheat(system, filename)
        self.send_json({
            "ok": res.get("ok", False),
            "result": res,
            "message": res.get("message", ""),
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
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
        user_note = (
            payload.get("note", "").strip() or "Gửi từ RetroHub Web Manager"
        )
        ok, res = upload_log_to_telegram(note=user_note)
        if ok:
          self.send_json({
              "ok": True,
              "message": "Đã gửi nhật ký thành công vào Telegram của tác giả!",
          })
        else:
          self.send_json({"ok": False, "error": str(res)}, 500)
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/logs/toggle":
      state.enable_logging = not getattr(state, "enable_logging", False)
      state.save_settings()
      try:
        sync_retroarch_logging(state.enable_logging)
      except Exception:
        pass
      self.send_json({
          "ok": True,
          "enable_logging": state.enable_logging,
          "message": (
              "Đã BẬT ghi nhật ký"
              if state.enable_logging
              else "Đã TẮT ghi nhật ký"
          ),
      })
      return

    if path == "/api/logs/clear":
      clear_log()
      self.send_json({
          "ok": True,
          "log_size": get_log_size_str(),
          "message": "Đã làm sạch toàn bộ nhật ký!",
      })
      return

    if path == "/api/rename":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        sys_dir = payload.get("system", "").strip()
        old_f = payload.get("old_filename", "").strip()
        new_f = payload.get("new_filename", "").strip()

        if not sys_dir or not old_f or not new_f:
          self.send_json(
              {"ok": False, "error": "Thiếu thông tin tham số"}, 400
          )
          return

        old_rom_path = os.path.join(ROMS_DIR, sys_dir, old_f)
        new_rom_path = os.path.join(ROMS_DIR, sys_dir, new_f)

        if not os.path.isfile(old_rom_path):
          self.send_json(
              {"ok": False, "error": f"Không tìm thấy file {old_f}"}, 404
          )
          return
        if os.path.exists(new_rom_path) and old_rom_path != new_rom_path:
          self.send_json(
              {"ok": False, "error": f"Tên mới {new_f} đã tồn tại!"}, 400
          )
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
            "message": (
                f"Đã đổi tên thành công: {new_f}"
                + (" (kèm ảnh bìa)" if renamed_art else "")
            ),
            "renamed_art": renamed_art,
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
          self.send_json(
              {"ok": False, "error": "Thiếu thông tin hệ máy hoặc tệp"}, 400
          )
          return

        src_rom = os.path.join(ROMS_DIR, from_sys, fname)
        dst_dir = os.path.join(ROMS_DIR, to_sys)
        os.makedirs(dst_dir, exist_ok=True)
        dst_rom = os.path.join(dst_dir, fname)

        if not os.path.isfile(src_rom):
          self.send_json(
              {"ok": False, "error": f"Không tìm thấy file nguồn {fname}"}, 404
          )
          return
        if os.path.exists(dst_rom):
          self.send_json(
              {"ok": False, "error": f"File {fname} đã tồn tại ở hệ máy đích!"},
              400,
          )
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
            "message": (
                f"Đã chuyển {fname} sang {to_sys}"
                + (" (kèm ảnh bìa)" if moved_art else "")
            ),
            "moved_art": moved_art,
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

    if path == "/api/cleanup_rom_images":
      try:
        cleaned = cleanup_rom_directory_images()
        self.send_json({
            "ok": True,
            "cleaned_count": cleaned,
            "message": (
                f"Đã dọn dẹp {cleaned} tệp/thư mục ảnh trùng trong ROMs"
            ),
        })
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
          self.send_json(
              {
                  "ok": False,
                  "error": "Thiếu dữ liệu cào ảnh (system hoặc filename)",
              },
              400,
          )
          return

        if not query_str:
          query_str = clean_rom_title(fname)

        base_name = os.path.splitext(fname)[0]
        target_img_dir = os.path.join(IMGS_DIR, sys_dir)
        os.makedirs(target_img_dir, exist_ok=True)
        target_art = os.path.join(target_img_dir, base_name + ".png")

        # 1. Trích xuất icon gốc từ JAR nếu là game Java
        if fname.lower().endswith(".jar") or sys_dir.upper() == "JAVA":
          rom_path = os.path.join(ROMS_DIR, sys_dir, fname)
          if not os.path.isfile(rom_path):
            for res_dir in ("240320", "320240", "128128", "176208", "640360"):
              cand = os.path.join(ROMS_DIR, sys_dir, res_dir, fname)
              if os.path.isfile(cand):
                rom_path = cand
                break
          if extract_jar_icon(rom_path, target_art):
            now_ts = int(time.time())
            self.send_json({
                "ok": True,
                "source": "JAR Icon",
                "image_url": "",
                "art_url": (
                    f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?v={now_ts}"
                ),
            })
            return

        best_url, src_type = find_best_boxart(
            sys_dir, query_str, filename=fname, fast_only=fast_only
        )
        if not best_url:
          self.send_json(
              {
                  "ok": False,
                  "error": "Không tìm thấy ảnh bìa phù hợp",
                  "not_found": True,
              },
              404,
          )
          return

        for old_ext in (".jpg", ".jpeg", ".webp", ".bmp"):
          old_f = os.path.join(target_img_dir, base_name + old_ext)
          if os.path.isfile(old_f):
            try:
              os.remove(old_f)
            except Exception:
              pass

        success, err_msg = download_image_to_file(
            best_url, target_art, timeout=12
        )
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
              "art_url": (
                  f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?v={now_ts}"
              ),
          })
          return
        else:
          self.send_json(
              {"ok": False, "error": f"Lỗi tải ảnh: {err_msg}"}, 500
          )
          return
      except Exception as e:
        self.send_json({"ok": False, "error": f"Lỗi tải ảnh: {e}"}, 500)
      return

    if path == "/api/upload_art":
      sys_dir = query.get("system", [""])[0]
      fname = query.get("filename", [""])[0]
      if not sys_dir or not fname:
        self.send_json(
            {"ok": False, "error": "Missing system or filename"}, 400
        )
        return

      base_name = os.path.splitext(fname)[0]
      target_img_dir = os.path.join(IMGS_DIR, sys_dir)
      os.makedirs(target_img_dir, exist_ok=True)
      target_art = os.path.join(target_img_dir, base_name + ".png")

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
            "art_url": (
                f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?v={now_ts}"
            ),
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/upload_rom":
      sys_dir = query.get("system", [""])[0]
      fname = query.get("filename", [""])[0]
      if not sys_dir or not fname:
        self.send_json(
            {"ok": False, "error": "Missing system or filename"}, 400
        )
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
        self.send_json(
            {"ok": True, "message": f"Đã tải lên game {fname} thành công!"}
        )
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    # ==================== STORE POST API ====================
    if path == "/api/store/download":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        game_id = payload.get("game_id")
        sys_code = payload.get("sys_code", "").strip()
        rom_url = payload.get("rom_url", "").strip()
        filename = payload.get("filename", "").strip()
        img_url = payload.get("img_url", "").strip()
        title = payload.get("title", "").strip() or filename

        if not sys_code:
          self.send_json({"ok": False, "error": "Thiếu mã hệ máy"}, 400)
          return

        if not rom_url and game_id:
          mirrors = db.get_game_mirrors(game_id)
          if mirrors:
            rom_url = mirrors[0]["rom_url"]
            if not filename:
              filename = mirrors[0]["filename"]

        if not rom_url:
          self.send_json(
              {"ok": False, "error": "Không tìm thấy link tải ROM"}, 400
          )
          return

        if not filename:
          filename = (
              os.path.basename(urllib.parse.urlparse(rom_url).path)
              or f"{title}.zip"
          )

        dl_id = f"dl_{int(time.time() * 1000)}_{sys_code}"
        threading.Thread(
            target=background_download_store_game,
            args=(dl_id, sys_code, title, rom_url, filename, img_url),
            daemon=True,
        ).start()

        self.send_json({
            "ok": True,
            "download_id": dl_id,
            "message": f"Đang bắt đầu tải game {title} về máy...",
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    # ==================== YOUTUBE POST API ====================
    if path == "/api/youtube/playlists/save":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        playlists = payload.get("playlists", [])
        yt.save_search_history(playlists)
        self.send_json(
            {"ok": True, "message": "Đã lưu danh sách playlist YouTube!"}
        )
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/youtube/playlists/add":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        name = payload.get("name", "").strip()
        if not name:
          self.send_json({"ok": False, "error": "Tên playlist trống"}, 400)
          return
        cur_list = yt.load_search_history() or []
        if name in cur_list:
          cur_list.remove(name)
        cur_list.insert(0, name)
        yt.save_search_history(cur_list)
        self.send_json({
            "ok": True,
            "message": f"Đã thêm playlist: {name}",
            "playlists": cur_list,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/chat":
      try:
        post_data = self.rfile.read(content_len).decode("utf-8")
        # Use curl to bypass Python's missing SSL module on TrimUI
        cmd = [
            "curl", "-s", "-k", "-X", "POST",
            "https://ai.xuanhoa493.com/v1/chat/completions",
            "-H", "Content-Type: application/json",
            "-H", "Authorization: Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2",
            "-d", post_data
        ]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # If curl failed or returned empty stdout, return the stderr as a JSON error
        if not result.stdout.strip():
            err_msg = result.stderr if result.stderr else "Empty response from curl (Exit code: " + str(result.returncode) + ")"
            self.wfile.write(json.dumps({"error": "Curl Error: " + err_msg}).encode('utf-8'))
        else:
            self.wfile.write(result.stdout.encode('utf-8'))
      except Exception as e:
        self.send_json({"error": str(e)}, status=500)
      return

    if path == "/api/run_cmd":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        cmd_str = payload.get("cmd", "")
        import subprocess
        p = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        self.send_json({"output": out, "code": p.returncode, "cmd": cmd_str})
      except Exception as e:
        self.send_json({"error": str(e), "code": -1}, status=500)
      return

    if path == "/api/youtube/playlists/import":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        url_or_id = payload.get("url", "").strip()
        custom_title = payload.get("custom_title", "").strip()
        if not url_or_id:
          self.send_json(
              {"ok": False, "error": "Vui lòng nhập Link hoặc ID Playlist YouTube."},
              400,
          )
          return

        res = yt.fetch_playlist_info_and_videos(url_or_id, limit=200)
        if not res.get("ok"):
          self.send_json(
              {"ok": False, "error": res.get("error", "Không thể lấy video từ Playlist này.")},
              400,
          )
          return

        final_title = custom_title if custom_title else res.get("title", f"Playlist {res.get('pid')}")
        final_title = yt.clean_yt_text(final_title)
        videos = res.get("videos", [])

        # Save into search history (playlist list)
        cur_list = yt.load_search_history() or []
        if final_title in cur_list:
          cur_list.remove(final_title)
        cur_list.insert(0, final_title)
        yt.save_search_history(cur_list)

        # Cache all videos into feed cache under final_title
        yt.save_feed_cache(final_title, videos)

        self.send_json({
            "ok": True,
            "message": f"Đã nhập thành công Playlist '{final_title}' với {len(videos)} video!",
            "title": final_title,
            "count": len(videos),
            "videos": videos,
            "playlists": cur_list,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/youtube/playlists/delete":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        name = payload.get("name", "").strip()
        cur_list = yt.remove_search_history_item(name)
        self.send_json({
            "ok": True,
            "message": f"Đã xóa playlist: {name}",
            "playlists": cur_list,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/youtube/favorites/add":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        video = payload.get("video")
        if not video or not video.get("id"):
          self.send_json(
              {"ok": False, "error": "Thiếu dữ liệu video hợp lệ"}, 400
          )
          return
        favs = yt.load_favorites() or []
        favs = [v for v in favs if v.get("id") != video.get("id")]
        favs.insert(0, video)
        yt.save_favorites(favs)
        self.send_json({
            "ok": True,
            "message": "Đã thêm video vào Yêu thích!",
            "favorites": favs,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/youtube/favorites/remove":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        v_id = payload.get("id", "").strip()
        favs = yt.load_favorites() or []
        favs = [v for v in favs if v.get("id") != v_id]
        yt.save_favorites(favs)
        self.send_json({
            "ok": True,
            "message": "Đã xóa video khỏi Yêu thích!",
            "favorites": favs,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    if path == "/api/youtube/cache/clear":
      try:
        cache_dir = get_yt_cache_dir()
        c = 0
        freed = 0
        if os.path.isdir(cache_dir):
          for f in os.listdir(cache_dir):
            p = os.path.join(cache_dir, f)
            if os.path.isfile(p):
              try:
                sz = os.path.getsize(p)
                os.remove(p)
                c += 1
                freed += sz
              except Exception:
                pass
        freed_mb = f"{freed / (1024*1024):.1f} MB"
        self.send_json({
            "ok": True,
            "message": (
                f"Đã xóa sạch {c} ảnh thumbnail YouTube, giải phóng"
                f" {freed_mb}!"
            ),
            "cleared_count": c,
            "freed_bytes": freed,
        })
      except Exception as e:
        self.send_json({"ok": False, "error": str(e)}, 500)
      return

    self.send_response(404)
    self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  daemon_threads = True
  allow_reuse_address = True


# ==================== TRIMUI SMART PRO WAKELOCK ====================
ORIG_DIMTIME = None

def get_current_dimtime():
    try:
        res = subprocess.run(["/usr/trimui/bin/systemval", "dimtime"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            val = res.stdout.strip()
            if val.isdigit() and int(val) > 0:
                return int(val)
    except Exception:
        pass
    return 300

def set_dimtime(val):
    try:
        subprocess.run(["/usr/trimui/bin/systemval", "dimtime", str(val)], timeout=2)
    except Exception:
        pass

def enable_wakelock():
    global ORIG_DIMTIME
    ORIG_DIMTIME = get_current_dimtime()
    set_dimtime(0)
    print(f"[*] [Wakelock] Disabled auto-sleep (saved original dimtime: {ORIG_DIMTIME}s)")

def disable_wakelock():
    global ORIG_DIMTIME
    val = ORIG_DIMTIME if (ORIG_DIMTIME and ORIG_DIMTIME > 0) else 300
    set_dimtime(val)
    print(f"[*] [Wakelock] Restored original dimtime: {val}s")

atexit.register(disable_wakelock)

def _sig_handler(sig, frame):
    disable_wakelock()
    sys.exit(0)

signal.signal(signal.SIGTERM, _sig_handler)
signal.signal(signal.SIGINT, _sig_handler)

def _keepalive_daemon():
    while True:
        try:
            set_dimtime(0)
            time.sleep(60)
        except Exception:
            time.sleep(60)

_keepalive_thread = threading.Thread(target=_keepalive_daemon, daemon=True)
_keepalive_thread.start()


def run_server():
  enable_wakelock()
  server_address = ("0.0.0.0", PORT)
  httpd = ThreadedHTTPServer(server_address, GameWebHandler)
  print(f"[*] RetroHub Web Game Manager running at http://0.0.0.0:{PORT}")
  try:
    httpd.serve_forever()
  except (KeyboardInterrupt, SystemExit):
    pass
  finally:
    disable_wakelock()
    httpd.server_close()


if __name__ == "__main__":
  run_server()
