# -*- coding: utf-8 -*-
"""Chuan bi cho mot lan ghi len the nho. Leaf module - chi dung stdlib.

The nho cua may choi la FAT hoac exFAT, khong co quyen POSIX that. Cai duy
nhat co the chan mot lan ghi o muc file la co read-only cua DOS: vfat va exfat
dich co do thanh mode 0444, nen ghi de len dung file dang mang co tra ve
EACCES trong khi ca phan con lai cua the van ghi binh thuong."""

import os


def human_bytes(n):
    """Doc duoc o moi co. Lam tron xuong MB thi mot the gan day bao "con 0 MB",
    khong noi len duoc gi ca."""
    if n >= 1024 ** 3:
        return "%.1f GB" % (n / (1024.0 ** 3))
    if n >= 1024 ** 2:
        return "%d MB" % (n // (1024 ** 2))
    return "%d KB" % (n // 1024)


def free_space(path):
    """Cho trong that su ghi duoc vao *path*.

    f_bavail chu khong phai f_bfree: he thong danh rieng mot phan cho root, va
    phan do khong phai cho ma nguoi dung ghi duoc vao."""
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


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
