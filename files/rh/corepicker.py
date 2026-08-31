# -*- coding: utf-8 -*-
"""Doi giai lap cho mot he may, bang chinh co che MainUI da co san.

MainUI doc khoa "launch" trong Emus/<he>/config.json de biet chay script nao, va
ve khoa "launchlist" thanh menu chon giai lap. Nha san xuat dung san co che nay
cho 14 he - nhung ARCADE, CPS1, CPS2, GG, MS, PS thi khong, du core thay the van
nam san tren the va tot hon han core dang chay (ARCADE/CPS1/CPS2 dang chay
fbalpha2012 doi 2012).

Do la ly do module nay ton tai: dung mot menu, vua bo sung launchlist cho nhung
he con thieu, vua doi core cho tat ca.

Script thay the duoc DAN XUAT tu chinh launch.sh cua he do - chi doi ten file
core. Viet lai tu dau la mat dac thu cua he mot cach im lang: GG goi
performance.sh, PS va GG tat netplay bang NET_PARAM=, MS co dong echo phan cach.
"""

import json
import os
import re
import shutil

from .paths import SDCARD_PATH

EMUS_DIR = f"{SDCARD_PATH}/Emus"
CORES_DIR = f"{SDCARD_PATH}/RetroArch/.retroarch/cores"

_CORE_RE = re.compile(r"[A-Za-z0-9_]+_libretro\.so")

# He -> (ten dat cho core dang chay, [(ten hien thi, core, ten script)])
# Chi liet ke nhung he thieu launchlist ma van co core thay the dang gia. Cac he
# da co launchlist san thi khong can mat gi o day - list_systems() van thay ho.
ALTERNATIVES = {
    "ARCADE": ("FBA2012", [("FBNEO", "fbneo", "launch_fbneo.sh"),
                           ("MAME", "mamearcade", "launch_mame.sh")]),
    "CPS1":   ("FBA2012 CPS1", [("FBNEO", "fbneo", "launch_fbneo.sh"),
                                ("MAME", "mamearcade", "launch_mame.sh")]),
    "CPS2":   ("FBA2012 CPS2", [("FBNEO", "fbneo", "launch_fbneo.sh"),
                                ("MAME", "mamearcade", "launch_mame.sh")]),
    "MAME":   ("MAME", [("FBNEO", "fbneo", "launch_fbneo.sh")]),
    "GG":     ("GenesisPlusGX", [("PicoDrive", "picodrive", "launch_picodrive.sh")]),
    "MS":     ("PicoDrive", [("GenesisPlusGX", "genesis_plus_gx", "launch_gpgx.sh")]),
    "PS":     ("PCSX ReARMed", [("SwanStation", "swanstation", "launch_swanstation.sh")]),
}


# Mot dong trong menu doi giai lap phai gop ca ten he lan ten giai lap dang chay.
# Badge ben phai rong co dinh 130px va ve chu can giua, nen ten dai tran ca hai
# dau - "PPSSPP Vulkan Performance Mode" la 30 ky tu. Vi vay ten giai lap di vao
# tieu de, con badge chi con nhan ngan. 46 la so ky tu app.py cho phep o mot dong
# co badge.
ROW_TITLE_MAX = 46


