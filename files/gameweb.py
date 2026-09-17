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
    import db
except ImportError:
    # Standalone mock fallbacks
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
          games = db.search_games_fts(
              query_str,
              sys_code=sys_code,
              limit=limit,
              source_type=source_type,
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


# ==============================================================================
# EMBEDDED FRONTEND HTML / CSS / JS
# ==============================================================================
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RetroHub - Web Manager</title>
    <style>
        :root {
            --bg-main: #0b0f19;
            --bg-card: #151d2f;
            --bg-card-hover: #1e293b;
            --bg-sidebar: #0f172a;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --accent: #00f6f6;
            --accent-green: #10b981;
            --accent-gold: #ffcf3c;
            --danger: #ef4444;
            --danger-hover: #dc2626;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --border: #334155;
            --radius: 10px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        /* Header & Navigation */
        header {
            background: rgba(15, 23, 42, 0.96);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            padding: 8px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            gap: 16px;
        }
        .header-left { display: flex; align-items: center; gap: 20px; }
        .logo-box { display: flex; align-items: center; gap: 10px; cursor: pointer; }
        .logo-box h1 { font-size: 20px; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .badge-device { background: #1e293b; color: #38bdf8; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid #0284c7; }

        .main-nav { display: flex; gap: 6px; align-items: center; background: #070a12; padding: 4px; border-radius: 10px; border: 1px solid var(--border); }
        .nav-tab {
            background: transparent;
            color: var(--text-sub);
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        .nav-tab:hover { color: #fff; background: rgba(255, 255, 255, 0.05); }
        .nav-tab.active { background: #1e293b; color: var(--primary); border: 1px solid #0284c7; box-shadow: 0 2px 8px rgba(0,0,0,0.4); }

        .header-stats { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--text-sub); }
        .stat-badge { background: #1e293b; padding: 5px 12px; border-radius: 8px; border: 1px solid var(--border); font-size: 12px; }
        .stat-badge strong { color: #38bdf8; }

        /* Views Container */
        .tab-view { display: none; flex: 1; min-height: 0; }
        .tab-view.active { display: flex; }

        .app-container { display: flex; flex: 1; overflow: hidden; width: 100%; }
        
        /* Sidebar */
        aside {
            width: 280px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            flex-shrink: 0;
        }
        .sidebar-header { padding: 14px 16px; font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-sub); letter-spacing: 0.5px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
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
        .sys-item.active .count { background: #0284c7; color: #fff; }

        /* Main Content */
        main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 18px 24px; background: var(--bg-main); }
        .toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
        .search-box { flex: 1; min-width: 220px; position: relative; }
        .search-box input {
            width: 100%;
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 9px 12px 9px 36px;
            color: #fff;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }
        .search-box input:focus { border-color: var(--primary); }
        .search-icon { position: absolute; left: 12px; top: 11px; width: 14px; height: 14px; opacity: 0.5; }
        .search-icon::before { content: "🔍"; font-size: 13px; }

        /* Buttons */
        .btn {
            background: #0284c7;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
        }
        .btn:hover { background: #0369a1; filter: brightness(1.1); transform: translateY(-1px); }
        .btn-sm { padding: 5px 10px; font-size: 11px; border-radius: 6px; }
        .btn-secondary { background: #1e293b; color: #cbd5e1; border: 1px solid var(--border); }
        .btn-secondary:hover { background: #334155; color: #fff; }
        .btn-green { background: #059669; }
        .btn-green:hover { background: #047857; }
        .btn-danger { background: #dc2626; }
        .btn-danger:hover { background: #b91c1c; }
        .btn-gold { background: #d97706; }
        .btn-gold:hover { background: #b45309; }
        .btn-batch { background: linear-gradient(135deg, #0284c7, #6366f1); border: none; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }

        /* Grids */
        .games-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 16px; }
        .game-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
        }
        .game-card:hover { transform: translateY(-3px); border-color: #0284c7; box-shadow: 0 8px 20px rgba(0,0,0,0.4); }
        .art-box {
            position: relative;
            width: 100%;
            aspect-ratio: 4/3;
            background: #070a12;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-bottom: 1px solid var(--border);
        }
        .art-box img { width: 100%; height: 100%; object-fit: contain; }
        
        .game-info { padding: 12px; flex: 1; display: flex; flex-direction: column; }
        .game-title { font-size: 13px; font-weight: 700; color: #f1f5f9; line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .game-meta { font-size: 11px; color: var(--text-sub); display: flex; justify-content: space-between; align-items: center; margin-top: auto; }
        .badge-tag { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
        .badge-viet { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-hack { background: rgba(234, 179, 8, 0.2); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.4); }
        .badge-top { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
        .badge-installed { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); font-size: 11px; font-weight: 700; }

        .game-actions { display: flex; gap: 4px; margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; }
        .game-actions .btn { flex: 1; justify-content: center; }

        /* Modals */
        .modal-backdrop {
            position: fixed; inset: 0; background: rgba(0,0,0,0.8);
            backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 200;
        }
        .modal-backdrop.show { display: flex; }
        .modal-box {
            background: #0f172a; border: 1px solid var(--border); border-radius: 12px;
            padding: 20px; width: 92vw; max-width: 520px; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .modal-header h3 { font-size: 16px; color: #fff; }
        .modal-close { background: none; border: none; font-size: 20px; color: var(--text-sub); cursor: pointer; }
        .modal-close:hover { color: #fff; }
        .form-group { margin-bottom: 14px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-sub); margin-bottom: 6px; }
        .form-group input, .form-group select {
            width: 100%; background: #0b0f19; border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; color: #fff; font-size: 13px; outline: none;
        }
        .form-group input:focus, .form-group select:focus { border-color: var(--primary); }

        /* Progress Bar */
        .progress-bar-bg { background: #1e293b; border-radius: 999px; overflow: hidden; }
        .progress-bar-fill { background: #0284c7; height: 100%; transition: width 0.2s ease; }

        /* Toast */
        #toast {
            position: fixed; bottom: 24px; right: 24px; background: #1e293b; color: #fff;
            border: 1px solid var(--primary); padding: 12px 20px; border-radius: 8px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.5); font-size: 13px; font-weight: 600;
            display: none; z-index: 300; animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

        /* YouTube Specific */
        .yt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
        .yt-card {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
            overflow: hidden; display: flex; flex-direction: column; transition: transform 0.15s, border-color 0.15s;
        }
        .yt-card:hover { transform: translateY(-3px); border-color: #ef4444; }
        .yt-thumb-box { position: relative; width: 100%; aspect-ratio: 16/9; background: #000; overflow: hidden; }
        .yt-thumb-box img { width: 100%; height: 100%; object-fit: cover; }
        .yt-dur-badge { position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
        
        .yt-playlist-item {
            padding: 10px 14px; display: flex; align-items: center; justify-content: space-between;
            border-radius: 8px; cursor: pointer; margin-bottom: 4px; transition: all 0.15s;
            border: 1px solid transparent;
        }
        .yt-playlist-item:hover { background: #1e293b; }
        .yt-playlist-item.active { background: #1e293b; border-color: #ef4444; color: #f87171; font-weight: 700; }

        @media (max-width: 860px) {
            header { flex-direction: column; align-items: stretch; gap: 10px; }
            .header-left { flex-direction: column; align-items: flex-start; gap: 10px; }
            .main-nav { width: 100%; justify-content: space-around; overflow-x: auto; }
            .app-container { flex-direction: column; }
            aside { width: 100%; height: 60px; flex-direction: row; border-right: none; border-bottom: 1px solid var(--border); }
            .sys-item { border-left: none; border-bottom: 3px solid transparent; white-space: nowrap; }
            .sys-item.active { border-bottom-color: var(--primary); border-left-color: transparent; }
            .sidebar-header { display: none; }
        }
    </style>
</head>
<body>

    <header>
        <div class="header-left">
            <div class="logo-box" onclick="switchMainTab('games')">
                <h1>RetroHub</h1>
                <span class="badge-device">Web Manager</span>
            </div>
            <nav class="main-nav">
                <button id="nav-btn-games" class="nav-tab active" onclick="switchMainTab('games')">
                    <span>🎮</span> Quản lý game
                </button>
                <button id="nav-btn-store" class="nav-tab" onclick="switchMainTab('store')">
                    <span>⚡</span> Tải game online
                </button>
                <button id="nav-btn-youtube" class="nav-tab" onclick="switchMainTab('youtube')">
                    <span>📺</span> Quản lý playlist YouTube
                </button>
                <button id="nav-btn-files" class="nav-tab" onclick="switchMainTab('files')">
                    <span>📁</span> Quản lý file
                </button>
                <button id="nav-btn-stream" class="nav-tab" onclick="switchMainTab('stream')">
                    <span>🖥️</span> Truyền màn hình
                </button>
                <button id="nav-btn-chat" class="nav-tab" onclick="switchMainTab('chat')">
                    <span>🤖</span> AI Chatbot
                </button>
            </nav>
        </div>
        <div class="header-stats">
            <div class="stat-badge" id="storage-stat">Bộ nhớ: <strong>Đang đọc...</strong></div>
            <button class="btn btn-sm btn-secondary" onclick="openSavesCheatsModal('saves')">Save & Cheats</button>
            <button class="btn btn-sm btn-secondary" onclick="reloadCurrentView()">Nạp lại</button>
        </div>
    </header>

    <!-- ================================================================= -->
    <!-- TAB 1: QUẢN LÝ GAME TRÊN THẺ NHỚ -->
    <!-- ================================================================= -->
    <div id="tab-view-games" class="tab-view active">
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
    </div>

    <!-- ================================================================= -->
    <!-- TAB 2: TẢI GAME ONLINE (ROMS STORE) -->
    <!-- ================================================================= -->
    <div id="tab-view-store" class="tab-view">
        <div class="app-container">
            <aside id="store-sidebar">
                <div class="sidebar-header">Danh mục tuyển chọn</div>
                <div id="store-categories-list"></div>
                <div class="sidebar-header" style="margin-top:10px;">Kho hệ máy (40,000+ Game)</div>
                <div id="store-systems-list"></div>
            </aside>

            <main id="store-main-scroll" onscroll="handleStoreScroll(event)">
                <div class="toolbar">
                    <div class="search-box">
                        <span class="search-icon"></span>
                        <input type="text" id="store-search-input" placeholder="Tìm kiếm trong 40,000+ game..." onkeydown="if(event.key==='Enter') executeStoreSearch()">
                    </div>
                    <select id="store-sort-select" onchange="executeStoreSearch()" style="background:#0f172a; border:1px solid var(--border); color:#fff; border-radius:8px; padding:8px 12px; font-size:12px; outline:none;">
                        <option value="downloads">Lượt tải nhiều nhất</option>
                        <option value="rating">Đánh giá cao nhất</option>
                        <option value="title">Tên A-Z</option>
                    </select>
                    <button class="btn btn-green" onclick="executeStoreSearch()">Tìm kiếm</button>
                </div>

                <!-- Floating Pinned Download Progress Bar -->
                <div id="store-download-banner" style="display:none; position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 580px; background: rgba(11, 19, 41, 0.95); border: 1px solid #0284c7; border-radius: 12px; padding: 14px 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(2,132,199,0.3); z-index: 1000; backdrop-filter: blur(10px);">
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; font-weight:700; margin-bottom:8px;">
                        <span id="store-dl-title" style="color:#38bdf8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;">Đang tải game về máy...</span>
                        <span id="store-dl-pct" style="color:#10b981; font-weight:800; font-size:14px;">0%</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 8px; margin-bottom:8px; background:#1e293b; border-radius:4px; overflow:hidden;">
                        <div id="store-dl-bar" class="progress-bar-fill" style="width:0%; background:linear-gradient(90deg, #0284c7, #10b981); height:100%; transition:width 0.25s ease;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11.5px; color:#94a3b8;">
                        <span id="store-dl-speed">Tốc độ: 0 KB/s</span>
                        <span id="store-dl-status">Đang kết nối server...</span>
                    </div>
                </div>

                <div id="store-games-container" class="games-grid"></div>
                <div id="store-loading" style="display:none; text-align:center; padding: 40px; color: var(--primary);">
                    <div style="font-size: 14px; font-weight: 700;">Đang nạp kho game trực tuyến...</div>
                </div>
                <div id="store-loading-more" style="display:none; text-align:center; padding: 24px; color: #38bdf8; font-weight: 600; font-size: 13px;">
                    Đang tải thêm game... ⏳
                </div>
                <div id="store-load-more-btn-container" style="display:none; text-align:center; padding: 24px 0;">
                    <button class="btn btn-secondary" onclick="loadMoreStoreGames()" style="padding: 10px 28px; font-size: 13px; font-weight: 600; border-radius: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">⬇️ Tải thêm game tiếp theo...</button>
                </div>
                <div id="store-empty-state" style="display:none; text-align:center; padding: 60px 20px; color: var(--text-sub);">
                    <div style="font-size: 16px; margin-bottom: 12px; font-weight: 600;">Không tìm thấy game</div>
                    <p>Hãy thử từ khóa khác hoặc chuyển sang hệ máy khác trong danh sách.</p>
                </div>
            </main>
        </div>
    </div>

    <!-- ================================================================= -->
    <!-- TAB 3: QUẢN LÝ PLAYLIST YOUTUBE -->
    <!-- ================================================================= -->
    <div id="tab-view-youtube" class="tab-view">
        <div class="app-container">
            <aside id="yt-sidebar" style="width: 320px;">
                <div class="sidebar-header" style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
                    <span style="font-weight:700;">Playlist & Chủ đề</span>
                    <div style="display:flex; gap:4px;">
                        <button class="btn btn-sm btn-danger" onclick="openImportPlaylistModal()" title="Dán link Playlist YouTube để nhập toàn bộ video" style="padding:4px 8px; font-size:11px;">📥 Dán link</button>
                        <button class="btn btn-sm btn-green" onclick="openAddPlaylistModal()" title="Thêm chủ đề / từ khóa tìm kiếm" style="padding:4px 8px; font-size:11px;">+ Thêm</button>
                    </div>
                </div>
                <div id="yt-playlists-list" style="padding: 10px;"></div>
                
                <div style="margin-top: auto; padding: 14px; border-top: 1px solid var(--border);">
                    <button class="btn btn-sm btn-secondary" style="width: 100%; justify-content: center;" onclick="clearYouTubeCache()">
                        🗑️ Dọn cache ảnh YouTube
                    </button>
                </div>
            </aside>

            <main>
                <div class="toolbar">
                    <div class="search-box">
                        <span class="search-icon"></span>
                        <input type="text" id="yt-search-input" placeholder="Tìm kiếm video trên YouTube..." onkeydown="if(event.key==='Enter') executeYouTubeSearch()">
                    </div>
                    <button class="btn btn-danger" onclick="executeYouTubeSearch()">Tìm video</button>
                    <button class="btn btn-secondary" onclick="addCurrentSearchAsPlaylist()">+ Lưu từ khóa làm Playlist</button>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <h3 id="yt-current-title" style="font-size:15px; color:#fff;">Trending YouTube</h3>
                    <span id="yt-video-count" style="font-size:12px; color:var(--text-sub);">0 video</span>
                </div>

                <div id="yt-videos-container" class="yt-grid"></div>
                <div id="yt-loading" style="display:none; text-align:center; padding: 40px; color: #ef4444;">
                    <div style="font-size: 14px; font-weight: 700;">Đang kết nối YouTube InnerTube...</div>
                </div>
            </main>
        </div>
    </div>

        <!-- ================================================================= -->
    <!-- TAB 6: AI CHATBOT -->
    <!-- ================================================================= -->
    <div id="tab-view-chat" class="tab-view">
        <div style="flex:1; display:flex; flex-direction:column; background:#070a13; height:100%; max-width: 900px; margin: 0 auto; width: 100%; border-left: 1px solid var(--border); border-right: 1px solid var(--border); box-shadow: 0 0 30px rgba(0,0,0,0.5);">
            <div style="padding:20px; border-bottom:1px solid var(--border); background:#0f172a; display:flex; align-items:center; gap:16px;">
                <div style="font-size:32px;">🤖</div>
                <div>
                    <h2 style="font-size:18px; font-weight:800; color:#fff; margin:0 0 4px 0;">Trợ lý ảo AI Chatbot</h2>
                    <div style="font-size:13px; color:#10b981; font-weight:600;">● Đang trực tuyến</div>
                </div>
                <button id="btn-send-info" class="btn btn-sm btn-green" style="margin-left:auto; font-size:13px; padding:8px 12px;" onclick="sendDeviceInfoToAI()" title="Gửi cấu trúc máy cho AI">📡 Gửi thông tin máy</button>
                <button class="btn btn-sm btn-secondary" style="margin-left:8px; font-size:13px; padding:8px 12px;" onclick="showSystemPrompt()" title="Xem khung nền kiến thức của AI">ℹ️ Xem Prompt</button>
                <button class="btn btn-sm btn-danger" style="margin-left:8px; font-size:13px; padding:8px 12px;" onclick="clearAIChat()">🗑️ Xóa log</button>
            </div>
            
            <div id="chat-messages" style="flex:1; overflow-y:auto; padding:16px 20px; display:flex; flex-direction:column; gap:12px; scroll-behavior: smooth;">
                <div style="display:flex; justify-content:flex-start;">
                    <div style="background:#1e293b; color:#f8fafc; padding:10px 14px; border-radius:12px; border-bottom-left-radius:4px; max-width:85%; font-size:14.5px; line-height:1.45; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                        Xin chào! Tôi là trợ lý ảo AI được tích hợp trực tiếp vào RetroHub. Tôi có thể giúp gì cho bạn?
                    </div>
                </div>
            </div>
            
            <div style="padding:16px 20px; border-top:1px solid var(--border); background:#0f172a;">
                <form id="chat-form" onsubmit="sendChatMessage(event)" style="display:flex; gap:12px;">
                    <input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:12px 20px; color:#fff; font-size:14.5px; outline:none; transition:border 0.2s;" onfocus="this.style.borderColor='#0284c7'" onblur="this.style.borderColor='#334155'" required>
                    <button type="submit" id="chat-submit-btn" class="btn btn-primary" style="border-radius:30px; padding:0 32px; font-size:15px; font-weight:700;">Gửi ✈️</button>
                </form>
            </div>
        </div>
    </div>

    <!-- TAB FILES -->
    <div id="tab-view-files" class="tab-view" style="flex-direction: column; width: 100%;">
        <div style="display:flex; justify-content:center; align-items:center; height:100%; padding:20px;">
            <div style="background:#0f172a; border:1px solid var(--border); border-radius:16px; padding:40px; text-align:center; max-width:550px; width:100%; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                <div style="font-size:48px; margin-bottom:20px;">📁</div>
                <h2 style="margin:0 0 10px 0; color:#38bdf8;">Web Quản Lý File (SFTPGo)</h2>
                <p style="color:var(--text-sub); font-size:14px; margin-bottom:30px; line-height:1.5;">
                    Truy cập, quản lý toàn bộ tệp tin trên thẻ nhớ qua giao diện Web chuyên nghiệp.
                </p>
                <div style="background:#0a0e1a; border:1px solid var(--border); border-radius:10px; padding:20px; margin-bottom:30px; text-align:left;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px;">
                        <span style="color:#94a3b8;">Địa chỉ Web (Trình duyệt):</span>
                        <strong style="color:#10b981;" id="files-sftp-url-disp">Đang tải...</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px;">
                        <span style="color:#94a3b8;">Tài khoản (Web):</span>
                        <strong style="color:#fff;">root</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px;">
                        <span style="color:#94a3b8;">Mật khẩu (Web):</span>
                        <strong style="color:#fff;">root</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:14px; border-top:1px dashed var(--border); padding-top:12px; margin-top:12px;">
                        <span style="color:#94a3b8;">Kết nối qua SFTP (WinSCP):</span>
                        <span style="color:#e2e8f0; font-size:13px;">Cổng: <strong style="color:#f59e0b;">2022</strong> (user/pass: <strong>trimui</strong>)</span>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="window.open('http://' + window.location.hostname + ':8080', '_blank')" style="font-size:16px; padding:12px 30px; border-radius:12px; width:100%; justify-content:center;">
                    Mở Web Quản Lý File (Sang Tab mới)
                </button>
                <script>
                    document.addEventListener("DOMContentLoaded", () => {
                        setTimeout(() => {
                            document.getElementById("files-sftp-url-disp").textContent = "http://" + window.location.hostname + ":8080";
                        }, 500);
                    });
                </script>
            </div>
        </div>
    </div>

    <!-- TAB STREAM -->
    <div id="tab-view-stream" class="tab-view" style="flex-direction: column; width: 100%;">
        <div style="display:flex; justify-content:center; align-items:center; height:100%; width:100%; padding:20px; flex:1;">
            <div style="background:#0f172a; border:1px solid var(--border); border-radius:16px; padding:40px; text-align:center; max-width:550px; width:100%; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                <div style="font-size:48px; margin-bottom:20px;">🖥️</div>
                <h2 style="margin:0 0 10px 0; color:#38bdf8;">Stream Màn Hình TrimUI</h2>
                <p style="color:var(--text-sub); font-size:14px; margin-bottom:30px; line-height:1.5;">
                    Phát trực tiếp màn hình máy chơi game lên trình duyệt với độ trễ siêu thấp (&lt; 30ms).
                </p>
                <div style="background:#0a0e1a; border:1px solid var(--border); border-radius:10px; padding:20px; margin-bottom:30px; text-align:left;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px; align-items:center;">
                        <span style="color:#94a3b8;">Trạng thái dịch vụ:</span>
                        <strong id="stream-status-badge" style="color:#94a3b8;">Đang tải...</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px; align-items:center;">
                        <span style="color:#94a3b8;">Địa chỉ Web Stream:</span>
                        <strong style="color:#10b981;" id="stream-url-disp">http://---:8088</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:14px; border-top:1px dashed var(--border); padding-top:12px; margin-top:12px; align-items:center;">
                        <span style="color:#94a3b8;">Nguồn phát OBS (MJPEG):</span>
                        <span style="color:#f59e0b; font-size:13px; font-family:monospace;" id="stream-obs-link">http://---:8088/stream.mjpg</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px;">
                    <button id="btn-stream-toggle" class="btn btn-secondary" onclick="toggleScreenStream()" style="font-size:15px; padding:12px 20px; border-radius:12px; flex:1;">
                        Đang kiểm tra...
                    </button>
                    <button id="btn-stream-newtab" class="btn btn-primary" onclick="openStreamNewTab()" style="font-size:15px; padding:12px 20px; border-radius:12px; flex:1; display:none;">
                        Mở Web Stream
                    </button>
                </div>
                <script>
                    document.addEventListener("DOMContentLoaded", () => {
                        setTimeout(() => {
                            const host = window.location.hostname || '127.0.0.1';
                            const el = document.getElementById("stream-url-disp");
                            if(el) el.textContent = "http://" + host + ":8088";
                            const obs = document.getElementById("stream-obs-link");
                            if(obs) obs.textContent = "http://" + host + ":8088/stream.mjpg";
                        }, 500);
                    });
                </script>
            </div>
        </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODALS -->
    <!-- ================================================================= -->
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
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-sub); margin-top: 4px;">
                <span>Nguồn: RetroHub Catalog DB & Libretro Thumbnails CDN</span>
                <button type="button" class="btn btn-secondary btn-sm" onclick="openGoogleImageSearch()">Google Images ↗</button>
            </div>
            <div id="scrape-results" class="games-grid" style="grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); margin: 12px 0; max-height: 280px; overflow-y: auto;"></div>

            <div style="background: rgba(15, 23, 42, 0.6); border: 1px dashed var(--border); border-radius: 6px; padding: 10px; margin-top: 6px;">
                <div style="font-size: 11px; color: var(--text-sub); margin-bottom: 6px; font-weight: 600;">Dán ảnh từ Clipboard (Ctrl+V) hoặc dán link:</div>
                <div style="display: flex; gap: 8px;">
                    <input type="text" id="scrape-direct-url" style="flex:1; background:#0b0f19; border:1px solid var(--border); color:#fff; padding:6px 10px; border-radius:6px; font-size:12px;" placeholder="Dán link https://... hoặc bấm Ctrl+V" onkeydown="if(event.key==='Enter') submitDirectArtUrl()">
                    <button class="btn btn-sm btn-green" onclick="submitDirectArtUrl()">Gán link</button>
                </div>
            </div>

            <div style="border-top:1px solid var(--border); padding-top:12px; display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <label class="btn btn-sm btn-secondary" style="margin:0; cursor:pointer;">
                    Tải ảnh từ máy
                    <input type="file" id="art-file-input" accept="image/*" style="display:none" onchange="uploadCustomArt(event)">
                </label>
                <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-scrape')">Đóng</button>
            </div>
        </div>
    </div>

    <!-- Modal Nhập Playlist YouTube từ Link -->
    <div class="modal-backdrop" id="modal-import-playlist">
        <div class="modal-box" style="max-width: 560px;">
            <div class="modal-header">
                <h3>📥 Nhập Playlist YouTube từ Link</h3>
                <button class="modal-close" onclick="closeModal('modal-import-playlist')">&times;</button>
            </div>
            <div class="form-group">
                <label>Link Playlist hoặc Link Video có list=</label>
                <input type="text" id="import-playlist-url" placeholder="https://www.youtube.com/playlist?list=PL... hoặc ID Playlist">
                <small style="color: var(--text-sub); display:block; margin-top:5px; font-size:11px;">
                    💡 Hỗ trợ mọi link: <code>youtube.com/playlist?list=...</code>, <code>youtu.be/...&list=...</code> hoặc mã ID Playlist (PL..., RD..., OLAK...).
                </small>
            </div>
            <div class="form-group" style="margin-top:12px;">
                <label>Tên Playlist hiển thị (tùy chọn)</label>
                <input type="text" id="import-playlist-title" placeholder="Để trống nếu muốn tự lấy tên gốc trên YouTube">
            </div>
            <div id="import-playlist-status" style="display:none; margin-top:14px; padding:12px; border-radius:8px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); color:#fca5a5; font-size:12px; text-align:center;">
                <span id="import-playlist-status-text">Đang trích xuất toàn bộ video từ YouTube InnerTube...</span>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-import-playlist')">Hủy</button>
                <button class="btn btn-danger" id="btn-submit-import-pl" onclick="submitImportPlaylist()">🚀 Nhập toàn bộ Playlist</button>
            </div>
        </div>
    </div>

    <!-- Modal Thêm Playlist YouTube -->
    <div class="modal-backdrop" id="modal-add-playlist">
        <div class="modal-box">
            <div class="modal-header">
                <h3>Thêm Playlist / Chủ đề YouTube</h3>
                <button class="modal-close" onclick="closeModal('modal-add-playlist')">&times;</button>
            </div>
            <div class="form-group">
                <label>Tên Playlist hoặc Từ khóa / Tên Kênh</label>
                <input type="text" id="new-playlist-name" placeholder="Ví dụ: Nhạc Trẻ Remix 2026, Phim Hoạt Hình, MixiGaming...">
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-add-playlist')">Hủy</button>
                <button class="btn btn-green" onclick="submitAddPlaylist()">Thêm vào danh sách</button>
            </div>
        </div>
    </div>

    <!-- Modal Save & Cheats -->
    <div class="modal-backdrop" id="modal-saves-cheats">
        <div class="modal-box" style="max-width: 780px; width: 92vw;">
            <div class="modal-header">
                <h3>Quản lý Save Game, Cheat Code & Logs</h3>
                <button class="modal-close" onclick="closeModal('modal-saves-cheats')">&times;</button>
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 14px;">
                <button id="tab-btn-saves" class="btn btn-sm" onclick="switchSavesCheatsTab('saves')">Sao lưu Save</button>
                <button id="tab-btn-cheats" class="btn btn-sm btn-secondary" onclick="switchSavesCheatsTab('cheats')">Kho Cheat Code</button>
                <button id="tab-btn-logs" class="btn btn-sm btn-secondary" onclick="switchSavesCheatsTab('logs')">Gửi Log & Chẩn đoán</button>
            </div>
            <div id="tab-content-saves">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span id="saves-stats-text" style="font-size: 12px; color: var(--text-sub);">Đang tải thống kê...</span>
                    <button class="btn btn-sm btn-green" onclick="createSaveBackupWeb()">+ Tạo bản sao lưu mới</button>
                </div>
                <div id="backups-list-table" style="max-height: 280px; overflow-y: auto; background: #0b0f19; border: 1px solid var(--border); border-radius: 8px; padding: 6px;"></div>
            </div>
            <div id="tab-content-cheats" style="display:none;">
                <div id="cheats-status-box" style="padding: 12px; background: #0b0f19; border: 1px solid var(--border); border-radius: 8px; font-size: 12px; margin-bottom: 12px;">Đang đọc kho cheat...</div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-sm btn-green" onclick="downloadCheatsWeb('installed')">Tải Cheat cho game hiện có</button>
                    <button class="btn btn-sm btn-secondary" onclick="downloadCheatsWeb('all')">Tải toàn bộ kho Cheat (~37MB)</button>
                </div>
            </div>
            <div id="tab-content-logs" style="display:none;">
                <div style="padding: 12px; background: #0b0f19; border: 1px solid var(--border); border-radius: 8px; font-size: 12px; margin-bottom: 12px;">
                    <div>Thiết bị: <strong id="web-log-device-id" style="color:#38bdf8;">...</strong> | Kích thước: <strong id="web-log-size">...</strong></div>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="btn btn-sm btn-batch" onclick="sendLogTelegramWeb()">Gửi Log lên Telegram tác giả</button>
                    <a href="/api/logs/download" class="btn btn-sm btn-secondary" download>Tải file báo cáo (.txt)</a>
                </div>
            </div>
            <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
                <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-saves-cheats')">Đóng</button>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <!-- ================================================================= -->
    <!-- JAVASCRIPT APP LOGIC -->
    <!-- ================================================================= -->
    <script>
        let currentTab = 'games';
        let allSystems = [];
        let currentSystem = null;
        let currentGames = [];
        let selectedGame = null;

        let storeCategories = [];
        let storeSystems = [];
        let currentStoreCategory = 'HITS';
        let currentStoreSystem = 'ALL';
        let storeGames = [];
        let storeDlInterval = null;

        let ytPlaylists = [];
        let currentYtTab = 'trending';
        let ytVideos = [];

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3000);
        }

        function closeModal(id) {
            const el = document.getElementById(id);
            if (el) el.classList.remove('show');
        }
        function openModal(id) {
            const el = document.getElementById(id);
            if (el) el.classList.add('show');
        }

        function switchMainTab(tab) {
            currentTab = tab;
            // Cập nhật URL hash
            history.replaceState(null, null, '#' + tab);
            document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));

            const btn = document.getElementById(`nav-btn-${tab}`);
            const view = document.getElementById(`tab-view-${tab}`);
            if (btn) btn.classList.add('active');
            if (view) view.classList.add('active');

            if (tab === 'games') {
                if (!allSystems.length) loadSystems();
            } else if (tab === 'store') {
                if (!storeCategories.length) loadStoreInit();
            } else if (tab === 'youtube') {
                if (!ytPlaylists.length) loadYouTubeInit();
            } else if (tab === 'stream') {
                checkStreamStatus();
            }
        }

        function reloadCurrentView() {
            loadStorageStatus();
            if (currentTab === 'games') loadSystems(true);
            else if (currentTab === 'store') loadStoreGames();
            else if (currentTab === 'youtube') loadYouTubeVideos(currentYtTab);
        }

        async function loadStorageStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.ok && data.storage) {
                    document.getElementById('storage-stat').innerHTML = `Bộ nhớ: <strong>Trống ${data.storage.free_gb}</strong> / ${data.storage.total_gb}`;
                }
            } catch (e) {}
        }

        // ==================== QUẢN LÝ GAME (GAMES MANAGER) ====================
        async function loadSystems(forceSelectFirst = false) {
            try {
                const res = await fetch('/api/systems');
                const data = await res.json();
                if (data.ok) {
                    allSystems = data.systems || [];
                    renderSystemsList(data.no_art_count || 0);
                    if (allSystems.length > 0 && (!currentSystem || forceSelectFirst)) {
                        selectSystem(allSystems[0].dir);
                    }
                }
            } catch (e) {
                console.error('Error loading systems:', e);
            }
        }

        function renderSystemsList(noArtCount) {
            const listEl = document.getElementById('systems-list');
            let html = '';
            if (noArtCount > 0) {
                html += `<div class="sys-item ${currentSystem === '__no_art__' ? 'active' : ''}" onclick="selectSystem('__no_art__')">
                    <span style="color:#f59e0b;">⚠️ Thiếu ảnh bìa</span>
                    <span class="count" style="background:#b45309; color:#fff;">${noArtCount}</span>
                </div>`;
            }
            allSystems.forEach(s => {
                const activeCls = (currentSystem === s.dir) ? 'active' : '';
                html += `<div class="sys-item ${activeCls}" onclick="selectSystem('${s.dir}')">
                    <span>${s.name}</span>
                    <span class="count">${s.count}</span>
                </div>`;
            });
            listEl.innerHTML = html;
        }

        async function selectSystem(sysDir) {
            currentSystem = sysDir;
            renderSystemsList();
            try {
                const res = await fetch(`/api/games?system=${encodeURIComponent(sysDir)}`);
                const data = await res.json();
                if (data.ok) {
                    currentGames = data.games || [];
                    renderGamesGrid(currentGames);
                }
            } catch (e) {
                console.error('Error loading games:', e);
            }
        }

        function renderGamesGrid(games) {
            const container = document.getElementById('games-container');
            const emptyEl = document.getElementById('empty-state');
            if (!games || games.length === 0) {
                container.innerHTML = '';
                emptyEl.style.display = 'block';
                return;
            }
            emptyEl.style.display = 'none';
            let html = '';
            games.forEach((g, idx) => {
                const artHtml = g.has_art ? `<img src="${g.art_url}" loading="lazy" alt="${g.title}">` : `<div style="font-size:32px;">🎮</div>`;
                html += `<div class="game-card">
                    <div class="art-box">${artHtml}</div>
                    <div class="game-info">
                        <div class="game-title" title="${g.filename}">${g.title}</div>
                        <div class="game-meta">
                            <span>${g.system}</span>
                            <span>${g.size_str}</span>
                        </div>
                        <div class="game-actions">
                            <button class="btn btn-sm btn-secondary" onclick="openScrapeModal('${g.system}', '${encodeURIComponent(g.filename)}')">Cào ảnh</button>
                            <button class="btn btn-sm btn-secondary" onclick="openRenameModal('${g.system}', '${encodeURIComponent(g.filename)}')">Đổi tên</button>
                            <button class="btn btn-sm btn-secondary" onclick="openMoveModal('${g.system}', '${encodeURIComponent(g.filename)}')">Chuyển</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteGame('${g.system}', '${encodeURIComponent(g.filename)}')">Xóa</button>
                        </div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        function filterGames() {
            const q = document.getElementById('search-input').value.toLowerCase().trim();
            if (!q) {
                renderGamesGrid(currentGames);
                return;
            }
            const filtered = currentGames.filter(g => g.title.toLowerCase().includes(q) || g.filename.toLowerCase().includes(q));
            renderGamesGrid(filtered);
        }

        // ==================== TẢI GAME ONLINE (ROMS STORE) ====================
        async function loadStoreInit() {
            try {
                const res = await fetch('/api/store/categories');
                const data = await res.json();
                if (data.ok) {
                    storeCategories = data.categories || [];
                    storeSystems = data.systems || [];
                    renderStoreSidebar();
                    loadStoreGames();
                }
            } catch (e) {
                console.error('Error loadStoreInit:', e);
            }
        }

        function renderStoreSidebar() {
            const catList = document.getElementById('store-categories-list');
            let htmlCat = '';
            storeCategories.forEach(c => {
                const active = (currentStoreCategory === c.id && currentStoreSystem === 'ALL') ? 'active' : '';
                htmlCat += `<div class="sys-item ${active}" onclick="selectStoreCategory('${c.id}')">
                    <span>${c.icon} ${c.name}</span>
                </div>`;
            });
            catList.innerHTML = htmlCat;

            const sysList = document.getElementById('store-systems-list');
            let htmlSys = '';
            storeSystems.forEach(s => {
                const active = (currentStoreSystem === s.code) ? 'active' : '';
                htmlSys += `<div class="sys-item ${active}" onclick="selectStoreSystem('${s.code}')">
                    <span>${s.name}</span>
                    <span class="count">${s.count}</span>
                </div>`;
            });
            sysList.innerHTML = htmlSys;
        }

        let currentStorePage = 1;
        let storeHasMore = true;
        let isStoreLoading = false;

        function selectStoreCategory(catId) {
            currentStoreCategory = catId;
            currentStoreSystem = 'ALL';
            document.getElementById('store-search-input').value = '';
            renderStoreSidebar();
            resetAndLoadStore();
        }

        function selectStoreSystem(sysCode) {
            currentStoreSystem = sysCode;
            currentStoreCategory = 'ALL';
            document.getElementById('store-search-input').value = '';
            renderStoreSidebar();
            resetAndLoadStore();
        }

        function executeStoreSearch() {
            resetAndLoadStore();
        }

        function resetAndLoadStore() {
            currentStorePage = 1;
            storeHasMore = true;
            storeGames = [];
            loadStoreGames(false);
        }

        function loadMoreStoreGames() {
            if (!isStoreLoading && storeHasMore) {
                currentStorePage++;
                loadStoreGames(true);
            }
        }

        function handleStoreScroll(e) {
            const el = e.target;
            if (el.scrollHeight - el.scrollTop - el.clientHeight < 350) {
                if (!isStoreLoading && storeHasMore) {
                    currentStorePage++;
                    loadStoreGames(true);
                }
            }
        }

        async function loadStoreGames(isAppend = false) {
            if (isStoreLoading) return;
            isStoreLoading = true;

            const container = document.getElementById('store-games-container');
            const loading = document.getElementById('store-loading');
            const loadingMore = document.getElementById('store-loading-more');
            const emptyEl = document.getElementById('store-empty-state');
            const loadMoreBtn = document.getElementById('store-load-more-btn-container');

            if (!isAppend) {
                container.innerHTML = '';
                loading.style.display = 'block';
                emptyEl.style.display = 'none';
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            } else {
                if (loadingMore) loadingMore.style.display = 'block';
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            }

            const sort = document.getElementById('store-sort-select').value;
            const q = document.getElementById('store-search-input').value.trim();
            const limit = 40;

            let url = `/api/store/games?source_type=${currentStoreCategory}&system=${currentStoreSystem}&sort=${sort}&page=${currentStorePage}&limit=${limit}`;
            if (q) url += `&query=${encodeURIComponent(q)}`;

            try {
                const res = await fetch(url);
                const data = await res.json();
                loading.style.display = 'none';
                if (loadingMore) loadingMore.style.display = 'none';

                if (data.ok && data.games && data.games.length > 0) {
                    if (isAppend) {
                        storeGames = storeGames.concat(data.games);
                        renderStoreGrid(data.games, true);
                    } else {
                        storeGames = data.games;
                        renderStoreGrid(storeGames, false);
                    }

                    if (data.games.length < limit) {
                        storeHasMore = false;
                        if (loadMoreBtn) loadMoreBtn.style.display = 'none';
                    } else {
                        storeHasMore = true;
                        if (loadMoreBtn) loadMoreBtn.style.display = 'block';
                    }
                } else {
                    storeHasMore = false;
                    if (!isAppend) {
                        emptyEl.style.display = 'block';
                    }
                    if (loadMoreBtn) loadMoreBtn.style.display = 'none';
                }
            } catch (e) {
                loading.style.display = 'none';
                if (loadingMore) loadingMore.style.display = 'none';
                if (!isAppend) emptyEl.style.display = 'block';
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            } finally {
                isStoreLoading = false;
            }
        }

        function renderStoreGrid(games, isAppend = false) {
            const container = document.getElementById('store-games-container');
            let html = '';
            games.forEach((g, idx) => {
                const imgUrl = g.img_url ? `<img src="${g.img_url}" loading="lazy" alt="${g.title}">` : `<div style="font-size:32px;">🕹️</div>`;
                const isViet = g.is_viet ? `<span class="badge-tag badge-viet">VIỆT HÓA</span>` : '';
                const isHack = g.is_hack ? `<span class="badge-tag badge-hack">HACK</span>` : '';
                const isHit = g.is_hit ? `<span class="badge-tag badge-top">TOP</span>` : '';

                const actionBtn = g.is_installed 
                    ? `<span class="badge-tag badge-installed">✓ Đã có trên thẻ</span>`
                    : `<button class="btn btn-sm btn-green" id="btn-store-dl-${g.id}" onclick="downloadStoreGame(${g.id}, '${g.sys_code}', '${encodeURIComponent(g.title)}', '${encodeURIComponent(g.rom_url || '')}', '${encodeURIComponent(g.filename || '')}', '${encodeURIComponent(g.img_url || '')}')">⬇️ Tải về máy</button>`;

                html += `<div class="game-card">
                    <div class="art-box">${imgUrl}</div>
                    <div class="game-info">
                        <div style="display:flex; gap:4px; margin-bottom:4px; flex-wrap:wrap;">${isViet}${isHack}${isHit}</div>
                        <div class="game-title" title="${g.title}">${g.title}</div>
                        <div class="game-meta">
                            <span>${g.sys_code}</span>
                            <span>${g.file_size_str || ''}</span>
                        </div>
                        <div class="game-actions" style="margin-top:10px;">
                            ${actionBtn}
                        </div>
                    </div>
                </div>`;
            });
            if (isAppend) {
                container.insertAdjacentHTML('beforeend', html);
            } else {
                container.innerHTML = html;
            }
        }

        async function downloadStoreGame(id, sysCode, titleEnc, romUrlEnc, fnameEnc, imgUrlEnc) {
            const title = decodeURIComponent(titleEnc);
            const romUrl = decodeURIComponent(romUrlEnc);
            const fname = decodeURIComponent(fnameEnc);
            const imgUrl = decodeURIComponent(imgUrlEnc);

            const btn = document.getElementById(`btn-store-dl-${id}`);
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Đang tải...';
            }

            try {
                const res = await fetch('/api/store/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        game_id: id,
                        sys_code: sysCode,
                        title: title,
                        rom_url: romUrl,
                        filename: fname,
                        img_url: imgUrl
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(`Bắt đầu tải: ${title}`);
                    startStoreDownloadPolling();
                } else {
                    alert('Lỗi: ' + (data.error || 'Không thể tải'));
                    if (btn) { btn.disabled = false; btn.innerText = '⬇️ Tải về máy'; }
                }
            } catch (e) {
                alert('Lỗi kết nối: ' + e);
                if (btn) { btn.disabled = false; btn.innerText = '⬇️ Tải về máy'; }
            }
        }

        function startStoreDownloadPolling() {
            const banner = document.getElementById('store-download-banner');
            banner.style.display = 'block';

            if (storeDlInterval) clearInterval(storeDlInterval);
            storeDlInterval = setInterval(async () => {
                try {
                    const res = await fetch('/api/store/download/status');
                    const data = await res.json();
                    if (data.ok && data.downloads && data.downloads.length > 0) {
                        const active = data.downloads[data.downloads.length - 1];
                        const pct = active.progress_pct || 0;
                        document.getElementById('store-dl-title').innerText = `Đang tải: ${active.title} (${active.sys_code})`;
                        document.getElementById('store-dl-pct').innerText = `${pct}%`;
                        document.getElementById('store-dl-bar').style.width = `${pct}%`;
                        
                        let sizeInfo = '';
                        if (active.total_bytes > 0) {
                            const curMb = (active.downloaded_bytes / (1024 * 1024)).toFixed(1);
                            const totMb = (active.total_bytes / (1024 * 1024)).toFixed(1);
                            sizeInfo = ` (${curMb} / ${totMb} MB)`;
                        } else if (active.downloaded_bytes > 0) {
                            const curMb = (active.downloaded_bytes / (1024 * 1024)).toFixed(1);
                            sizeInfo = ` (${curMb} MB)`;
                        }

                        document.getElementById('store-dl-speed').innerText = `Tốc độ: ${active.speed_str || '0 KB/s'}${sizeInfo}`;
                        
                        if (active.status === 'completed') {
                            document.getElementById('store-dl-status').innerText = '✓ Đã tải xong và lưu vào thẻ nhớ!';
                            document.getElementById('store-dl-status').style.color = '#34d399';
                        } else if (active.status === 'error') {
                            document.getElementById('store-dl-status').innerText = `❌ ${active.error_msg || 'Lỗi tải game'}`;
                            document.getElementById('store-dl-status').style.color = '#f87171';
                        } else {
                            document.getElementById('store-dl-status').innerText = 'Đang nhận tệp...';
                            document.getElementById('store-dl-status').style.color = 'var(--text-sub)';
                        }

                        if (active.status === 'completed' || active.status === 'error') {
                            clearInterval(storeDlInterval);
                            setTimeout(() => { banner.style.display = 'none'; }, 4000);
                            loadStoreGames(false);
                            loadSystems();
                        }
                    } else {
                        clearInterval(storeDlInterval);
                        banner.style.display = 'none';
                    }
                } catch (e) {}
            }, 350);
        }

        // ==================== QUẢN LÝ YOUTUBE ====================
        async function loadYouTubeInit() {
            try {
                const res = await fetch('/api/youtube/playlists');
                const data = await res.json();
                if (data.ok) {
                    ytPlaylists = data.playlists || [];
                    renderYouTubePlaylists(data.favorites_count || 0);
                    loadYouTubeVideos('trending');
                }
            } catch (e) {
                console.error('Error loadYouTubeInit:', e);
            }
        }

        function renderYouTubePlaylists(favCount = 0) {
            const listEl = document.getElementById('yt-playlists-list');
            let html = '';
            
            // Item 1: Trending
            html += `<div class="yt-playlist-item ${currentYtTab === 'trending' ? 'active' : ''}" onclick="selectYouTubePlaylist('trending')">
                <span>🔥 Trending YouTube</span>
            </div>`;

            // Item 2: Favorites
            html += `<div class="yt-playlist-item ${currentYtTab === 'favorites' ? 'active' : ''}" onclick="selectYouTubePlaylist('favorites')">
                <span>⭐ Video Yêu thích</span>
                <span class="count" style="background:#b45309; color:#fff; font-size:11px; padding:2px 7px; border-radius:10px;">${favCount}</span>
            </div>`;

            // Custom playlists
            ytPlaylists.forEach(q => {
                const active = (currentYtTab === q) ? 'active' : '';
                html += `<div class="yt-playlist-item ${active}" onclick="selectYouTubePlaylist('${q.replace(/'/g, "\\'")}')">
                    <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;">${q}</span>
                    <button class="btn btn-sm btn-danger" style="padding:2px 6px; font-size:10px;" onclick="deletePlaylist(event, '${q.replace(/'/g, "\\'")}')">&times;</button>
                </div>`;
            });

            listEl.innerHTML = html;
        }

        function selectYouTubePlaylist(q) {
            currentYtTab = q;
            renderYouTubePlaylists();
            loadYouTubeVideos(q);
        }

        async function loadYouTubeVideos(query) {
            const container = document.getElementById('yt-videos-container');
            const loading = document.getElementById('yt-loading');
            const countEl = document.getElementById('yt-video-count');
            const titleEl = document.getElementById('yt-current-title');

            container.innerHTML = '';
            loading.style.display = 'block';

            if (query === 'favorites') {
                titleEl.innerText = '⭐ Video Yêu thích';
                try {
                    const res = await fetch('/api/youtube/favorites');
                    const data = await res.json();
                    loading.style.display = 'none';
                    if (data.ok) {
                        ytVideos = data.favorites || [];
                        countEl.innerText = `${ytVideos.length} video`;
                        renderYouTubeGrid(ytVideos, true);
                    }
                } catch (e) { loading.style.display = 'none'; }
                return;
            }

            titleEl.innerText = (query === 'trending') ? '🔥 Trending YouTube' : `📺 Playlist: ${query}`;
            try {
                const res = await fetch(`/api/youtube/search?q=${encodeURIComponent(query)}&limit=24`);
                const data = await res.json();
                loading.style.display = 'none';
                if (data.ok && data.videos) {
                    ytVideos = data.videos;
                    countEl.innerText = `${ytVideos.length} video`;
                    renderYouTubeGrid(ytVideos, false);
                }
            } catch (e) {
                loading.style.display = 'none';
            }
        }

        function executeYouTubeSearch() {
            const q = document.getElementById('yt-search-input').value.trim();
            if (!q) return;
            currentYtTab = q;
            renderYouTubePlaylists();
            loadYouTubeVideos(q);
        }

        function renderYouTubeGrid(videos, isFavList = false) {
            const container = document.getElementById('yt-videos-container');
            if (!videos || videos.length === 0) {
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-sub);">Chưa có video nào.</div>';
                return;
            }

            let html = '';
            videos.forEach(v => {
                const favBtn = isFavList 
                    ? `<button class="btn btn-sm btn-danger" onclick="removeFromFavorites('${v.id}')">❌ Xóa khỏi Yêu thích</button>`
                    : `<button class="btn btn-sm btn-gold" onclick="addToFavorites('${v.id}', '${encodeURIComponent(v.title)}', '${encodeURIComponent(v.channel || '')}', '${encodeURIComponent(v.duration || '')}', '${encodeURIComponent(v.thumb || '')}')">⭐ Lưu yêu thích</button>`;

                html += `<div class="yt-card">
                    <div class="yt-thumb-box">
                        <img src="${v.thumb}" loading="lazy" alt="${v.title}">
                        <span class="yt-dur-badge">${v.duration || 'Video'}</span>
                    </div>
                    <div class="game-info">
                        <div class="game-title" title="${v.title}">${v.title}</div>
                        <div class="game-meta">
                            <span>${v.channel || 'YouTube'}</span>
                            <span>${v.age || ''}</span>
                        </div>
                        <div class="game-actions" style="margin-top:10px;">
                            ${favBtn}
                            <a href="https://www.youtube.com/watch?v=${v.id}" target="_blank" class="btn btn-sm btn-secondary">Xem ↗</a>
                        </div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        function openImportPlaylistModal() {
            document.getElementById('import-playlist-url').value = '';
            document.getElementById('import-playlist-title').value = '';
            document.getElementById('import-playlist-status').style.display = 'none';
            document.getElementById('btn-submit-import-pl').disabled = false;
            openModal('modal-import-playlist');
        }

        async function submitImportPlaylist() {
            const url = document.getElementById('import-playlist-url').value.trim();
            const customTitle = document.getElementById('import-playlist-title').value.trim();
            if (!url) {
                alert('Vui lòng dán Link hoặc ID Playlist YouTube!');
                return;
            }

            const statusEl = document.getElementById('import-playlist-status');
            const statusText = document.getElementById('import-playlist-status-text');
            const btnSubmit = document.getElementById('btn-submit-import-pl');

            statusEl.style.display = 'block';
            statusText.innerText = '⏳ Đang quét danh sách và lấy toàn bộ video từ YouTube...';
            btnSubmit.disabled = true;

            try {
                const res = await fetch('/api/youtube/playlists/import', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url, custom_title: customTitle})
                });
                const data = await res.json();
                btnSubmit.disabled = false;

                if (data.ok) {
                    closeModal('modal-import-playlist');
                    showToast(`🎉 ${data.message}`);
                    ytPlaylists = data.playlists || [];
                    currentYtTab = data.title;
                    renderYouTubePlaylists();
                    
                    // Render the imported videos directly
                    const titleEl = document.getElementById('yt-current-title');
                    const countEl = document.getElementById('yt-video-count');
                    titleEl.innerText = `📺 Playlist: ${data.title}`;
                    countEl.innerText = `${data.count} video`;
                    ytVideos = data.videos || [];
                    renderYouTubeGrid(ytVideos, false);
                } else {
                    statusText.innerText = '❌ ' + (data.error || 'Lỗi khi nhập playlist');
                }
            } catch (e) {
                btnSubmit.disabled = false;
                statusText.innerText = '❌ Lỗi kết nối: ' + e;
            }
        }

        function openAddPlaylistModal() {
            document.getElementById('new-playlist-name').value = '';
            openModal('modal-add-playlist');
        }

        async function submitAddPlaylist() {
            const name = document.getElementById('new-playlist-name').value.trim();
            if (!name) return;
            try {
                const res = await fetch('/api/youtube/playlists/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-add-playlist');
                    showToast(`Đã thêm playlist ${name}!`);
                    ytPlaylists = data.playlists || [];
                    selectYouTubePlaylist(name);
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function deletePlaylist(e, name) {
            e.stopPropagation();
            if (!confirm(`Bạn có chắc muốn xóa playlist "${name}"?`)) return;
            try {
                const res = await fetch('/api/youtube/playlists/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(`Đã xóa playlist ${name}!`);
                    ytPlaylists = data.playlists || [];
                    selectYouTubePlaylist('trending');
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function addToFavorites(id, titleEnc, channelEnc, durEnc, thumbEnc) {
            const video = {
                id: id,
                title: decodeURIComponent(titleEnc),
                channel: decodeURIComponent(channelEnc),
                duration: decodeURIComponent(durEnc),
                thumb: decodeURIComponent(thumbEnc)
            };
            try {
                const res = await fetch('/api/youtube/favorites/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({video: video})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã lưu video vào Yêu thích!');
                    loadYouTubeInit();
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function removeFromFavorites(id) {
            try {
                const res = await fetch('/api/youtube/favorites/remove', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: id})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã xóa khỏi Yêu thích!');
                    loadYouTubeVideos('favorites');
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        function addCurrentSearchAsPlaylist() {
            const q = document.getElementById('yt-search-input').value.trim();
            if (!q) return;
            document.getElementById('new-playlist-name').value = q;
            submitAddPlaylist();
        }

        async function clearYouTubeCache() {
            if (!confirm('Dọn dẹp toàn bộ bộ nhớ đệm ảnh thumbnail YouTube trên thẻ nhớ?')) return;
            try {
                const res = await fetch('/api/youtube/cache/clear', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã dọn dẹp cache YouTube!');
                    loadStorageStatus();
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        // ==================== MODALS & HELPERS ====================
        function openRenameModal(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            selectedGame = {system: sys, filename: fn};
            document.getElementById('rename-old').value = fn;
            document.getElementById('rename-new').value = fn;
            openModal('modal-rename');
        }

        async function submitRename() {
            if (!selectedGame) return;
            const newName = document.getElementById('rename-new').value.trim();
            if (!newName) return;
            try {
                const res = await fetch('/api/rename', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        system: selectedGame.system,
                        old_filename: selectedGame.filename,
                        new_filename: newName
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-rename');
                    showToast(data.message || 'Đổi tên thành công!');
                    selectSystem(selectedGame.system);
                } else { alert('Lỗi: ' + (data.error || 'Không thể đổi tên')); }
            } catch (e) { alert('Lỗi kết nối: ' + e); }
        }

        function openMoveModal(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            selectedGame = {system: sys, filename: fn};
            document.getElementById('move-game').value = `${fn} (${sys})`;
            const sel = document.getElementById('move-target-sys');
            let opts = '';
            allSystems.forEach(s => {
                if (s.dir !== sys) opts += `<option value="${s.dir}">${s.name} (${s.dir})</option>`;
            });
            sel.innerHTML = opts;
            openModal('modal-move');
        }

        async function submitMove() {
            if (!selectedGame) return;
            const targetSys = document.getElementById('move-target-sys').value;
            if (!targetSys) return;
            try {
                const res = await fetch('/api/move', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        from_system: selectedGame.system,
                        to_system: targetSys,
                        filename: selectedGame.filename
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-move');
                    showToast(data.message || 'Chuyển hệ máy thành công!');
                    loadSystems();
                } else { alert('Lỗi: ' + (data.error || 'Không thể chuyển')); }
            } catch (e) { alert('Lỗi kết nối: ' + e); }
        }

        async function deleteGame(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            if (!confirm(`Bạn có chắc chắn muốn xóa game "${fn}" khỏi thẻ nhớ?`)) return;
            try {
                const res = await fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({system: sys, filename: fn, delete_art: true})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(`Đã xóa ${fn}`);
                    selectSystem(sys);
                } else { alert('Lỗi: ' + (data.error || 'Không thể xóa')); }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        function openScrapeModal(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            selectedGame = {system: sys, filename: fn};
            document.getElementById('scrape-query').value = cleanRomTitle(fn);
            document.getElementById('scrape-results').innerHTML = '';
            openModal('modal-scrape');
            executeScrapeSearch();
        }

        function cleanRomTitle(fn) {
            let base = fn.replace(/\.[^/.]+$/, "");
            base = base.replace(/^\d+\s*[-–—.]\s*/, "");
            return base.replace(/\(.*?\)|\[.*?\]/g, "").trim();
        }

        async function executeScrapeSearch() {
            if (!selectedGame) return;
            const q = document.getElementById('scrape-query').value.trim();
            const resBox = document.getElementById('scrape-results');
            resBox.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-sub);">Đang tìm ảnh...</div>';
            try {
                const res = await fetch(`/api/scrape/search?system=${encodeURIComponent(selectedGame.system)}&query=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.ok && data.candidates && data.candidates.length > 0) {
                    let html = '';
                    data.candidates.forEach(c => {
                        html += `<div class="game-card" style="cursor:pointer;" onclick="applyScrapedArt('${encodeURIComponent(c.url)}')">
                            <div class="art-box"><img src="${c.url}" loading="lazy" alt="Boxart"></div>
                            <div style="padding:6px; font-size:10px; color:var(--text-sub); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${c.type || 'Boxart'}</div>
                        </div>`;
                    });
                    resBox.innerHTML = html;
                } else {
                    resBox.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-sub);">Không tìm thấy ảnh. Hãy thử nhập từ khóa khác hoặc dán link bên dưới.</div>';
                }
            } catch (e) {
                resBox.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:#ef4444;">Lỗi tìm ảnh: ' + e + '</div>';
            }
        }

        async function applyScrapedArt(urlEnc) {
            if (!selectedGame) return;
            const url = decodeURIComponent(urlEnc);
            try {
                const res = await fetch('/api/scrape/auto', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        system: selectedGame.system,
                        filename: selectedGame.filename,
                        query: document.getElementById('scrape-query').value.trim(),
                        fast: false
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-scrape');
                    showToast('Đã gán ảnh bìa thành công!');
                    selectSystem(selectedGame.system);
                } else { alert('Lỗi gán ảnh: ' + (data.error || 'Thất bại')); }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function submitDirectArtUrl() {
            const url = document.getElementById('scrape-direct-url').value.trim();
            if (!url || !selectedGame) return;
            applyScrapedArt(encodeURIComponent(url));
        }

        function openGoogleImageSearch() {
            if (!selectedGame) return;
            const q = document.getElementById('scrape-query').value.trim() + ' ' + selectedGame.system + ' boxart cover';
            window.open('https://www.google.com/search?tbm=isch&q=' + encodeURIComponent(q), '_blank');
        }

        function handleUploadRomClick() {
            document.getElementById('rom-file-input-direct').click();
        }

        async function handleDirectRomFiles(e) {
            const files = e.target.files;
            if (!files || files.length === 0 || !currentSystem) return;
            for (let i = 0; i < files.length; i++) {
                const f = files[i];
                showToast(`Đang tải lên ${f.name}...`);
                try {
                    await fetch(`/api/upload_rom?system=${encodeURIComponent(currentSystem)}&filename=${encodeURIComponent(f.name)}`, {
                        method: 'POST',
                        body: f
                    });
                } catch (err) {}
            }
            showToast('Tải ROMs thành công!');
            selectSystem(currentSystem);
        }

        // ==================== SAVE & CHEATS MODAL ====================
        function openSavesCheatsModal(tab = 'saves') {
            switchSavesCheatsTab(tab);
            openModal('modal-saves-cheats');
        }

        function switchSavesCheatsTab(tab) {
            ['saves', 'cheats', 'logs'].forEach(t => {
                const btn = document.getElementById(`tab-btn-${t}`);
                const c = document.getElementById(`tab-content-${t}`);
                if (btn) btn.className = (t === tab) ? 'btn btn-sm' : 'btn btn-sm btn-secondary';
                if (c) c.style.display = (t === tab) ? 'block' : 'none';
            });
            if (tab === 'saves') loadSavesData();
            else if (tab === 'cheats') loadCheatsData();
        }

        async function loadSavesData() {
            try {
                const res = await fetch('/api/saves');
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('saves-stats-text').innerText = `Tổng cộng ${data.stats ? data.stats.total_files : 0} file save trên thẻ nhớ.`;
                    const box = document.getElementById('backups-list-table');
                    if (!data.backups || data.backups.length === 0) {
                        box.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-sub); font-size:12px;">Chưa có bản sao lưu nào. Hãy bấm "+ Tạo bản sao lưu mới" ở trên!</div>';
                        return;
                    }
                    let html = '';
                    data.backups.forEach(b => {
                        html += `<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 10px; border-bottom:1px solid var(--border); font-size:12px;">
                            <div>
                                <strong style="color:#38bdf8;">${b.created_at || b.filename}</strong>
                                <span style="color:var(--text-sub); margin-left:8px;">(${b.size_str})</span>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <a href="/api/saves/download?file=${encodeURIComponent(b.filename)}" class="btn btn-sm btn-secondary" download>Tải về (.zip)</a>
                                <button class="btn btn-sm btn-green" onclick="restoreSaveBackupWeb('${b.filename}')">Khôi phục</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteSaveBackupWeb('${b.filename}')">Xóa</button>
                            </div>
                        </div>`;
                    });
                    box.innerHTML = html;
                }
            } catch (e) {}
        }

        async function createSaveBackupWeb() {
            try {
                const res = await fetch('/api/saves/backup', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã tạo bản sao lưu thành công!');
                    loadSavesData();
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function restoreSaveBackupWeb(fn) {
            if (!confirm(`Khôi phục dữ liệu từ bản sao lưu "${fn}"?`)) return;
            try {
                const res = await fetch('/api/saves/restore', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: fn})
                });
                const data = await res.json();
                if (data.ok) showToast(data.message || 'Khôi phục thành công!');
                else alert('Lỗi: ' + data.error);
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function deleteSaveBackupWeb(fn) {
            if (!confirm(`Xóa bản sao lưu "${fn}"?`)) return;
            try {
                const res = await fetch('/api/saves/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: fn})
                });
                const data = await res.json();
                if (data.ok) { showToast('Đã xóa bản sao lưu!'); loadSavesData(); }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function loadCheatsData() {
            try {
                const res = await fetch('/api/cheats/status');
                const data = await res.json();
                if (data.ok && data.status) {
                    document.getElementById('cheats-status-box').innerHTML = `Đã cài đặt: <strong>${data.status.installed_count}</strong> file cheat trên máy. Tổng kho Libretro: <strong>${data.status.total_available}</strong> game hỗ trợ cheat.`;
                }
            } catch (e) {}
        }

        async function downloadCheatsWeb(mode) {
            try {
                const res = await fetch('/api/cheats/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: mode})
                });
                const data = await res.json();
                if (data.ok) showToast(data.message || 'Đang tải kho cheat...');
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function sendLogTelegramWeb() {
            try {
                const res = await fetch('/api/logs/send-telegram', {method: 'POST'});
                const data = await res.json();
                if (data.ok) showToast('Đã gửi nhật ký lên Telegram tác giả!');
                else alert('Lỗi: ' + data.error);
            } catch (e) { alert('Lỗi: ' + e); }
        }

        
        // ==================== AI CHATBOT ====================
        let aiChatHistory = [
            { role: "system", content: `Bạn là trợ lý AI chuyên gia điều hành hệ sinh thái RetroHub và thiết bị TrimUI Smart Pro (Linux/Busybox aarch64).
Bạn có quyền thực thi lệnh trực tiếp trên máy thông qua shell bằng cách đề xuất lệnh cho người dùng bấm chạy.

QUY TẮC LÀM VIỆC CỐT LÕI (BẮT BUỘC TUÂN THỦ):
1. LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT, ngắn gọn, súc tích, đi thẳng vào giải pháp kỹ thuật.
2. TUYỆT ĐỐI KHÔNG ĐOÁN MÒ: Không tự suy diễn đường dẫn file, file log hay cấu hình hệ thống khi chưa được cung cấp hoặc chưa kiểm chứng. Mọi thông tin chưa rõ PHẢI được điều tra bằng câu lệnh thực tế.
3. HÀNH ĐỘNG BẰNG CÂU LỆNH: Mọi thao tác kiểm tra, chẩn đoán, đọc log, sửa lỗi PHẢI viết dưới dạng câu lệnh shell trong block \`\`\`bash ... \`\`\` (hoặc [CMD]...[/CMD]) để người dùng bấm chạy, sau đó dựa vào kết quả thực tế để tư vấn tiếp.
4. KHÔNG dùng cú pháp LaTeX (như $\rightarrow$, $\textbf{}$), chỉ dùng ký tự Unicode (->, →, **bold**).

ĐẶC THÙ HỆ THỐNG CẦN NHỚ:
- Python 3 trên máy KHÔNG hỗ trợ module SSL: Tuyệt đối không dùng code Python import ssl. Các tác vụ mạng HTTPS phải dùng \`curl -s -k\`.
- Môi trường Shell là Busybox/Ash: Ưu tiên các lệnh tiêu chuẩn, tránh dùng các flag nâng cao không được Busybox hỗ trợ.
- Khi người dùng gửi "Thông tin máy", hãy đọc kỹ phần cứng, danh sách giả lập (/Emus), Apps, RetroArch Cores, cấu trúc RetroHub và các file log thực tế để đưa ra câu lệnh chính xác 100%.` }
        ];

        function appendChatMessage(role, text, skipEscape = false, isCard = false) {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
            
            const bubble = document.createElement('div');
            bubble.style.maxWidth = '85%';
            bubble.style.fontSize = '14px';
            bubble.style.lineHeight = '1.4';
            bubble.style.whiteSpace = 'pre-wrap';
            bubble.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            
            if (isCard) {
                bubble.style.background = 'transparent';
                bubble.style.padding = '0';
                bubble.style.border = 'none';
                bubble.style.boxShadow = 'none';
            } else if (role === 'user') {
                bubble.style.background = '#0284c7';
                bubble.style.color = '#fff';
                bubble.style.padding = '8px 12px';
                bubble.style.borderRadius = '12px';
                bubble.style.borderBottomRightRadius = '4px';
                bubble.style.border = '1px solid #0369a1';
            } else {
                bubble.style.background = '#1e293b';
                bubble.style.color = '#f8fafc';
                bubble.style.padding = '8px 12px';
                bubble.style.borderRadius = '12px';
                bubble.style.borderBottomLeftRadius = '4px';
                bubble.style.border = '1px solid #334155';
            }
            
            // Escape HTML
            let safeText = skipEscape ? text : text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            // Format basic markdown
            safeText = safeText.replace(/\$\\rightarrow\$/g, '→').replace(/\$\\leftarrow\$/g, '←');
            safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            safeText = safeText.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            // Format executable blocks FIRST ([CMD] or ```bash) -> Single Row
            let cmdCount = 0;
            let allCmds = [];
            safeText = safeText.replace(/\[CMD\]([\s\S]*?)\[\/CMD\]|```(?:[a-zA-Z0-9]+)?\n?([\s\S]*?)```/gi, (match, cmd1, cmd2) => {
                const cmdText = cmd1 || cmd2;
                cmdCount++;
                const rawCmd = cmdText.trim();
                allCmds.push(rawCmd);
                const b64Cmd = btoa(encodeURIComponent(rawCmd));
                
                return `<div style="display: flex; align-items: center; justify-content: space-between; background: #070a13; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 6px 4px 10px; margin: 4px 0; gap: 8px; max-width: 100%;">
                    <code style="font-family: monospace; color: #38bdf8; font-size: 13px; line-height: 1.4; white-space: pre-wrap; word-break: break-all; flex: 1;">${rawCmd}</code>
                    <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); cursor: pointer; padding: 4px 6px; border-radius: 4px; color: #34d399; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; outline: none; transition: all 0.2s;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                </div>`;
            });
            
            // Format inline code (`)
            safeText = safeText.replace(/`([^`\n]+)`/g, `<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 4px; font-size: 13px; color: #38bdf8;">$1</code>`);
            
            if (cmdCount > 1) {
                const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                safeText += `<div style="display: flex; justify-content: flex-end; margin-top: 6px;">
                    <div style="display: inline-flex; align-items: center; background: #070a13; border: 1px solid rgba(234, 179, 8, 0.35); border-radius: 6px; padding: 3px 6px 3px 10px; gap: 8px;">
                        <span style="font-family: monospace; color: #facc15; font-size: 12px; font-weight: 600;">⚡ Chạy tất cả (${cmdCount} lệnh)</span>
                        <button onclick="executeAllAiCommands(event, '${b64Cmds}')" title="Thực thi tất cả theo thứ tự" style="background: rgba(234, 179, 8, 0.15); border: none; cursor: pointer; padding: 3px 6px; border-radius: 4px; color: #facc15; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; outline: none; transition: all 0.2s;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                    </div>
                </div>`;
            }

            bubble.innerHTML = safeText;
            wrapper.appendChild(bubble);
            container.appendChild(wrapper);
            
            // Auto scroll to bottom smoothly
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 50);
        }

        async function executeAllAiCommands(e, b64Cmds) {
            const cmds = JSON.parse(decodeURIComponent(atob(b64Cmds)));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            
            let combinedOutput = "";
            for(let i=0; i<cmds.length; i++) {
                const cmd = cmds[i];
                try {
                    const res = await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: cmd})
                    });
                    const data = await res.json();
                    const rawOut = (data.output || '').trim();
                    const code = (typeof data.code !== 'undefined') ? data.code : 0;
                    const outLog = rawOut || (code === 0 ? '(Thành công - Không có output)' : `(Mã lỗi: ${code})`);
                    combinedOutput += `--- [${i+1}/${cmds.length}] ${cmd} (Exit: ${code}) ---\n${outLog}\n\n`;
                } catch(err) {
                    combinedOutput += `--- [${i+1}/${cmds.length}] ${cmd} (Lỗi) ---\n${err.message}\n\n`;
                }
            }
            
            btn.innerHTML = '✅';
            btn.style.background = 'rgba(56, 189, 248, 0.15)';
            btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            btn.style.color = '#38bdf8';
            
            const systemPromptText = `[System Execution Result]\n${combinedOutput.trim()}`;
            const safeCombined = combinedOutput.trim().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #facc15; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                    <span style="display: flex; align-items: center; gap: 6px;">
                        <span>⚡</span> Đã thực thi ${cmds.length} lệnh
                    </span>
                    <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem log)</span>
                </summary>
                <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeCombined}</div>
            </details>`;
            appendChatMessage('user', htmlText, true, true);
            aiChatHistory.push({ role: 'user', content: systemPromptText });
            
            document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
            document.getElementById('chat-submit-btn').disabled = true;
            doHeadlessAiFetch();
        }


        async function sendDeviceInfoToAI() {
            const btn = document.getElementById('btn-send-info');
            if(btn) { btn.disabled = true; btn.innerHTML = '⏳ Đang quét...'; }
            
            const cmd = 'echo "--- SYSTEM INFO ---"; uname -a; echo ""; echo "--- RAM ---"; free -m; echo ""; echo "--- DISK ---"; df -h; echo ""; echo "--- ROOT DIR ---"; ls -la /mnt/SDCARD | head -n 30; echo ""; echo "--- ROMS DIRS ---"; ls -d /mnt/SDCARD/Roms/*/ 2>/dev/null; echo ""; echo "--- GIẢ LẬP ĐÃ CÀI (/mnt/SDCARD/Emus) ---"; ls -d /mnt/SDCARD/Emus/*/ 2>/dev/null; echo ""; echo "--- APPS (/mnt/SDCARD/Apps) ---"; ls -d /mnt/SDCARD/Apps/*/ 2>/dev/null; echo ""; echo "--- CẤU TRÚC APP RETROHUB ---"; find /mnt/SDCARD/Apps/RetroHub -maxdepth 2 2>/dev/null | grep -v "/\._" | head -n 45; echo ""; echo "--- RETROARCH CORES (.so) ---"; ls /mnt/SDCARD/RetroArch/.retroarch/cores/*.so 2>/dev/null | awk -F/ "{print \$NF}"; echo ""; echo "--- CÁC FILE LOG THỰC TẾ TRÊN MÁY ---"; find /mnt/SDCARD /tmp -maxdepth 5 -type f 2>/dev/null | grep -iE "\.(log|out)$|loi\.txt$" | grep -v "\._" | head -n 30';
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                const outLog = data.output || '(Lỗi đọc dữ liệu)';
                const safeLog = outLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #34d399; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span>📡</span> Đã nạp cấu hình & giả lập máy cho AI
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem chi tiết)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeLog}</div>
                </details>`;
                
                appendChatMessage('user', htmlText, true, true);
                
                const plainText = 'Đây là toàn bộ thông tin phần cứng, danh sách giả lập đã cài (/mnt/SDCARD/Emus, RetroArch Cores, Apps), cấu trúc thư mục và các file log thực tế trên máy TrimUI:\n```\n' + outLog + '\n```\nHãy ghi nhớ các giả lập và file log này để tư vấn chính xác.';
                aiChatHistory.push({ role: 'user', content: plainText });
                
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                
                doHeadlessAiFetch();
            } catch (e) {
                alert('Lỗi lấy thông tin: ' + e.message);
            } finally {
                if(btn) { btn.disabled = false; btn.innerHTML = '📡 Gửi thông tin máy'; }
            }
        }

        async function executeAiCommand(e, b64Cmd) {
            const cmd = decodeURIComponent(atob(b64Cmd));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                
                const rawOut = (data.output || '').trim();
                const code = (typeof data.code !== 'undefined') ? data.code : 0;
                let displayLog = rawOut;
                if (!displayLog) {
                    if (code === 0) {
                        displayLog = '✓ Lệnh đã thực thi thành công (Không có text xuất ra terminal / Exit code: 0)';
                    } else {
                        displayLog = `⚠️ Lệnh hoàn tất với mã lỗi (Exit code: ${code})`;
                    }
                }
                const safeLog = displayLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #38bdf8; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span style="color: #34d399;">✓</span> Kết quả thực thi
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem log)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeLog}</div>
                </details>`;
                
                const plainText = `Đã thực thi lệnh trên TrimUI: \`${cmd}\`\nKết quả:\n\`\`\`\n${rawOut || '(Lệnh hoàn tất - Không có output)'}\n\`\`\`\nExit code: ${code}`;
                
                btn.innerHTML = '✅';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';
                
                // Add to chat and send to AI
                appendChatMessage('user', htmlText, true, true);
                aiChatHistory.push({ role: 'user', content: plainText });
                
                // Send headless request
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                
                doHeadlessAiFetch();
                
            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
            }
        }
        
        async function doHeadlessAiFetch() {
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: 'auto', messages: aiChatHistory })
                });
                if (!res.ok) throw new Error('Mã lỗi API: ' + res.status);
                const data = await res.json();
                if (data.error) {
                    const errMsg = typeof data.error === 'object' ? (data.error.message || JSON.stringify(data.error)) : data.error;
                    throw new Error(errMsg);
                }
                if (data.choices && data.choices.length > 0) {
                    const reply = data.choices[0].message.content;
                    appendChatMessage('assistant', reply);
                    aiChatHistory.push({ role: 'assistant', content: reply });
                } else {
                    appendChatMessage('assistant', 'Lỗi: Phản hồi từ AI bị rỗng.');
                }
            } catch (err) {
                appendChatMessage('assistant', '⚠️ Lỗi khi phản hồi: ' + err.message);
            } finally {
                const btn = document.getElementById('chat-submit-btn');
                btn.disabled = false;
                btn.textContent = 'Gửi ✈️';
            }
        }

        function showSystemPrompt() {
            const sysPrompt = aiChatHistory.length > 0 ? aiChatHistory[0].content : "Không tìm thấy System Prompt.";
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**

\`\`\`text
${sysPrompt}
\`\`\``);
        }

        function clearAIChat() {
            if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện?')) return;
            
            aiChatHistory = [{ role: "system", content: "You are a helpful AI assistant integrated into a RetroHub gaming device web manager. Answer in Vietnamese. Be concise and friendly." }];
            const container = document.getElementById('chat-messages');
            if (container) {
                container.innerHTML = `
                    <div style="display:flex; justify-content:flex-start;">
                        <div style="background:#1e293b; color:#f8fafc; padding:10px 14px; border-radius:12px; border-bottom-left-radius:4px; max-width:85%; font-size:14.5px; line-height:1.45; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                            Đã dọn dẹp lịch sử trò chuyện. Tôi có thể giúp gì cho bạn tiếp theo?
                        </div>
                    </div>
                `;
            }
        }

        async function sendChatMessage(e) {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;
            
            const btn = document.getElementById('chat-submit-btn');
            input.value = '';
            input.disabled = true;
            btn.disabled = true;
            btn.innerHTML = 'Đang nghĩ... <span style="font-size:12px;">⏳</span>';
            
            appendChatMessage('user', text);
            aiChatHistory.push({ role: 'user', content: text });
            
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        model: 'auto',
                        messages: aiChatHistory
                    })
                });
                
                if (!res.ok) {
                    throw new Error('Mã lỗi API: ' + res.status);
                }
                
                const data = await res.json();
                if (data.error) {
                    const errMsg = typeof data.error === 'object' ? (data.error.message || JSON.stringify(data.error)) : data.error;
                    throw new Error(errMsg);
                }
                if (data.choices && data.choices.length > 0) {
                    const reply = data.choices[0].message.content;
                    appendChatMessage('assistant', reply);
                    aiChatHistory.push({ role: 'assistant', content: reply });
                } else {
                    appendChatMessage('assistant', 'Lỗi: Phản hồi từ AI bị rỗng.');
                }
            } catch (err) {
                appendChatMessage('assistant', '⚠️ Không thể kết nối tới máy chủ AI. Chi tiết lỗi: ' + err.message);
                // Remove the user message from history so they can try again if they want, or just let it be
            } finally {
                input.disabled = false;
                btn.disabled = false;
                btn.textContent = 'Gửi ✈️';
                input.focus();
            }
        }


        // ==================== STREAM JS LOGIC ====================
        function openStreamNewTab() {
            window.open('http://' + window.location.hostname + ':8088', '_blank');
        }

        async function checkStreamStatus() {
            const statusBadge = document.getElementById('stream-status-badge');
            const toggleBtn = document.getElementById('btn-stream-toggle');
            const newTabBtn = document.getElementById('btn-stream-newtab');
            if (!statusBadge || !toggleBtn) return;
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: 'ps | grep "python.*streamer.py" | grep -v grep'})
                });
                const data = await res.json();
                const out = data.output || '';
                if (out.includes('streamer.py')) {
                    statusBadge.textContent = '🟢 Đang chạy';
                    statusBadge.style.color = '#10b981';
                    toggleBtn.innerHTML = '🛑 Tắt Stream';
                    toggleBtn.className = 'btn btn-danger';
                    if (newTabBtn) newTabBtn.style.display = 'inline-flex';
                } else {
                    statusBadge.textContent = '🔴 Đã tắt';
                    statusBadge.style.color = '#ef4444';
                    toggleBtn.innerHTML = '▶️ Bật Stream ngay';
                    toggleBtn.className = 'btn btn-secondary';
                    if (newTabBtn) newTabBtn.style.display = 'none';
                }
            } catch(e) {
                statusBadge.textContent = '⚠️ Lỗi kiểm tra';
            }
        }

        async function toggleScreenStream() {
            const toggleBtn = document.getElementById('btn-stream-toggle');
            if (!toggleBtn) return;
            
            const isRunning = toggleBtn.innerHTML.includes('Tắt');
            toggleBtn.disabled = true;
            toggleBtn.innerHTML = '⏳ Đang xử lý...';
            
            try {
                if (isRunning) {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'kill -9 $(ps | awk "/streamer\.py/ {print $1}")'})
                    });
                } else {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'nohup /mnt/SDCARD/System/bin/python3 /mnt/SDCARD/Apps/RetroHub/streamer.py > /dev/null 2>&1 &'})
                    });
                    
                    // Tự động mở tab mới khi bật stream thành công (sau 1.5s để server kịp khởi động)
                    setTimeout(() => {
                        window.open('http://' + window.location.hostname + ':8088', '_blank');
                    }, 1500);
                }
                setTimeout(checkStreamStatus, 1500);
            } catch(e) {
                alert('Lỗi: ' + e.message);
                checkStreamStatus();
            } finally {
                setTimeout(() => toggleBtn.disabled = false, 1500);
            }
        }
        
        // Auto-check stream status initially
        setTimeout(checkStreamStatus, 1000);

        // Khởi động trang web
        loadStorageStatus();
        
        // Đọc hash từ URL (ví dụ: /#chat)
        const initialTab = window.location.hash.replace('#', '');
        if (initialTab && document.getElementById(`nav-btn-${initialTab}`)) {
            switchMainTab(initialTab);
        } else {
            loadSystems(); // Mặc định
        }
    </script>
</body>
</html>
"""


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
