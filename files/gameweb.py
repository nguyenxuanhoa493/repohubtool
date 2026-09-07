#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# RETROHUB - WEB GAME MANAGER (PORT 8090)
# Quản lý kho game qua Web: Đổi tên, Cào ảnh bìa (Scrape Art), Chuyển hệ máy, Tải ROM
# Hoàn toàn thuần Python stdlib - Zero external dependencies - Siêu nhẹ, mượt mà
# ==============================================================================

import os
import sys
import time
import json
import shutil
import urllib.request
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 8090

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

# Mapping sang tên repository của Libretro Thumbnails
LIBRETRO_MAP = {
    "GBA": "Nintendo_-_Game_Boy_Advance",
    "GBC": "Nintendo_-_Game_Boy_Color",
    "GB": "Nintendo_-_Game_Boy",
    "FC": "Nintendo_-_Nintendo_Entertainment_System",
    "NES": "Nintendo_-_Nintendo_Entertainment_System",
    "SFC": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "SNES": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "N64": "Nintendo_-_Nintendo_64",
    "NDS": "Nintendo_-_Nintendo_DS",
    "MD": "Sega_-_Mega_Drive_-_Genesis",
    "GENESIS": "Sega_-_Mega_Drive_-_Genesis",
    "SEGACD": "Sega_-_Mega-CD_-_Sega_CD",
    "GG": "Sega_-_Game_Gear",
    "MS": "Sega_-_Master_System_-_Mark_III",
    "SS": "Sega_-_Saturn",
    "DC": "Sega_-_Dreamcast",
    "PS": "Sony_-_PlayStation",
    "PS1": "Sony_-_PlayStation",
    "PSP": "Sony_-_PlayStation_Portable",
    "PCE": "NEC_-_PC_Engine_-_TurboGrafx_16",
    "WS": "Bandai_-_WonderSwan",
    "WSC": "Bandai_-_WonderSwan_Color",
    "NGP": "SNK_-_Neo_Geo_Pocket",
    "NEOGEO": "SNK_-_Neo_Geo",
    "ATARI2600": "Atari_-_2600",
    "ATARI7800": "Atari_-_7800",
    "LYNX": "Atari_-_Lynx",
    "FBNEO": "FBNeo_-_Arcade_Games",
    "MAME": "MAME",
    "ARCADE": "FBNeo_-_Arcade_Games",
}

