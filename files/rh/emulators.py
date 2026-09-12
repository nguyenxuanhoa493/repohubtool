# -*- coding: utf-8 -*-
"""Tim dung gia lap va dung script cho mot he may. Leaf module - chi stdlib.

Truoc day cho nay ghep thang Emus/<he>/launch.sh, va sai hai lan tren chinh
ban the SD chinh hang TG4040:

- Ten thu muc gia lap khong nhat thiet trung ten he: Emus/PPSSPP phuc vu
  Roms/PSP, Emus/WSC phuc vu Roms/WS. Ghep thang thi ra mot duong dan khong
  ton tai, va game PSP bao "chua cau hinh gia lap".
- 5 he (CPS3, FBNEO, NEOGEO, PPSSPP, SS) dang chay bang mot script khac
  launch.sh. Chay launch.sh van len game, nhung bang core hoac che do khac cai
  nguoi dung da chon trong MainUI - PSP thanh GL normal thay vi Vulkan
  performance, cham hon han.

Ca hai deu nam trong Emus/<X>/config.json: "rompath" chi ve thu muc ROM, va
"launch" la script dang duoc chon. Doc lai file do moi lan mo game, nen doi
core trong MainUI thi RetroHub theo ngay ma khong can biet gi them."""

import json
import os

from .paths import SDCARD_PATH

EMUS_DIR = f"{SDCARD_PATH}/Emus"
DEFAULT_SCRIPT = "launch.sh"


ALIASES = {
    "NES": "FC", "FC": "NES",
    "SNES": "SFC", "SFC": "SNES",
    "MD": "GENESIS", "GENESIS": "MD", "MEGADRIVE": "MD", "SEGAMD": "MD",
    "PS": "PS1", "PS1": "PS", "PSX": "PS",
    "TG16": "PCE", "PCE": "TG16", "PCENGINE": "PCE",
    "WS": "WSC", "WSC": "WS",
    "MS": "SMS", "SMS": "MS",
    "PSP": "PPSSPP",
    "GBC": "GB",
}


