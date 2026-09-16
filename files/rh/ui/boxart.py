# -*- coding: utf-8 -*-
"""Boxart resolution and rendering (proportional scaling & vector fallback avatars)."""

import os
import sdl2
from ..paths import SDCARD_PATH
from .. import state
from .primitives import fill_rect, draw_rect, draw_text

SYS_BADGE = {
    "GBA": ("GBA", (138, 43, 226)),
    "GBC": ("GBC", (200, 50, 160)),
    "GB": ("GB", (110, 135, 70)),
    "SFC": ("SNES", (115, 105, 190)),
    "SNES": ("SNES", (115, 105, 190)),
    "FC": ("NES", (220, 45, 45)),
    "NES": ("NES", (220, 45, 45)),
    "MD": ("GENESIS", (25, 105, 215)),
    "GENESIS": ("GENESIS", (25, 105, 215)),
    "GG": ("GAME GEAR", (35, 125, 195)),
    "MS": ("MASTER SYS", (45, 135, 205)),
    "NDS": ("NINTENDO DS", (0, 175, 230)),
    "PSP": ("PSP", (15, 85, 210)),
    "PS": ("PLAYSTATION", (0, 105, 215)),
    "PS1": ("PLAYSTATION", (0, 105, 215)),
    "N64": ("NINTENDO 64", (235, 90, 20)),
    "ARCADE": ("ARCADE", (255, 140, 0)),
    "MAME": ("MAME", (255, 140, 0)),
    "NEOGEO": ("NEO-GEO", (230, 55, 55)),
    "NGP": ("NEO GEO PKT", (185, 190, 200)),
    "CPS1": ("CPS-1", (225, 160, 20)),
    "CPS2": ("CPS-2", (40, 185, 115)),
    "CPS3": ("CPS-3", (180, 75, 220)),
    "PCE": ("PC ENGINE", (225, 105, 20)),
    "WS": ("WONDERSWAN", (55, 165, 195)),
    "WSC": ("WSWAN COLOR", (65, 185, 215)),
    "PICO8": ("PICO-8", (255, 35, 85)),
    "ATARI2600": ("ATARI 2600", (195, 65, 25)),
    "ATARI7800": ("ATARI 7800", (205, 75, 35)),
    "LYNX": ("ATARI LYNX", (195, 145, 15)),
    "DC": ("DREAMCAST", (240, 115, 20)),
    "SS": ("SEGA SATURN", (135, 145, 160)),
    "SEGACD": ("SEGA CD", (0, 136, 207)),
    "JAVA": ("JAVA", (205, 97, 85)),
}


def resolve_game_img_path(sys_code, filename):
    """Find local boxart path (.png or .jpg) on-demand."""
    if not filename:
        return None
    fn = os.path.basename(str(filename).replace("\\", "/"))
    base_name = os.path.splitext(fn)[0]
    img_dir = state.catalogs.get(sys_code, {}).get("img_dir", f"{SDCARD_PATH}/Imgs/{sys_code}")
    p1 = os.path.join(img_dir, f"{base_name}.png")
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(img_dir, f"{base_name}.jpg")
    if os.path.exists(p2):
        return p2
    return None


def draw_proportional_boxart(renderer, texture_fn, path, box_x, box_y, box_w, box_h):
    """Draw boxart texture keeping aspect ratio centered inside box."""
    tex, orig_w, orig_h = texture_fn(path)
    if not tex or orig_w <= 0 or orig_h <= 0:
        return False
    scale = min(box_w / float(orig_w), box_h / float(orig_h))
    dest_w = max(1, int(orig_w * scale))
    dest_h = max(1, int(orig_h * scale))
    dest_x = box_x + (box_w - dest_w) // 2
    dest_y = box_y + (box_h - dest_h) // 2
    dest_r = sdl2.SDL_Rect(int(dest_x), int(dest_y), int(dest_w), int(dest_h))
    sdl2.SDL_RenderCopy(renderer, tex, None, dest_r)
    return True


def draw_default_boxart_avatar(renderer, font_badge, box_x, box_y, box_w, box_h, sys_code="ROM", game_title="Game", text_texture_cache=None):
    """Placeholder tile for a game with no boxart."""
    if box_w <= 10 or box_h <= 10:
        return False

    s_tag, theme_col = SYS_BADGE.get(sys_code.upper(), (sys_code.upper(), (0, 200, 220)))
    tr_c, tg_c, tb_c = theme_col

    # Card body with a subtle bevel
    fill_rect(renderer, box_x, box_y, box_w, box_h, 16, 22, 34, 255)
    fill_rect(renderer, box_x + 1, box_y + 1, box_w - 2, 2, 65, 85, 125, 255)
    fill_rect(renderer, box_x + 1, box_y + box_h - 3, box_w - 2, 2, 8, 12, 18, 255)
    draw_rect(renderer, box_x, box_y, box_w, box_h, 40, 55, 85, 255, thickness=1)

    # Coloured header carrying the system tag
    header_h = max(24, int(box_h * 0.16))
    fill_rect(renderer, box_x + 2, box_y + 2, box_w - 4, header_h, tr_c, tg_c, tb_c, 255)
    fill_rect(renderer, box_x + 2, box_y + header_h, box_w - 4, 1, 255, 255, 255, 90)
    draw_text(renderer, s_tag, font_badge, box_x + box_w // 2, box_y + header_h // 2 + 1,
              255, 255, 255, center_x=True, center_y=True, text_texture_cache=text_texture_cache)

    # Small cartridge mark, centred in the remaining space
    body_y = box_y + header_h
    body_h = box_h - header_h
    cw = max(14, min(int(box_w * 0.34), int(body_h * 0.44)))
    ch = int(cw * 1.15)
    cx = box_x + (box_w - cw) // 2
    cy = body_y + (body_h - ch) // 2
    if cw >= 14 and ch >= 14:
        fill_rect(renderer, cx, cy, cw, ch, tr_c, tg_c, tb_c, 60)
        draw_rect(renderer, cx, cy, cw, ch, tr_c, tg_c, tb_c, 150, thickness=1)
        lx, ly = cx + max(2, cw // 6), cy + max(2, ch // 6)
        lw, lh = cw - 2 * max(2, cw // 6), int(ch * 0.42)
        if lw > 4 and lh > 4:
            fill_rect(renderer, lx, ly, lw, lh, tr_c, tg_c, tb_c, 120)
        pin_w = max(2, cw // 7)
        pin_y = cy + ch - max(3, ch // 8)
        for k in range(3):
            px = cx + max(2, cw // 6) + k * (pin_w * 2)
            if px + pin_w <= cx + cw - 2:
                fill_rect(renderer, px, pin_y, pin_w, max(2, ch // 10), tr_c, tg_c, tb_c, 170)
    return True
