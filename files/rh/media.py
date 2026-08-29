# -*- coding: utf-8 -*-
"""Picking the real ROM out of an archive, and writing boxart as true PNG."""

import os
import subprocess

import sdl2
import sdl2.sdlimage as sdlimage

from .paths import TEMP_DOWNLOAD_DIR

# Giu lai ten cu o day: rh/downloader.py va cac cho khac van import tu media.
from .romfiles import (GENERIC_ROM_EXTS, ROM_EXT_PRIORITY,  # noqa: F401
                       SIDECAR_EXTS, pick_primary_rom)

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
