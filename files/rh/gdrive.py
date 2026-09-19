# -*- coding: utf-8 -*-
"""Bo phan giai link va quan ly thu vien game Google Drive cong khai.

Module nay thuan Python stdlib (khong dung requests/BeautifulSoup), tuong thich
100% voi thiet bi TrimUI (Linux ARM). Ho tro boc tach Direct Link tu form xac
nhan virus cua Google Drive cho ca file lon (>100MB).
"""

import os
import re
import json
import time
import urllib.request
import urllib.parse
import ssl

from .paths import SDCARD_PATH, APP_DIR

# Bang anh xa phan mo rong file ROM sang ma he may (sys_code)
EXT_TO_SYS = {
    ".gba": "GBA",
    ".sfc": "SFC",
    ".smc": "SFC",
    ".fig": "SFC",
    ".nes": "FC",
    ".fc": "FC",
    ".md": "MD",
    ".gen": "MD",
    ".smd": "MD",
    ".gb": "GB",
    ".gbc": "GBC",
    ".nds": "NDS",
    ".cso": "PSP",
    ".pbp": "PS",
    ".chd": "PS",
    ".cue": "PS",
    ".jar": "JAVA",
    ".jad": "JAVA",
    ".p8": "PICO8",
    ".gg": "GG",
    ".sms": "MS",
    ".wsc": "WS",
    ".ws": "WS",
    ".pce": "PCE",
    ".n64": "N64",
    ".z64": "N64",
    ".v64": "N64",
    ".cdi": "DC",
    ".gdi": "DC",
}


def get_gdrive_library_path():
    """Tra ve duong dan luu tru danh sach game Drive tren the nho hoac data."""
    sd = os.environ.get("SDCARD_PATH") or SDCARD_PATH
    if sd and os.path.exists(sd):
        d = os.path.join(sd, "RetroHub")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "gdrive_library.json")
    d = os.path.join(APP_DIR, "data")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "gdrive_library.json")


