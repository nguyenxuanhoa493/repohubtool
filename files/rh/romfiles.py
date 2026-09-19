# -*- coding: utf-8 -*-
"""Duoi file ROM va cach chon file chinh trong mot mo file vua bung ra.

Leaf module - chi dung stdlib. Truoc day phan nay nam trong rh/media.py, ma
module do import sdl2, nen khong test duoc va bo giai nen khong dung lai duoc."""

import os

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
    # Catalogue dat ten he PlayStation la "PS"; "PS1" giu lai cho ma cu goi ten do.
    "PS":  [".m3u", ".cue", ".chd", ".pbp"],
    "PS1": [".m3u", ".cue", ".chd", ".pbp"],
    "PSP": [".iso", ".cso"],
}
GENERIC_ROM_EXTS = [".m3u", ".cue", ".chd", ".iso", ".gba", ".sfc", ".smc", ".nes",
                    ".gb", ".gbc", ".gg", ".sms", ".md", ".gen", ".smd", ".nds",
                    ".z64", ".n64", ".v64", ".p8", ".pbp", ".cso", ".bin"]
SIDECAR_EXTS = (".nfo", ".diz", ".sfv", ".md5", ".sha1", ".dat", ".jpg", ".jpeg",
                ".gif", ".html", ".txt", ".url")


def referenced_by_sidecar(rom_path, companions):
    """True khi mot .cue/.m3u ben canh tro dung ten file cua *rom_path*.

    Doi ten mot .bin/.iso ma co .cue tro toi no thi cue tro vao khoang khong.
    Doi ten chinh cai .cue thi khong sao: cue tro ten .bin chu khong tu tro minh.
    """
    base = os.path.basename(rom_path).lower()
    for c in companions:
        if not c.lower().endswith((".cue", ".m3u")):
            continue
        try:
            with open(c, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().lower()
        except OSError:
            continue
        if base in text:
            return True
    return False

def safe_preferred_name(rom_path, companions, prefer_name):
    """Ten moi cho ROM chinh, None khi phai giu nguyen ten trong archive.

    Kho ghi ten goi tai ve (.zip) con thu muc Roms giu ten ROM da bung, nen doi
    ten giup lan sau tim lai duoc game. Chi doi khi viec do khong lam hong tham
    chieu cua .cue/.m3u."""
    if not prefer_name:
        return None
    if not companions:
        return prefer_name
    if referenced_by_sidecar(rom_path, companions):
        return None
    return prefer_name

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
