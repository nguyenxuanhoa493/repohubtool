# -*- coding: utf-8 -*-
"""Screen backlight control for audio-only playback.

Thin wrapper over the standard sysfs backlight interface plus the framebuffer
blank node. Everything degrades gracefully: if no control is found the caller
just keeps the screen on and the audio still plays.
"""

import glob
import os
import re

_BACKLIGHT_GLOB = "/sys/class/backlight/*/brightness"
_BLANK_PATHS = (
    "/sys/class/graphics/fb0/blank",
    "/sys/class/graphics/fb1/blank",
)


def _brightness_paths():
    return sorted(glob.glob(_BACKLIGHT_GLOB))


def _blank_paths():
    return [p for p in _BLANK_PATHS if os.path.exists(p)]


def available() -> bool:
    """True when at least one backlight/blank node can be written."""
    return bool(_brightness_paths() or _blank_paths())


def _read(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _write(path, value) -> bool:
    try:
        with open(path, "w") as f:
            f.write(str(value))
        return True
    except Exception:
        return False


_BLANK_GLOB = "sys/class/graphics/fb*/blank"
_FB_STATE_GLOB = "sys/class/graphics/fb*/state"
_BL_POWER_GLOB = "sys/class/backlight/*/bl_power"
_BRIGHTNESS_GLOB = "sys/class/backlight/*/brightness"
# TrimUI Brick (Allwinner sun50iw10, do tren may 192.168.1.12) khong co
# /sys/class/backlight, fb0/blank rong, va trang thai man hinh nam trong
# /sys/class/disp/disp/attr/sys: chu "unblank"/"blank" va "backlight( 72)".
_DISP_SYS_GLOB = "sys/class/disp/disp/attr/sys"
_DISP_BL_RE = re.compile(r"backlight\(\s*(\d+)\)")

def screen_is_off(root="/"):
    """True khi firmware da tat/blank man hinh.

    Phai hoi du cac node vi khong biet firmware nao dung node nao: co may TrimUI
    blank bang /sys/class/graphics/fb0/blank, co may bang fb1/blank hoac
    /sys/class/backlight/*/bl_power, va co may (Brick/Allwinner - do that tren
    may 192.168.1.12) khong co /sys/class/backlight nao ca: tin hieu nam o
    fb*/state va /sys/class/disp/disp/attr/sys ("unblank"/"blank" +
    "backlight( N)"). Chi hoi mot node thi app tuong nham man hinh con sang va
    tiep tuc ve 25-28 khung/giay - dung luc nguoi dung da tat may (nong may,
    ton pin).

    brightness = 0 chi bi coi la tat khi max_brightness > 0, tuc node do sang
    that su hoat dong - do dung la gia tri ma screen_off() ghi vao. `root` de
    test duoc tren cay sysfs gia (_src/selftest_perf.py T2)."""
    for pattern in (_BLANK_GLOB, _FB_STATE_GLOB, _BL_POWER_GLOB):
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            value = _read(path)
            if value and value != "0":
                return True
    for path in sorted(glob.glob(os.path.join(root, _DISP_SYS_GLOB))):
        text = _read(path) or ""
        # "unblank" chua chuoi con "blank", nen phai kiem no truoc.
        if "unblank" not in text and "blank" in text:
            return True
        match = _DISP_BL_RE.search(text)
        if match and int(match.group(1)) == 0:
            return True
    for path in sorted(glob.glob(os.path.join(root, _BRIGHTNESS_GLOB))):
        if _read(path) != "0":
            continue
        max_value = _read(os.path.join(os.path.dirname(path), "max_brightness"))
        if max_value and max_value.isdigit() and int(max_value) > 0:
            return True
    return False

def screen_off():
    """Turn the screen off. Returns a token to pass to screen_on(), or None."""
    saved = []
    for p in _brightness_paths():
        cur = _read(p)
        if cur is None:
            continue
        if _write(p, 0):
            saved.append((p, cur))
    for p in _blank_paths():
        cur = _read(p)
        if cur is None:
            continue
        if _write(p, 1):
            saved.append((p, cur))
    return saved or None


def screen_on(saved):
    """Restore a state returned by screen_off()."""
    if not saved:
        return
    for path, value in saved:
        _write(path, value)
