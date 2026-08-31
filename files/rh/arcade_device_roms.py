# -*- coding: utf-8 -*-
"""Dung lai cac set ROM thiet bi ma core MAME doi phai co rieng.

Cac ban ROM arcade luu hanh deu dong goi theo quy uoc FBNeo: ROM dung chung cua
chip am thanh nam ngay trong zip cua game. MAME thi tach chung thanh set thiet
bi rieng va tim theo ten khac, nen game tai ve chet ngay o khau nap ROM:

    dl-1425.bin NOT FOUND (tried in qsound_hle mvsc)
    Fatal error: Required files are missing, the machine cannot be run.

Byte dung roi, chi sai ten va sai cho. Rut tu chinh file vua tai ra dat lai cho
dung - app khong kem theo ROM nao ca, va mot lan dat la moi game cung ho chip do
sau nay deu chay."""

import os
import zipfile

# ten trong bo ROM FBNeo -> (ten set thiet bi cua MAME, ten file MAME tim)
DEVICE_ROMS = {
    "qsound.bin": ("qsound_hle", "dl-1425.bin"),
}


def ensure_device_roms(rom_zip_path, rom_dir):
    """Sinh cac set ROM thiet bi con thieu ben canh game, tra ve ten file da tao.

    Khong bao gio ghi de set da co: ban nguoi dung tu chep vao co the la ban dump
    dung chuan hon ban di kem game."""
    created = []
    if not zipfile.is_zipfile(rom_zip_path):
        return created

    try:
        with zipfile.ZipFile(rom_zip_path) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                key = os.path.basename(member.filename).lower()
                if key not in DEVICE_ROMS:
                    continue

                set_name, mame_name = DEVICE_ROMS[key]
                out_path = os.path.join(rom_dir, f"{set_name}.zip")
                if os.path.exists(out_path):
                    continue

                # Doc het ROM truoc khi mo file dich: zip hong thi nem o day, luc
                # chua co gi nam trong thu muc ROM de phai don.
                data = zf.read(member)

                # Ghi ra ban tam roi doi ten: mat dien giua chung se de lai mot
                # zip cut, va lan chay sau thay file "da co" nen bo qua vinh vien.
                part_path = out_path + ".part"
                with zipfile.ZipFile(part_path, "w", zipfile.ZIP_DEFLATED) as out:
                    out.writestr(mame_name, data)
                os.replace(part_path, out_path)
                created.append(os.path.basename(out_path))
    except (OSError, zipfile.BadZipFile) as e:
        print(f"Device ROM extraction failed for {os.path.basename(rom_zip_path)}: {e}")

    return created
