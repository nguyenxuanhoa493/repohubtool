# -*- coding: utf-8 -*-
"""Dua game NAOMI/Atomiswave ve he DC, noi duy nhat co core chay duoc chung.

Kho game gan nhan MAME cho ca hai bo mach nay, va ca hai deu chet o he MAME:
`mvsc2` thi bo ROM lech han ban MAME 0.259, con `mslug6` nap het 142 MB ROM roi
bi kernel giet vi may chi co 975 MB. Chay tren core flycast thi ca hai deu vao
game binh thuong, ma flycast o day chinh la he DC.

Nhan dien tu chinh noi dung zip chu khong tu danh sach ten: danh sach do quet
duoc chi la can duoi, chac chan con game khac lot luoi."""

import os
import shutil
import zipfile

# ROM cua BIOS di kem trong zip, la dau nhan dang chac chan nhat cho tung bo mach.
_MARKERS = (
    ("ATOMISWAVE", ("bios0.ic23", "bios1.ic23")),
    ("NAOMI", ("epr-21576", "naomi_boot.bin")),
)


def flycast_hardware(rom_path):
    """"ATOMISWAVE", "NAOMI", hoac None neu day khong phai phan cung cua flycast."""
    if not zipfile.is_zipfile(rom_path):
        return None
    try:
        with zipfile.ZipFile(rom_path) as zf:
            names = [os.path.basename(n).lower() for n in zf.namelist()]
    except (OSError, zipfile.BadZipFile):
        return None

    for hardware, markers in _MARKERS:
        for m in markers:
            if any(n.startswith(m) for n in names):
                return hardware
    return None


def _move_art(src_dir, dst_dir, base):
    """Chuyen anh bia neu co. Thieu anh khong phai la loi."""
    for ext in (".png", ".jpg"):
        src = os.path.join(src_dir, base + ext)
        if not os.path.exists(src):
            continue
        try:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, os.path.join(dst_dir, base + ext))
        except OSError as e:
            print(f"Cannot move artwork {base + ext}: {e}")
        return


def route_to_dc(rom_path, src_img_dir, dc_rom_dir, dc_img_dir):
    """Chuyen game sang he DC neu no la NAOMI/Atomiswave. Tra ve duong dan moi.

    None nghia la khong dong toi gi: game khong thuoc phan cung nay, hoac ben DC
    da co san mot ban - ban do co the la ban nguoi dung tu chep vao, ghi de len
    no la mat du lieu that."""
    if not flycast_hardware(rom_path):
        return None

    name = os.path.basename(rom_path)
    base = os.path.splitext(name)[0]
    dst = os.path.join(dc_rom_dir, name)
    if os.path.exists(dst):
        print(f"DC already has {name}, leaving the MAME copy alone")
        return None

    try:
        os.makedirs(dc_rom_dir, exist_ok=True)
        shutil.move(rom_path, dst)
    except OSError as e:
        print(f"Cannot move {name} into the DC system: {e}")
        return None

    # Anh chuyen sau ROM: ROM la thu bat buoc, anh chi la trang tri. Neu buoc
    # nay hong thi game van chay, chi la hien tran khong bia.
    _move_art(src_img_dir, dc_img_dir, base)
    _move_art(os.path.join(os.path.dirname(rom_path), ".media"),
              os.path.join(dc_rom_dir, ".media"), base)
    return dst
