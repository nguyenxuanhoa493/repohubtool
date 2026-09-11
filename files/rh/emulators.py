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
                        if os.path.isfile(p):
                            return p

        # 2. Neu chua co launchers.cfg hoac script khong hop le, tu chon tu launchlist
        valid_scripts = []
        for item in launchlist:
            if isinstance(item, dict):
                sh_name = str(item.get("launch") or "").strip()
                if sh_name and sh_name != "default.sh":
                    p = os.path.join(emu_dir, os.path.basename(sh_name))
                    if os.path.isfile(p):
                        valid_scripts.append((str(item.get("name") or ""), sh_name, p))

        if valid_scripts:
            # Uu tien Vulkan neu co (vi dụ PPSSPP Vulkan tren TrimUI Smart Pro cho FPS tot nhat)
            for name, sh_name, p in valid_scripts:
                if "vulkan" in sh_name.lower() or "vulkan" in name.lower():
                    return p
            # Tiep theo la OpenGL
            for name, sh_name, p in valid_scripts:
                if "gl" in sh_name.lower() or "opengl" in name.lower():
                    return p
            # Mac dinh lay script dau tien hop le
            return valid_scripts[0][2]

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

    fallback = None
    for name in folders:
        emu_dir = os.path.join(root, name)
        cfg = _config_of(emu_dir)
        rompath = os.path.basename(str(cfg.get("rompath") or "").rstrip("/"))
        if name != sys_code and rompath != sys_code:
            continue
        script = _script_in(emu_dir, cfg)
        if not script:
            continue
        # Thu muc trung ten he la cai chinh; cai chi khop qua rompath chi duoc
        # dung khi khong co cai nao trung ten.
        if name == sys_code:
            return (emu_dir, script)
        if fallback is None:
            fallback = (emu_dir, script)
    if fallback:
        return fallback

    # Check NextUI platform Paks: Emus/tg5040/<sys_code>.pak / Emus/tg5050/<sys_code>.pak
    for plat in ("tg5040", "tg5050"):
        pak_dir = os.path.join(root, plat, f"{sys_code}.pak")
        pak_launch = os.path.join(pak_dir, "launch.sh")
        if os.path.isfile(pak_launch):
            return (pak_dir, pak_launch)

    return (None, None)