# Đuôi file ROM hợp lệ thường gặp
VALID_EXTS = {
    ".zip", ".7z", ".rar", ".chd", ".iso", ".cue", ".bin", ".pbp",
    ".gba", ".gbc", ".gb", ".nes", ".sfc", ".smc", ".md", ".smd", ".gen",
    ".n64", ".z64", ".v64", ".nds", ".cso", ".pce", ".ws", ".wsc",
    ".ngp", ".ngc", ".p8", ".png", ".jar", ".a26", ".a78", ".lnx"
}

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
                art_url = f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(art_file)}" if has_art else None

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

        if path == "/api/systems":
            systems = list_all_systems()
            self.send_json({"ok": True, "systems": systems})
            return

        if path == "/api/games":
            sys_dir = query.get("system", [""])[0]
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
                        self.send_header("Cache-Control", "public, max-age=86400")
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
            if not q_name:
                self.send_json({"ok": False, "error": "Query required"}, 400)
                return

            repo_name = LIBRETRO_MAP.get(sys_code) or LIBRETRO_MAP.get(sys_code.replace(" ", "_"))
            if not repo_name:
                for k, v in LIBRETRO_MAP.items():
                    if k in sys_code:
                        repo_name = v
                        break

            candidates = []
            if repo_name:
                clean_q = q_name.replace("&", "_").replace("*", "_").replace("/", "_").replace(":", "_").replace("`", "_")
                boxart_url = f"https://raw.githubusercontent.com/libretro-thumbnails/{repo_name}/master/Named_Boxarts/{urllib.parse.quote(clean_q)}.png"
                candidates.append({
                    "title": f"{q_name} (Named Boxart)",
                    "type": "Boxart",
                    "url": boxart_url
                })
                title_url = f"https://raw.githubusercontent.com/libretro-thumbnails/{repo_name}/master/Named_Titles/{urllib.parse.quote(clean_q)}.png"
                candidates.append({
                    "title": f"{q_name} (Title Screen)",
                    "type": "Title Screen",
                    "url": title_url
                })
                snap_url = f"https://raw.githubusercontent.com/libretro-thumbnails/{repo_name}/master/Named_Snaps/{urllib.parse.quote(clean_q)}.png"
                candidates.append({
                    "title": f"{q_name} (Gameplay Snap)",
                    "type": "Snap",
                    "url": snap_url
                })

            self.send_json({
                "ok": True,
                "system": sys_code,
                "query": q_name,
                "repo": repo_name,
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

        if path == "/api/scrape/apply":
            try:
                payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
                sys_dir = payload.get("system", "").strip()
                fname = payload.get("filename", "").strip()
                img_url = payload.get("image_url", "").strip()

                if not sys_dir or not fname or not img_url:
                    self.send_json({"ok": False, "error": "Thiếu dữ liệu cào ảnh"}, 400)
                    return

                base_name = os.path.splitext(fname)[0]
                target_img_dir = os.path.join(IMGS_DIR, sys_dir)
                os.makedirs(target_img_dir, exist_ok=True)
                target_art = os.path.join(target_img_dir, base_name + ".png")

                req = urllib.request.Request(img_url, headers={"User-Agent": "RetroHub-Tool/1.89"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        data = resp.read()
                        with open(target_art, "wb") as f:
                            f.write(data)
                        self.send_json({
                            "ok": True,
                            "message": f"Đã tải và gán ảnh bìa thành công cho {fname}!",
                            "art_url": f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?t={int(time.time())}"
                        })
                        return
                    else:
                        self.send_json({"ok": False, "error": f"Không thể tải ảnh: HTTP {resp.status}"}, 400)
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

            try:
                data = self.rfile.read(content_len)
                with open(target_art, "wb") as f:
                    f.write(data)
                self.send_json({
                    "ok": True,
                    "message": "Đã tải lên ảnh bìa thành công!",
                    "art_url": f"/art/{urllib.parse.quote(sys_dir)}/{urllib.parse.quote(base_name + '.png')}?t={int(time.time())}"
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
            height: 180px;
            background: #0f172a;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .art-img { width: 100%; height: 100%; object-fit: contain; padding: 6px; }
        .art-placeholder { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #475569; }
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
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            max-height: 280px;
            overflow-y: auto;
            padding: 4px;
        }
        .scrape-card {
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            background: #0f172a;
            cursor: pointer;
            transition: border-color 0.15s;
        }
        .scrape-card:hover { border-color: var(--primary); }
        .scrape-img { width: 100%; height: 110px; object-fit: contain; background: #000; border-radius: 4px; }
        .scrape-label { font-size: 10px; text-align: center; color: var(--text-sub); }

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
            <button class="btn btn-sm btn-secondary" onclick="loadSystems(true)">⟲ Nạp lại</button>
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
                    <span class="search-icon">🔍</span>
                    <input type="text" id="search-input" placeholder="Tìm game trong hệ..." oninput="filterGames()">
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-green" onclick="openUploadRomModal()">+ Tải ROM lên</button>
                </div>
            </div>

            <div id="games-container" class="games-grid"></div>
            <div id="empty-state" style="display:none; text-align:center; padding: 60px 20px; color: var(--text-sub);">
                <div style="font-size: 40px; margin-bottom: 12px;">📂</div>
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
        <div class="modal-box" style="max-width: 640px;">
            <div class="modal-header">
                <h3>Cào ảnh bìa (Boxart)</h3>
                <button class="modal-close" onclick="closeModal('modal-scrape')">&times;</button>
            </div>
            <div style="display: flex; gap: 8px;">
                <input type="text" id="scrape-query" style="flex:1; background:#0f172a; border:1px solid var(--border); color:#fff; padding:8px 12px; border-radius:6px;" placeholder="Nhập từ khóa tìm kiếm ảnh...">
                <button class="btn btn-sm" onclick="executeScrapeSearch()">Tìm ảnh</button>
            </div>
            <div style="font-size:11px; color:var(--text-sub);">Nguồn: Libretro Thumbnails Official Database & Fast CDN</div>
            
            <div id="scrape-results" class="scrape-candidates"></div>

            <div style="border-top:1px solid var(--border); padding-top:12px; display:flex; justify-content:space-between; align-items:center;">
                <label class="btn btn-sm btn-secondary" style="margin:0; cursor:pointer;">
                    📁 Tải ảnh từ máy
                    <input type="file" id="art-file-input" accept="image/*" style="display:none" onchange="uploadCustomArt(event)">
                </label>
                <button class="btn btn-secondary btn-sm" onclick="closeModal('modal-scrape')">Đóng</button>
            </div>
        </div>
    </div>

    <div class="modal-backdrop" id="modal-upload-rom">
        <div class="modal-box">
            <div class="modal-header">
                <h3>Tải ROM lên hệ máy</h3>
                <button class="modal-close" onclick="closeModal('modal-upload-rom')">&times;</button>
            </div>
            <div class="form-group">
                <label>Hệ máy đích</label>
                <select id="upload-target-sys"></select>
            </div>
            <div class="form-group">
                <label>Chọn tệp ROM (.zip, .gba, .sfc, .chd, .iso...)</label>
                <input type="file" id="rom-file-input" multiple>
            </div>
            <div id="upload-progress" style="display:none; font-size:13px; color:#38bdf8; text-align:center;">Đang tải lên...</div>
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-upload-rom')">Đóng</button>
                <button class="btn btn-green" onclick="submitUploadRom()">Bắt đầu tải</button>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        let allSystems = [];
        let currentSystem = null;
        let currentGames = [];
        let selectedGame = null;

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

        async function loadSystems(refresh=false) {
            try {
                const res = await fetch("/api/systems");
                const data = await res.json();
                if (data.ok) {
                    allSystems = data.systems;
                    renderSystems();
                    if (!currentSystem && allSystems.length > 0) {
                        selectSystem(allSystems[0].dir);
                    } else if (refresh && currentSystem) {
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
            listEl.innerHTML = allSystems.map(s => `
                <div class="sys-item ${currentSystem === s.dir ? 'active' : ''}" onclick="selectSystem('${s.dir}')">
                    <span>${s.name}</span>
                    <span class="count">${s.count}</span>
                </div>
            `).join('');
        }

        async function selectSystem(sysDir) {
            currentSystem = sysDir;
            renderSystems();
            document.getElementById("search-input").value = "";
            const cont = document.getElementById("games-container");
            cont.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-sub);">Đang tải danh sách game...</div>`;
            document.getElementById("empty-state").style.display = "none";

            try {
                const res = await fetch(`/api/games?system=${encodeURIComponent(sysDir)}`);
                const data = await res.json();
                if (data.ok) {
                    currentGames = data.games;
                    renderGames(currentGames);
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
            cont.innerHTML = games.map(g => `
                <div class="game-card">
                    <div class="art-box">
                        ${g.has_art ? `<img class="art-img" src="${g.art_url}" loading="lazy" alt="${g.name}">` : `
                            <div class="art-placeholder">
                                <div style="font-size:28px;">🎮</div>
                                <span style="font-size:11px;">Chưa có ảnh bìa</span>
                            </div>
                        `}
                        <div class="art-btn-overlay">
                            <button class="btn btn-sm btn-green" onclick="openScrapeModal('${escapeJs(g.filename)}')">🎨 Cào Art</button>
                        </div>
                    </div>
                    <div class="game-info">
                        <div class="game-title" title="${g.filename}">${g.name}</div>
                        <div class="game-meta">
                            <span>${g.ext.toUpperCase()}</span>
                            <span>${g.size_str}</span>
                        </div>
                        <div class="game-actions">
                            <button class="btn btn-secondary btn-sm" style="flex:1" onclick="openRenameModal('${escapeJs(g.filename)}')">✏️ Sửa</button>
                            <button class="btn btn-secondary btn-sm" style="flex:1" onclick="openMoveModal('${escapeJs(g.filename)}')">📦 Chuyển</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteGame('${escapeJs(g.filename)}')">🗑️</button>
                        </div>
                    </div>
                </div>
            `).join('');
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

        function openRenameModal(filename) {
            selectedGame = filename;
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
            try {
                const res = await fetch("/api/rename", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        system: currentSystem,
                        old_filename: selectedGame,
                        new_filename: newName
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-rename");
                    selectSystem(currentSystem);
                } else {
                    showToast(data.error, true);
                }
            } catch (e) {
                showToast("Lỗi khi đổi tên game!", true);
            }
        }

        function openMoveModal(filename) {
            selectedGame = filename;
            document.getElementById("move-game").value = filename;
            const sel = document.getElementById("move-target-sys");
            sel.innerHTML = allSystems.filter(s => s.dir !== currentSystem).map(s => `
                <option value="${s.dir}">${s.name} (${s.dir})</option>
            `).join('');
            document.getElementById("modal-move").style.display = "flex";
        }

        async function submitMove() {
            const targetSys = document.getElementById("move-target-sys").value;
            if (!targetSys) return;
            try {
                const res = await fetch("/api/move", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        from_system: currentSystem,
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

        async function deleteGame(filename) {
            if (!confirm(`Bạn có chắc chắn muốn xóa game "${filename}" khỏi thẻ nhớ không?`)) return;
            try {
                const res = await fetch("/api/delete", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        system: currentSystem,
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

        function openScrapeModal(filename) {
            selectedGame = filename;
            const base = filename.replace(/\.[^/.]+$/, "");
            document.getElementById("scrape-query").value = base;
            document.getElementById("scrape-results").innerHTML = "";
            document.getElementById("modal-scrape").style.display = "flex";
            executeScrapeSearch();
        }

        async function executeScrapeSearch() {
            const q = document.getElementById("scrape-query").value.trim();
            if (!q) return;
            const resBox = document.getElementById("scrape-results");
            resBox.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-sub);">Đang tìm ảnh bìa...</div>`;

            try {
                const res = await fetch(`/api/scrape/search?system=${encodeURIComponent(currentSystem)}&query=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.ok && data.candidates.length > 0) {
                    resBox.innerHTML = data.candidates.map((c, idx) => `
                        <div class="scrape-card" onclick="applyScrapedArt('${escapeJs(c.url)}')">
                            <img class="scrape-img" src="${c.url}" onerror="this.parentElement.style.display='none'" alt="${c.type}">
                            <span class="scrape-label">${c.type}</span>
                        </div>
                    `).join('');
                } else {
                    resBox.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-sub);">Không tìm thấy ảnh trên CDN cho từ khóa này. Bạn có thể bấm "Tải ảnh từ máy" bên dưới!</div>`;
                }
            } catch (e) {
                resBox.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--danger);">Lỗi tìm ảnh bìa!</div>`;
            }
        }

        async function applyScrapedArt(url) {
            try {
                const res = await fetch("/api/scrape/apply", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        system: currentSystem,
                        filename: selectedGame,
                        image_url: url
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-scrape");
                    selectSystem(currentSystem);
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
            try {
                const res = await fetch(`/api/upload_art?system=${encodeURIComponent(currentSystem)}&filename=${encodeURIComponent(selectedGame)}`, {
                    method: "POST",
                    headers: {"Content-Type": file.type || "application/octet-stream"},
                    body: file
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message);
                    closeModal("modal-scrape");
                    selectSystem(currentSystem);
                } else {
                    showToast(data.error, true);
                }
            } catch (err) {
                showToast("Lỗi tải ảnh lên!", true);
            }
        }

        function openUploadRomModal() {
            const sel = document.getElementById("upload-target-sys");
            sel.innerHTML = allSystems.map(s => `
                <option value="${s.dir}" ${s.dir === currentSystem ? 'selected' : ''}>${s.name} (${s.dir})</option>
            `).join('');
            document.getElementById("rom-file-input").value = "";
            document.getElementById("upload-progress").style.display = "none";
            document.getElementById("modal-upload-rom").style.display = "flex";
        }

        async function submitUploadRom() {
            const targetSys = document.getElementById("upload-target-sys").value;
            const files = document.getElementById("rom-file-input").files;
            if (!targetSys || files.length === 0) {
                alert("Vui lòng chọn ít nhất một file ROM!");
                return;
            }
            const prog = document.getElementById("upload-progress");
            prog.style.display = "block";

            for (let i = 0; i < files.length; i++) {
                const f = files[i];
                prog.innerText = `Đang tải lên (${i+1}/${files.length}): ${f.name}...`;
                try {
                    await fetch(`/api/upload_rom?system=${encodeURIComponent(targetSys)}&filename=${encodeURIComponent(f.name)}`, {
                        method: "POST",
                        headers: {"Content-Type": "application/octet-stream"},
                        body: f
                    });
                } catch (e) {
                    showToast(`Lỗi tải lên ${f.name}`, true);
                }
            }
            showToast(`Đã tải lên ${files.length} ROM thành công!`);
            closeModal("modal-upload-rom");
            loadSystems(true);
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
