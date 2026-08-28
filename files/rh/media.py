# -*- coding: utf-8 -*-
"""Picking the real ROM out of an archive, and writing boxart as true PNG."""

import os
import subprocess

import sdl2
import sdl2.sdlimage as sdlimage

from .paths import TEMP_DOWNLOAD_DIR

ROM_EXT_PRIORITY = {
    "GBA": [".gba"],
    "SFC": [".sfc", ".smc", ".fig"],
    "FC":  [".nes", ".fds", ".unf"],
    "MD":  [".md", ".gen", ".smd", ".bin"],
    "GB":  [".gb"],
    "GBC": [".gbc", ".gb"],
    "GG":  [".gg"],
    "MS":  [".sms"],
    "NDS": [".nds"],
    "N64": [".z64", ".n64", ".v64"],
    "PICO8": [".p8", ".png"],
    "PS1": [".m3u", ".cue", ".chd", ".pbp"],
    "PSP": [".iso", ".cso"],
}
GENERIC_ROM_EXTS = [".m3u", ".cue", ".chd", ".iso", ".gba", ".sfc", ".smc", ".nes",
                    ".gb", ".gbc", ".gg", ".sms", ".md", ".gen", ".smd", ".nds",
                    ".z64", ".n64", ".v64", ".p8", ".pbp", ".cso", ".bin"]
SIDECAR_EXTS = (".nfo", ".diz", ".sfv", ".md5", ".sha1", ".dat", ".jpg", ".jpeg", ".gif", ".html")

def pick_primary_rom(paths, sys_code):
    """Choose the file the emulator should actually be launched with.

    A zip holding a .cue/.bin pair, a multi-disc set, or bundled docs must not resolve
    to whichever entry happened to be last in the archive.
    """
    if not paths:
        return None
    prefs = ROM_EXT_PRIORITY.get(sys_code, [])

    def rank(p):
        ext = os.path.splitext(p)[1].lower()
        try:
            size = os.path.getsize(p)
        except Exception:
            size = 0
        if ext in prefs:
            return (0, prefs.index(ext), -size)
        if ext in GENERIC_ROM_EXTS:
            return (1, GENERIC_ROM_EXTS.index(ext), -size)
        if ext in SIDECAR_EXTS:
            return (3, 0, -size)
        return (2, 0, -size)

    return sorted(paths, key=rank)[0]

IMG_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"BM", ".bmp"),
)

def sniff_image_ext(raw):
    for magic, ext in IMG_MAGIC:
        if raw.startswith(magic):
            return ext
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return ".webp"
    return ""

def save_boxart_png(raw, target_png):
    """Write boxart as a genuine PNG.

    The catalog serves plenty of .jpeg and .gif URLs, and the stock TrimUI browser
    trusts the file extension rather than sniffing content - so writing raw JPEG bytes
    into a .png name leaves the boxart invisible outside RetroHub itself.
    """
    if not raw:
        return False
    if sniff_image_ext(raw) == ".png":
        with open(target_png, "wb") as f:
            f.write(raw)
        return True

    tmp_img = os.path.join(TEMP_DOWNLOAD_DIR, "boxart_src" + (sniff_image_ext(raw) or ".img"))
    try:
        os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)
        with open(tmp_img, "wb") as f:
            f.write(raw)

        # GraphicsMagick first, same binary the splash converter uses. [0] takes the
        # first frame so an animated GIF cannot expand into a numbered set of files.
        gm_bin = "/mnt/SDCARD/System/bin/gm"
        if os.path.exists(gm_bin):
            cmd = ('export LD_LIBRARY_PATH=/mnt/SDCARD/System/lib:$LD_LIBRARY_PATH; '
                   '"%s" convert "%s[0]" "%s"' % (gm_bin, tmp_img, target_png))
            if subprocess.call(cmd, shell=True) == 0 and os.path.exists(target_png) and os.path.getsize(target_png) > 100:
                return True

        surf = sdlimage.IMG_Load(tmp_img.encode('utf-8'))
        if surf:
            sdlimage.IMG_SavePNG(surf, target_png.encode('utf-8'))
            sdl2.SDL_FreeSurface(surf)
            if os.path.exists(target_png) and os.path.getsize(target_png) > 100:
                return True

        # Last resort: keep the raw bytes under the .png name. SDL_image sniffs content,
        # so RetroHub's own grid still renders it even if the stock browser will not.
        with open(target_png, "wb") as f:
            f.write(raw)
        return True
    finally:
        try:
            os.remove(tmp_img)
        except Exception:
            pass