def row_title(row, limit=ROW_TITLE_MAX):
    """'<he>  ·  <giai lap dang chay>', da cat sao cho khong tran khoi dong."""
    text = "%s  ·  %s" % (row.get("label") or row.get("code") or "",
                          row.get("current") or "")
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _read_config(path):
    """utf-8-sig: vai config.json tren the co BOM va json.loads nghen ngay ky tu dau."""
    with open(path, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    return cfg if isinstance(cfg, dict) else {}


def derive_script(text, core):
    """Ban sao cua launch.sh, chi doi core. Dong bi chu thich khong dong toi."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith("#") and _CORE_RE.search(line):
            lines[i] = _CORE_RE.sub(core + "_libretro.so", line, count=1)
            return "\n".join(lines) + "\n"
    raise ValueError("launch.sh khong co dong nap core nao dang hoat dong")


def ensure_launchlist(code, emus_root=None, cores_dir=None):
    """Bo sung launchlist cho mot he neu no thieu. True neu vua them.

    Khong bao gio doi khoa "launch": he van chay dung core cu cho toi khi nguoi
    dung tu chon cai khac."""
    emus_root = emus_root or EMUS_DIR
    cores_dir = cores_dir or CORES_DIR
    if code not in ALTERNATIVES:
        return False

    d = os.path.join(emus_root, code)
    cfg_p = os.path.join(d, "config.json")
    base_p = os.path.join(d, "launch.sh")
    if not os.path.isfile(cfg_p) or not os.path.isfile(base_p):
        return False

    try:
        cfg = _read_config(cfg_p)
    except (OSError, ValueError):
        return False
    if cfg.get("launchlist"):
        return False

    cur_name, alts = ALTERNATIVES[code]
    base = open(base_p, encoding="utf-8", errors="ignore").read()
    entries = [{"name": cur_name, "launch": cfg.get("launch") or "launch.sh"}]
    for disp, core, script in alts:
        if not os.path.isfile(os.path.join(cores_dir, core + "_libretro.so")):
            continue
        try:
            out = os.path.join(d, script)
            with open(out, "w", encoding="utf-8") as f:
                f.write(derive_script(base, core))
            os.chmod(out, 0o755)
        except (OSError, ValueError) as e:
            print(f"Cannot build {script} for {code}: {e}")
            continue
        entries.append({"name": disp, "launch": script})

    if len(entries) < 2:
        return False

    try:
        shutil.copy2(cfg_p, cfg_p + ".bak")
        cfg["launchlist"] = entries
        with open(cfg_p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
            f.write("\n")
    except OSError as e:
        print(f"Cannot write launchlist for {code}: {e}")
        return False
    return True


def set_core(code, launch_name, emus_root=None):
    """Chon script mo game cho mot he. Chinh la thu MainUI ghi khi ban chon tay."""
    emus_root = emus_root or EMUS_DIR
    d = os.path.join(emus_root, code)
    cfg_p = os.path.join(d, "config.json")
    if not os.path.isfile(cfg_p) or not os.path.isfile(os.path.join(d, launch_name)):
        return False
    try:
        cfg = _read_config(cfg_p)
        cfg["launch"] = launch_name
        with open(cfg_p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
            f.write("\n")
    except (OSError, ValueError) as e:
        print(f"Cannot set core for {code}: {e}")
        return False
    return True


def list_systems(emus_root=None, cores_dir=None):
    """Cac he doi core duoc, kem lua chon va ten core dang chay.

    Gom ca he co launchlist san tu nha san xuat lan he vua duoc bo sung."""
    emus_root = emus_root or EMUS_DIR
    cores_dir = cores_dir or CORES_DIR
    rows = []
    try:
        names = sorted(os.listdir(emus_root))
    except OSError:
        return rows

    for code in names:
        d = os.path.join(emus_root, code)
        cfg_p = os.path.join(d, "config.json")
        if code.startswith("_") or not os.path.isfile(cfg_p):
            continue
        try:
            cfg = _read_config(cfg_p)
        except (OSError, ValueError):
            continue

        if not cfg.get("launchlist") and code in ALTERNATIVES:
            ensure_launchlist(code, emus_root=emus_root, cores_dir=cores_dir)
            try:
                cfg = _read_config(cfg_p)
            except (OSError, ValueError):
                continue

        opts = [e for e in (cfg.get("launchlist") or [])
                if e.get("launch") and os.path.isfile(os.path.join(d, e["launch"]))]
        if len(opts) < 2:
            continue

        cur = cfg.get("launch") or "launch.sh"
        cur_name = next((e["name"] for e in opts if e["launch"] == cur), cur)
        rows.append({"code": code, "label": cfg.get("label") or code,
                     "current": cur_name, "current_launch": cur, "options": opts})
    return rows