def load_gdrive_library():
    """Doc danh sach game Drive da luu."""
    p = get_gdrive_library_path()
    if not os.path.isfile(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading gdrive_library: {e}")
        return []


def save_gdrive_library(items):
    """Ghi danh sach game Drive vao file json."""
    p = get_gdrive_library_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp_p = p + ".tmp"
        with open(tmp_p, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp_p, p)
        return True
    except Exception as e:
        print(f"Error saving gdrive_library: {e}")
        return False


def add_to_gdrive_library(item):
    """Them hoac cap nhat game vao thu vien Drive."""
    items = load_gdrive_library()
    fid = item.get("file_id") or ""
    item_id = item.get("id") or (f"gdrive_{fid}" if fid else f"gdrive_{int(time.time()*1000)}")
    item["id"] = item_id
    if "added_at" not in item:
        item["added_at"] = int(time.time())

    found = False
    for i, cur in enumerate(items):
        if cur.get("id") == item_id or (fid and cur.get("file_id") == fid):
            # Cap nhat thong tin
            cur.update(item)
            found = True
            break
    if not found:
        items.insert(0, item)

    save_gdrive_library(items)
    return item


def delete_from_gdrive_library(item_id):
    """Xoa mot game khoi thu vien Drive."""
    items = load_gdrive_library()
    new_items = [it for it in items if it.get("id") != item_id]
    if len(new_items) != len(items):
        save_gdrive_library(new_items)
        return True
    return False


def extract_file_id(url_or_id):
    """Trich xuat Google Drive File ID tu URL hoac chuoi ID truan."""
    if not url_or_id:
        return None
    s = str(url_or_id).strip()
    if not s:
        return None

    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"/folders/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, s)
        if m:
            return m.group(1)

    if "http" not in s and "/" not in s and re.match(r"^[a-zA-Z0-9_-]{15,}$", s):
        return s

    parts = s.split("/")
    if len(parts) > 5 and parts[5]:
        return parts[5].split("?")[0]

    return None


def guess_system_from_filename(filename):
    """Doan he may tu phan mo rong hoac ten file ROM."""
    if not filename:
        return "ALL"
    name_lower = filename.lower().strip()
    ext = os.path.splitext(name_lower)[1]

    if ext in EXT_TO_SYS:
        return EXT_TO_SYS[ext]

    if ext == ".iso":
        if "psp" in name_lower:
            return "PSP"
        return "PS"

    if ext in (".zip", ".7z", ".rar"):
        # File zip co the la Arcade, GBA hoac PS/PSP
        if any(w in name_lower for w in ("arcade", "fba", "neogeo", "cps", "mame")):
            return "ARCADE"
        if "gba" in name_lower:
            return "GBA"
        if "sfc" in name_lower or "snes" in name_lower:
            return "SFC"
        if "nes" in name_lower:
            return "FC"
        if "genesis" in name_lower or "megadrive" in name_lower:
            return "MD"
        return "ARCADE"

    return "ALL"


def _parse_cd_filename(cd):
    """Doc ten file tu header Content-Disposition."""
    if not cd:
        return ""
    m = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1).strip().strip('"').strip("'"))
    m = re.search(r'filename="([^"]+)"', cd, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"filename=([^;]+)", cd, re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"').strip("'")
    return ""


def _format_bytes(s):
    """Chuyen doi so bytes sang dinh dang KB/MB/GB de doc."""
    try:
        n = float(s)
    except (ValueError, TypeError):
        return ""
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{int(n)} {u}" if n == int(n) else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def parse_download_page_html(html, default_url):
    """Boc tach direct link va thong tin file tu trang HTML xac nhan cua Drive."""
    # 1. Boc tach ten file va size tu <span class="uc-name-size"><a>ten_file</a> (dung_luong)</span>
    filename = ""
    file_size = ""
    name_m = re.search(r'<span[^>]*class=["\']uc-name-size["\'][^>]*>(.*?)</span>', html, re.DOTALL | re.IGNORECASE)
    if name_m:
        span_content = name_m.group(1)
        a_m = re.search(r'<a[^>]*>(.*?)</a>', span_content, re.DOTALL | re.IGNORECASE)
        if a_m:
            filename = a_m.group(1).strip()
        sz_m = re.search(r'\(([^)]+)\)', span_content)
        if sz_m:
            file_size = sz_m.group(1).strip()

    file_ext = filename.split(".")[-1].lower() if "." in filename else ""

    # 2. Boc tach form download-form
    form_m = re.search(r'<form[^>]*id=["\']download-form["\'][^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)
    if not form_m:
        # Thu tim bat ky form nao co download
        form_m = re.search(r'<form[^>]*action=["\']([^"\']*download[^"\']*)["\'][^>]*>(.*?)</form>', html, re.DOTALL | re.IGNORECASE)

    if form_m:
        action_url = form_m.group(1).strip()
        form_inner = form_m.group(2)
        if not action_url or action_url.startswith("/"):
            action_url = "https://drive.usercontent.google.com" + action_url if action_url else "https://drive.usercontent.google.com/download"

        params = []
        input_matches = re.findall(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*>', form_inner, re.IGNORECASE)
        for input_tag in re.finditer(r'<input[^>]+>', form_inner, re.IGNORECASE):
            tag_text = input_tag.group(0)
            name_match = re.search(r'name=["\']([^"\']+)["\']', tag_text, re.IGNORECASE)
            val_match = re.search(r'value=["\']([^"\']*)["\']', tag_text, re.IGNORECASE)
            if name_match:
                k = name_match.group(1)
                v = val_match.group(1) if val_match else ""
                params.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}")

        if params:
            sep = "&" if "?" in action_url else "?"
            direct_link = f"{action_url}{sep}" + "&".join(params)
            return direct_link, filename, file_ext, file_size

    # Neu khong co form, fallback
    return default_url, filename, file_ext, file_size


def resolve_gdrive_info(url_or_id, timeout=15):
    """Phan tich link Google Drive va tra ve direct download link va metadata."""
    if url_or_id and "/folders/" in str(url_or_id):
        raise ValueError("Lien ket ban nhap la Thu muc (Folder). Vui long mo thu muc tren Google Drive va lay lien ket cua tung tep (file) ROM cong khai de them vao may.")

    file_id = extract_file_id(url_or_id)
    if not file_id:
        raise ValueError("Khong tim thay File ID hop le trong duong dan Google Drive")

    init_url = f"https://drive.google.com/uc?id={file_id}&export=download"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        ctx = ssl._create_unverified_context()
    except Exception:
        ctx = None

    req = urllib.request.Request(init_url, headers=headers)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

    try:
        resp = opener.open(req, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"Loi ket noi den Google Drive: {e}")

    content_type = (resp.headers.get("Content-Type") or "").lower()
    final_url = resp.geturl()

    # TH1: Google stream file luon (file nho hoac khong can xac nhan virus)
    if "text/html" not in content_type:
        cd = resp.headers.get("Content-Disposition", "")
        cl = resp.headers.get("Content-Length", "")
        resp.close()
        filename = _parse_cd_filename(cd) or f"gdrive_{file_id}.zip"
        file_ext = filename.split(".")[-1].lower() if "." in filename else ""
        file_size = _format_bytes(cl) if cl else "--"
        file_size_bytes = int(cl) if cl and cl.isdigit() else 0
        suggested_sys = guess_system_from_filename(filename)

        return {
            "ok": True,
            "file_id": file_id,
            "title": os.path.splitext(filename)[0],
            "filename": filename,
            "file_ext": file_ext,
            "file_size": file_size,
            "file_size_bytes": file_size_bytes,
            "direct_link": final_url,
            "suggested_sys": suggested_sys,
            "url": url_or_id,
        }

    # TH2: Phao cuu sinh - Google tra ve trang HTML (can confirm hoac canh bao virus)
    try:
        body = resp.read(256 * 1024).decode("utf-8", errors="replace")
    finally:
        resp.close()

    direct_link, filename, file_ext, file_size = parse_download_page_html(body, init_url)

    if not filename:
        # Kiem tra xem co phai loi quyen truy cap khong
        if "cần quyền truy cập" in body.lower() or "need permission" in body.lower() or "sign in" in body.lower():
            raise PermissionError("Tep Google Drive nay chua duoc bat chia se cong khai (Ai co duong lien ket deu co the xem)")
        filename = f"gdrive_{file_id}.zip"
        file_ext = "zip"

    suggested_sys = guess_system_from_filename(filename)

    return {
        "ok": True,
        "file_id": file_id,
        "title": os.path.splitext(filename)[0],
        "filename": filename,
        "file_ext": file_ext,
        "file_size": file_size or "--",
        "file_size_bytes": 0,
        "direct_link": direct_link,
        "suggested_sys": suggested_sys,
        "url": url_or_id,
    }
