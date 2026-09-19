# -*- coding: utf-8 -*-
"""Single source of truth for the build number.

The build script reads APP_VERSION from here to name the release, and the
updater compares it against the version in the published manifest, so the
constant must stay in sync with the git tag."""

# 2.35 da duoc phat hanh lai (ban refactor repo) duoi dung so phien ban do,
# nen may dang chay 2.35 khong thay co ban moi. 2.36 la ban dau tien lon hon no.
# 2.39: ban gom cac fix sau 2.38 - hang cho tai, OTA lap lai, Switch emulator
# core, Storage trang, tran panel phai o man chi tiet game, va tinh nang YouTube.
# 2.40: tu dong tai boxart & load truoc dung luong game; sua loi tim duong dan
# ROM sau khi bung; sua font dieu huong DPAD tranh loi glyph.
# 2.41: sua vong lap cap nhat OTA (buoc bo gia lap bi bo qua vi loi ten cuc bo
# trong modal, man hinh dung o 95%), them nut Huy khi dang tai, nut Bo qua co tac
# dung that, kho game khong con moi cap nhat sai tren may cai tu file zip, va
# gia lap J2ME doc dung che do ban phim nguoi dung chon.
# 2.42: giam nhiet/pin - chi ve khi co thay doi (4 khung/giay khi ranh), nhan dien dung
# man hinh tat tren TrimUI Brick (Allwinner disp), man hinh tat thi LED tat han, cache
# duong dan anh bia + tran cache (RAM anh bia 70MB -> 21MB), huy ket qua cu khi doi tab/video.
# 2.43: menu Retro Store (Grid 3x2), tich hop 1.400+ ROMs Google Drive va nang cap Webgame.
# 2.44: bao mat toan dien - loai bo token Telegram va API key AI khoi codebase, chuyen sang Cloudflare Worker Proxy.
# 2.45: sua loi cai gia lap Java J2ME tren the nho FAT32 ([Errno 5] Input/output error), co che giai nen da tang an toan va tiet kiem RAM.
# 2.46: bao mat & nang cap - proxy quet Google Drive qua Cloudflare Worker, ho tro dry-run va toi uu bo nap secrets.
APP_VERSION = "2.46"



def version_tuple(v=None):
    """Split a version string into ints so 1.10 sorts after 1.9.

    Anything unparsable sorts lowest, which makes a malformed manifest look
    older than the running build instead of triggering a bogus update."""
    try:
        return tuple(int(p) for p in str(v or APP_VERSION).strip().lstrip("v").split("."))
    except (TypeError, ValueError):
        return (0,)


def is_newer(remote, local=None):
    """True when *remote* is a strictly later version than *local*."""
    return version_tuple(remote) > version_tuple(local)
