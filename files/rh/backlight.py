# -*- coding: utf-8 -*-
"""Screen backlight control for audio-only playback.

Thin wrapper over the standard sysfs backlight interface plus the framebuffer
blank node. Everything degrades gracefully: if no control is found the caller
just keeps the screen on and the audio still plays.
"""

import glob
import os

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
