# -*- coding: utf-8 -*-
"""Doc mot exception tai game ra dung nguyen nhan. Leaf module - chi dung stdlib.

Truoc day moi that bai deu ket thuc bang cung mot cau "TAI THAT BAI", nen mat
Wi-Fi, nguon chan hotlink va the nho day deu trong y het nhau. Nguoi dung khong
biet phai sua gi. Tra ve key cua rh.i18n de nguoi goi tu dich."""

import errno
import socket
import urllib.error

# Khong con mang thi thu lai la vo ich: nguoi goi dung vong retry khi thay key nay.
NO_NET = "dl_err_no_net"
# The nho khong nhan lenh ghi. Doi mirror khac la vo ich y het NO_NET, nen
# nguoi goi cung dung vong retry khi thay key nay.
READONLY = "dl_err_readonly"
GENERIC = "fail_msg"

# Loi "khong co duong ra": phan biet voi mot server that su tu choi.
_OFFLINE_ERRNOS = (errno.ENETUNREACH, errno.EHOSTUNREACH)

# EROFS khi kernel biet mount la chi doc; EACCES/EPERM khi chinh tang FAT hay
# exfat-fuse tu choi, la truong hop hay gap hon tren may that.
_READONLY_ERRNOS = (errno.EACCES, errno.EPERM, errno.EROFS)

_HTTP_KEYS = {
    401: "dl_err_blocked",
    403: "dl_err_blocked",
    451: "dl_err_blocked",
    404: "dl_err_gone",
    410: "dl_err_gone",
    429: "dl_err_busy",
    503: "dl_err_busy",
}


# Toan bo tu vung ma classify_error co the tra ve. Test i18n duyet tap nay,
# nen them mot ly do moi ma quen dich se hong test chu khong hong tren may.
ALL_KEYS = frozenset(
    [NO_NET, READONLY, GENERIC, "dl_err_timeout", "dl_err_disk_full",
     "dl_err_truncated"]
    + list(_HTTP_KEYS.values())
)


def classify_error(ex):
    """Key i18n mo ta vi sao lan tai nay hong, hoac GENERIC neu khong doan duoc."""
    if ex is None:
        return GENERIC

    # HTTPError truoc: no vua la URLError vua la OSError, nen mo goi hay so errno
    # deu se doc nham no thanh mot thu khac.
    if isinstance(ex, urllib.error.HTTPError):
        return _HTTP_KEYS.get(ex.code, GENERIC)

    # URLError chi la lop boc; nguyen nhan that nam trong .reason.
    if isinstance(ex, urllib.error.URLError) and isinstance(ex.reason, BaseException):
        return classify_error(ex.reason)

    # gaierror = phan giai ten that bai, dau hieu ro nhat cua may chua vao mang.
    if isinstance(ex, socket.gaierror):
        return NO_NET

    # Phai dung trong socket.timeout la TimeoutError, va TimeoutError la OSError,
    # nen doan nay phai chan trong so errno o duoi.
    if isinstance(ex, (socket.timeout, TimeoutError)):
        return "dl_err_timeout"

    if isinstance(ex, OSError):
        if ex.errno in _OFFLINE_ERRNOS:
            return NO_NET
        if ex.errno == errno.ENOSPC:
            return "dl_err_disk_full"
        # The exFAT bi co dirty (rut khoi may tinh khong an toan) duoc mount
        # lai o che do chi doc, va file DOS mang co read-only cung ra EACCES.
        # Ca hai deu la "the khong cho ghi", khong phai loi mang hay loi nguon.
        if ex.errno in _READONLY_ERRNOS:
            return READONLY
        return GENERIC

    if isinstance(ex, ValueError):
        msg = str(ex).lower()
        # Trang chan hotlink tra HTML kem status 200; downloader doi no thanh ValueError.
        if "returned html" in msg:
            return "dl_err_blocked"
        if "truncated" in msg or "incomplete" in msg:
            return "dl_err_truncated"

    return GENERIC


def wifi_offline(get_ip):
    """May chua co IP Wi-Fi hay chua.

    Doc IP thay vi goi thu mot request: re hon, va tra loi ngay thay vi doi
    het timeout. Khong doc duoc thi coi nhu con mang - tha thu tai roi bao loi
    that con hon chan tai tren mot may ma cach do IP nay khong ap dung."""
    try:
        return not (get_ip() or "").strip()
    except Exception:
        return False
