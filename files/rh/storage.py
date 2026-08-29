# -*- coding: utf-8 -*-
"""Chuan bi cho mot lan ghi len the nho. Leaf module - chi dung stdlib.

The nho cua may choi la FAT hoac exFAT, khong co quyen POSIX that. Cai duy
nhat co the chan mot lan ghi o muc file la co read-only cua DOS: vfat va exfat
dich co do thanh mode 0444, nen ghi de len dung file dang mang co tra ve
EACCES trong khi ca phan con lai cua the van ghi binh thuong."""

import os


def unlock(path):
    """Go co read-only khoi *path* neu can. True khi duong ghi da thong.

    File chua ton tai cung tinh la thong: khong co gi chan ca. Tra ve False
    chi khi da co file that su khong ghi duoc va chmod khong cuu duoc no -
    luc do van de nam o ca the chu khong rieng file nay."""
    try:
        if not os.path.exists(path) or os.access(path, os.W_OK):
            return True
        os.chmod(path, os.stat(path).st_mode | 0o200)
    except OSError:
        return False
    return os.access(path, os.W_OK)