def _config_of(emu_dir):
    """config.json cua mot thu muc gia lap, {} neu khong doc duoc.

    utf-8-sig chu khong phai utf-8: vai file tren the co BOM, va json.loads
    nghen ngay o ky tu dau."""
    try:
        with open(os.path.join(emu_dir, "config.json"), "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def _is_script_broken(emu_dir, script_path):
    """Kiem tra xem mot script co dang goi binary standalone bi loi / 0-byte hay khong."""
    if not script_path or not os.path.isfile(script_path):
        return True
    try:
        with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return True

    # Neu script co co che RetroArch fallback hoac chinh la script RetroArch thi khong broken
    if "RetroArch" in content or "ra64.trimui" in content or "_libretro.so" in content:
        return False

    # Quet xem script co thuc thi binary standalone nao <= 1024 bytes (0-byte) khong
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for token in line.split():
            clean = token.replace('"', '').replace("'", "")
            if clean.startswith("./") or clean.startswith("$SA_DIR/") or clean.startswith("$progdir/"):
                bin_name = os.path.basename(clean)
                candidates = [
                    os.path.join(emu_dir, bin_name),
                ]
                try:
                    for sub in os.listdir(emu_dir):
                        sub_path = os.path.join(emu_dir, sub)
                        if os.path.isdir(sub_path):
                            candidates.append(os.path.join(sub_path, bin_name))
                except OSError:
                    pass
                for c in candidates:
                    if os.path.isfile(c) and os.path.getsize(c) <= 1024:
                        return True
    return False


def _script_in(emu_dir, cfg):
    """Duong dan script mo game, hoac None neu thu muc nay khong chay duoc gi."""
    named = str(cfg.get("launch") or "").strip()

    # CrossMix-OS su dung default.sh lam script trung gian goi load_launcher.sh.
    # Trong load_launcher.sh chua cu phap bash (< <(...)) se bi loi cu phap neu chay bang /bin/sh.
    # Ta uu tien phan giai truc tiep script launcher con tu launchlist hoac launchers.cfg.
    launchlist = cfg.get("launchlist")
    if isinstance(launchlist, list) and launchlist:
        # 1. Kiem tra xem may da co file cau hinh launchers.cfg hay chua (do CrossMix tao ra)
        cfg_launcher_name = ""
        cfg_path = os.path.join(emu_dir, "launchers.cfg")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "launcher=" in line:
                            cfg_launcher_name = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass

        if cfg_launcher_name:
            for item in launchlist:
                if isinstance(item, dict) and item.get("name") == cfg_launcher_name:
                    sh_name = str(item.get("launch") or "").strip()
                    if sh_name and sh_name != "default.sh":
                        p = os.path.join(emu_dir, os.path.basename(sh_name))
                        if os.path.isfile(p) and not _is_script_broken(emu_dir, p):
                            return p

        # 2. Loc danh sach script hop le tu launchlist
        valid_scripts = []
        for item in launchlist:
            if isinstance(item, dict):
                sh_name = str(item.get("launch") or "").strip()
                if sh_name and sh_name != "default.sh":
                    p = os.path.join(emu_dir, os.path.basename(sh_name))
                    if os.path.isfile(p):
                        valid_scripts.append((str(item.get("name") or ""), sh_name, p))

        if valid_scripts:
            # Uu tien cac script khong bi broken (khong tro vao file binary 0-byte)
            working_scripts = [s for s in valid_scripts if not _is_script_broken(emu_dir, s[2])]
            pool = working_scripts if working_scripts else valid_scripts

            # Uu tien Vulkan neu co (vi du PPSSPP Vulkan tren TrimUI Smart Pro cho FPS tot nhat)
            for name, sh_name, p in pool:
                if "vulkan" in sh_name.lower() or "vulkan" in name.lower():
                    return p
            # Tiep theo la OpenGL
            for name, sh_name, p in pool:
                if "gl" in sh_name.lower() or "opengl" in name.lower():
                    return p
            # Mac dinh lay script dau tien hop le
            return pool[0][2]

    # Uu tien script khong bi broken
    for name in (named, DEFAULT_SCRIPT):
        if not name:
            continue
        p = os.path.join(emu_dir, os.path.basename(name))
        if os.path.isfile(p) and not _is_script_broken(emu_dir, p):
            return p

    # Fallback cuoi cung neu tat ca deu co nguy co loi: van tra ve script de he thu chay
    for name in (named, DEFAULT_SCRIPT):
        if not name:
            continue
        p = os.path.join(emu_dir, os.path.basename(name))
        if os.path.isfile(p):
            return p
    return None


def resolve(sys_code, emus_root=None):
    """(thu muc gia lap, script mo game) cho *sys_code*, hoac (None, None)."""
    root = emus_root or EMUS_DIR
    try:
        folders = sorted(d for d in os.listdir(root)
                         if os.path.isdir(os.path.join(root, d)) and not d.startswith("."))
    except OSError:
        return (None, None)

    # Tap hop cac ma he tuong duong (alias)
    sys_upper = sys_code.upper() if sys_code else ""
    target_names = {sys_code, sys_upper, sys_code.lower()} if sys_code else set()
    for k, v in ALIASES.items():
        if k.upper() == sys_upper:
            target_names.update([v, v.upper(), v.lower()])
        elif v.upper() == sys_upper:
            target_names.update([k, k.upper(), k.lower()])

    fallback = None
    for name in folders:
        emu_dir = os.path.join(root, name)
        cfg = _config_of(emu_dir)
        rompath = os.path.basename(str(cfg.get("rompath") or "").rstrip("/"))

        matches_name = name in target_names or name.upper() in target_names
        matches_rom = rompath in target_names or rompath.upper() in target_names
        if not (matches_name or matches_rom):
            continue

        script = _script_in(emu_dir, cfg)
        if not script:
            continue

        # Uu tien thu muc trung ten he goc hoac rompath trung he goc
        if name == sys_code or rompath == sys_code:
            return (emu_dir, script)
        if fallback is None:
            fallback = (emu_dir, script)

    if fallback:
        return fallback

    # Check NextUI platform Paks: Emus/tg5040/<sys_code>.pak / Emus/tg5050/<sys_code>.pak
    for plat in ("tg5040", "tg5050"):
        for code in target_names:
            pak_dir = os.path.join(root, plat, f"{code}.pak")
            pak_launch = os.path.join(pak_dir, "launch.sh")
            if os.path.isfile(pak_launch):
                return (pak_dir, pak_launch)

    return (None, None)
