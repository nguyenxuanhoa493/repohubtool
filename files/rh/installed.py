# -*- coding: utf-8 -*-
"""Tim ban cai that tren the, va cac file di kem cua no.

Kho game ghi `filename` la ten goi tai ve (thuong la .zip/.7z), con thu muc
Roms giu ten ROM da bung ra (.gba, .cue...). Vi vay moi phep so sanh "game nay
da cai chua" phai qua base name, khong phai qua ten file. Module nay la module
la (chi stdlib, khong SDL2) nen test duoc tren may build.

Ket qua duoc cache ngan (CACHE_TTL) vi mot lan mo modal chi can mot lan quet,
nhung danh sach store thi goi lien tuc; cache bi xoa ngay sau khi tai hoac xoa
game de khong hien trang thai cu."""

import os
import time

from .paths import IMGS_DIR, resolve_rom_dir
from .romfiles import GENERIC_ROM_EXTS, ROM_EXT_PRIORITY

CACHE_TTL = 3.0

# Cac duoi duoc coi la ROM khi quet thu muc, de mot file .png boxart nam lan
# trong Roms/ khong bi tinh la game.
KNOWN_ROMS = frozenset(GENERIC_ROM_EXTS) | frozenset(
    ext for exts in ROM_EXT_PRIORITY.values() for ext in exts) | frozenset(
    (".zip", ".7z", ".rar", ".jar", ".jad", ".cdi", ".gdi", ".ngp", ".ngc",
     ".pce", ".wsc", ".ws", ".a26", ".a78", ".lnx", ".fig", ".smd"))

_cache = {}
# Cache rieng cho danh sach thu muc: xem _scan_dirs().
_dir_cache = {}

def invalidate():
    """Quen moi thu da quet. Goi sau khi tai xong hoac xoa game."""
    _cache.clear()
    _dir_cache.clear()

def base_key(sys_code, filename):
    """Khoa so sanh cua mot ten file: bo duong dan, bo duoi, bo duoi .p8."""
    fn = os.path.basename(str(filename or "").replace("\\", "/")).strip()
    base = os.path.splitext(fn)[0]
    if base.lower().endswith(".p8"):
        base = os.path.splitext(base)[0]
    return base.strip().lower()

def _img_dir(sys_code):
    from . import state
    return state.catalogs.get(sys_code, {}).get("img_dir", os.path.join(IMGS_DIR, sys_code))

def _scan_dirs(sys_code):
    """Thu muc he may, va mot tang con (J2ME chia theo do phan giai man hinh).

    Ket qua duoc cache ngan (CACHE_TTL) vi ham nay nam tren duong render: man
    Library goi image_path() cho tung o anh bia moi khung hinh, va mot lan
    image_path() la mot lan listdir + isdir toan bo file trong Roms/<he> -
    do tren may that la 5.3 ms/lan voi thu muc 300 file (xem
    _src/selftest_perf.py). invalidate() xoa ca cache nay, nen sau khi tai/xoa
    game thi danh sach thu muc duoc quet lai ngay."""
    now = time.time()
    hit = _dir_cache.get(sys_code)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]

    rom_dir = resolve_rom_dir(sys_code)
    dirs = [rom_dir]
    try:
        for sub in sorted(os.listdir(rom_dir)):
            p = os.path.join(rom_dir, sub)
            if os.path.isdir(p) and not sub.startswith("."):
                dirs.append(p)
    except OSError:
        pass
    _dir_cache[sys_code] = (now, (rom_dir, dirs))
    return rom_dir, dirs

def entries(sys_code):
    """[{sys_code, filename, path, base, size}] cua mot he may, co cache ngan."""
    now = time.time()
    hit = _cache.get(sys_code)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]

    out = []
    for d in _scan_dirs(sys_code)[1]:
        try:
            with os.scandir(d) as it:
                for e in it:
                    if e.name.startswith("."):
                        continue
                    try:
                        if not e.is_file():
                            continue
                        size = e.stat().st_size
                    except OSError:
                        continue
                    ext = os.path.splitext(e.name)[1].lower()
                    if ext not in KNOWN_ROMS and not (sys_code == "PICO8" and ext == ".png"):
                        continue
                    out.append({
                        "sys_code": sys_code,
                        "filename": e.name,
                        "path": e.path,
                        "base": base_key(sys_code, e.name),
                        "size": size,
                    })
        except OSError:
            continue
    _cache[sys_code] = (now, out)
    return out

def find(sys_code, filename):
    """Ban cai khop voi mot dong catalogue, hoac None.

    Uu tien ten file dung y nguyen (truong hop goi tai ve duoc giu nguyen ten),
    sau do moi den base name (truong hop da bung ra ROM)."""
    if not sys_code or not filename:
        return None
    want_full = os.path.basename(str(filename).replace("\\", "/")).strip().lower()
    want_base = base_key(sys_code, filename)
    found = entries(sys_code)
    for e in found:
        if e["filename"].lower() == want_full:
            return e
    if want_base:
        for e in found:
            if e["base"] == want_base:
                return e
    return None

def image_path(sys_code, filename):
    """Duong dan boxart cua game, thu ca ten catalogue lan ten ban cai that."""
    if not sys_code or not filename:
        return None
    entry = find(sys_code, filename)
    bases = [base_key(sys_code, filename)]
    if entry and entry["base"] not in bases:
        bases.append(entry["base"])
    img_dir = _img_dir(sys_code)
    rom_dir, dirs = _scan_dirs(sys_code)
    for base in bases:
        if not base:
            continue
        for suffix in (".png", ".jpg"):
            for d in [img_dir] + [os.path.join(x, ".media") for x in dirs]:
                cand = os.path.join(d, base + suffix)
                if os.path.exists(cand):
                    return cand
    return None

def companions(rom_path):
    """Cac file di kem cua cung mot game: cung thu muc, cung base, khac duoi.

    Chi lay dung base de khong xoa nham dia khac hay ban hack cung ten.
    Tra ve danh sach duong dan, khong gom chinh *rom_path*."""
    if not rom_path:
        return []
    d = os.path.dirname(rom_path)
    base = base_key(None, os.path.basename(rom_path))
    out = []
    try:
        with os.scandir(d) as it:
            for e in it:
                if e.name.startswith(".") or e.path == rom_path:
                    continue
                try:
                    if not e.is_file():
                        continue
                except OSError:
                    continue
                if base_key(None, e.name) == base:
                    out.append(e.path)
    except OSError:
        return []
    return out
