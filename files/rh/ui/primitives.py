# -*- coding: utf-8 -*-
"""Low-level SDL2 drawing primitives and vector icon rendering."""

import time
import ctypes
import sdl2
import sdl2.sdlttf as sdlttf
from ..i18n import tr

_text_w_cache = {}


def measure_text(text, font, cache=_text_w_cache):
    """Measure the pixel width of a single line of text."""
    if text is None:
        return 0
    # Auto-detect if font and text were passed in reversed order
    if not isinstance(text, str) and isinstance(font, str):
        text, font = font, text
    else:
        text = str(text)
    if not font:
        return len(text) * 10
    key = (text, id(font))
    cached = cache.get(key) if cache is not None else None
    if cached is not None:
        return cached
    w = ctypes.c_int(0)
    h = ctypes.c_int(0)
    sdlttf.TTF_SizeUTF8(font, text.encode("utf-8"), ctypes.byref(w), ctypes.byref(h))
    if cache is not None:
        if len(cache) > 600:
            cache.clear()
        cache[key] = w.value
    return w.value


def truncate_text(text, font, max_w, cache=_text_w_cache):
    """Safely truncate text with ellipsis (...) if it exceeds max_w pixels."""
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if max_w is None or max_w <= 0:
        return text
    if measure_text(text, font, cache) <= max_w:
        return text
    cur = text
    while cur and measure_text(cur + "...", font, cache) > max_w:
        cur = cur[:-1]
    return cur.rstrip() + "..." if cur else "..."


def fill_rect(renderer, x, y, w, h, r, g, b, a=255):
    rect = sdl2.SDL_Rect(int(x), int(y), int(w), int(h))
    sdl2.SDL_SetRenderDrawColor(renderer, r, g, b, a)
    sdl2.SDL_RenderFillRect(renderer, rect)


def draw_rect(renderer, x, y, w, h, r, g, b, a=255, thickness=1):
    sdl2.SDL_SetRenderDrawColor(renderer, r, g, b, a)
    for i in range(thickness):
        rect = sdl2.SDL_Rect(int(x + i), int(y + i), int(w - 2 * i), int(h - 2 * i))
        sdl2.SDL_RenderDrawRect(renderer, rect)


def draw_line(renderer, x1, y1, x2, y2, r, g, b, a=255, thickness=1):
    sdl2.SDL_SetRenderDrawColor(renderer, r, g, b, a)
    if thickness <= 1:
        sdl2.SDL_RenderDrawLine(renderer, int(x1), int(y1), int(x2), int(y2))
    else:
        for i in range(-thickness // 2, thickness // 2 + 1):
            sdl2.SDL_RenderDrawLine(renderer, int(x1), int(y1 + i), int(x2), int(y2 + i))
            sdl2.SDL_RenderDrawLine(renderer, int(x1 + i), int(y1), int(x2 + i), int(y2))


def draw_text(renderer, text, font, x, y, r, g, b, a=255, center_x=False, center_y=False, text_texture_cache=None, max_cache=280, right_align=False, max_w=None):
    if text is None or text == "":
        return 0, 0
    if not isinstance(text, str):
        text = str(text)
    if max_w is not None and max_w > 0:
        text = truncate_text(text, font, max_w)
    if not font or not renderer:
        return 0, 0

    now_ts = time.time()
    key = (text, id(font), r, g, b, a)
    cached = text_texture_cache.get(key) if text_texture_cache is not None else None
    if cached:
        tex, w, h = cached[0], cached[1], cached[2]
        cached[3] = now_ts
    else:
        color = sdl2.SDL_Color(r, g, b, a)
        surf = sdlttf.TTF_RenderUTF8_Blended(font, text.encode("utf-8"), color)
        if not surf:
            return 0, 0
        w = surf.contents.w
        h = surf.contents.h
        tex = sdl2.SDL_CreateTextureFromSurface(renderer, surf)
        sdl2.SDL_FreeSurface(surf)
        if not tex:
            return 0, 0

        if text_texture_cache is not None:
            if len(text_texture_cache) >= max_cache:
                old_keys = sorted(text_texture_cache.keys(), key=lambda k: text_texture_cache[k][3])[:50]
                for ok in old_keys:
                    item = text_texture_cache.pop(ok, None)
                    if item and item[0]:
                        sdl2.SDL_DestroyTexture(item[0])
            text_texture_cache[key] = [tex, w, h, now_ts]

    if right_align:
        dest_x = x - w
    elif center_x:
        dest_x = x - (w // 2)
    else:
        dest_x = x

    dest_y = y - (h // 2) if center_y else y
    dest = sdl2.SDL_Rect(int(dest_x), int(dest_y), int(w), int(h))
    sdl2.SDL_RenderCopy(renderer, tex, None, dest)
    if text_texture_cache is None:
        sdl2.SDL_DestroyTexture(tex)
    return w, h


def draw_text_fit(renderer, text, font, x, y, max_w, r, g, b, a=255, center_x=False, center_y=False, text_texture_cache=None, max_cache=280, right_align=False):
    """Draw text strictly constrained within max_w width, auto-truncating with ellipsis if needed."""
    return draw_text(renderer, text, font, x, y, r, g, b, a=a, center_x=center_x, center_y=center_y, text_texture_cache=text_texture_cache, max_cache=max_cache, right_align=right_align, max_w=max_w)



def wrap_text_to_width(text, font, max_w, max_lines=2, cache=_text_w_cache):
    """Break text into at most max_lines that each fit within max_w pixels."""
    if text is None or text == "":
        return [""]
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    if not text or measure_text(text, font, cache) <= max_w:
        return [text]

    words = text.split()
    lines = []
    cur = ""
    for i, word in enumerate(words):
        cand = (cur + " " + word).strip()
        if cur and measure_text(cand, font, cache) > max_w:
            lines.append(cur)
            if len(lines) == max_lines - 1:
                cur = " ".join(words[i:])
                break
            cur = word
        else:
            cur = cand

    if measure_text(cur, font, cache) > max_w:
        while cur and measure_text(cur + "...", font, cache) > max_w:
            cur = cur[:-1]
        cur = cur.rstrip() + "..."
    lines.append(cur)
    return lines[:max_lines]


def draw_action_vector_icon(renderer, act_id, cx, cy, sz=70, r=255, g=255, b=255, a=255):
    """Vẽ biểu tượng vector độ nét cao (kích thước siêu lớn, sắc nét) cho các thẻ hành động."""
    if act_id == "PLAY":
        hw = 24
        for i in range(hw * 2):
            h_span = int((hw * 2 - i) * 0.62)
            fill_rect(renderer, cx - hw + 6 + i, cy - h_span, 1, h_span * 2 + 1, r, g, b, a)

    elif act_id == "PLAY_CHEAT":
        for i in range(30):
            h_span = int((30 - i) * 0.58)
            fill_rect(renderer, cx - 28 + i, cy - h_span, 1, h_span * 2 + 1, r, g, b, a)
        draw_line(renderer, cx + 14, cy - 25, cx + 4, cy - 3, 255, 215, 0, a, thickness=5)
        draw_line(renderer, cx + 4, cy - 3, cx + 18, cy - 3, 255, 215, 0, a, thickness=5)
        draw_line(renderer, cx + 18, cy - 3, cx + 6, cy + 25, 255, 215, 0, a, thickness=5)
        fill_rect(renderer, cx + 5, cy - 6, 11, 7, 255, 215, 0, a)

    elif act_id == "GET_CHEAT":
        draw_line(renderer, cx + 9, cy - 28, cx - 11, cy, r, g, b, a, thickness=6)
        draw_line(renderer, cx - 11, cy, cx + 11, cy, r, g, b, a, thickness=6)
        draw_line(renderer, cx + 11, cy, cx - 9, cy + 28, r, g, b, a, thickness=6)
        fill_rect(renderer, cx - 5, cy - 5, 11, 10, r, g, b, a)
        fill_rect(renderer, cx - 2, cy - 12, 6, 24, r, g, b, a)

    elif act_id == "GET_BOXART":
        draw_rect(renderer, cx - 28, cy - 22, 56, 44, r, g, b, a, thickness=4)
        fill_rect(renderer, cx + 8, cy - 15, 11, 11, r, g, b, a)
        draw_line(renderer, cx - 24, cy + 15, cx - 8, cy - 5, r, g, b, a, thickness=4)
        draw_line(renderer, cx - 8, cy - 5, cx + 6, cy + 15, r, g, b, a, thickness=4)
        draw_line(renderer, cx + 3, cy + 15, cx + 16, cy + 3, r, g, b, a, thickness=4)
        draw_line(renderer, cx + 16, cy + 3, cx + 24, cy + 15, r, g, b, a, thickness=4)

    elif act_id == "NETPLAY":
        draw_rect(renderer, cx - 28, cy - 18, 56, 36, r, g, b, a, thickness=4)
        fill_rect(renderer, cx - 24, cy - 24, 14, 6, r, g, b, a)
        fill_rect(renderer, cx + 10, cy - 24, 14, 6, r, g, b, a)
        fill_rect(renderer, cx - 22, cy - 3, 14, 6, r, g, b, a)
        fill_rect(renderer, cx - 18, cy - 7, 6, 14, r, g, b, a)
        fill_rect(renderer, cx + 14, cy - 9, 6, 6, r, g, b, a)
        fill_rect(renderer, cx + 8, cy - 3, 6, 6, r, g, b, a)
        fill_rect(renderer, cx + 20, cy - 3, 6, 6, r, g, b, a)
        fill_rect(renderer, cx + 14, cy + 3, 6, 6, r, g, b, a)

    elif act_id == "DEL":
        fill_rect(renderer, cx - 7, cy - 27, 14, 5, r, g, b, a)
        draw_line(renderer, cx - 25, cy - 21, cx + 25, cy - 21, r, g, b, a, thickness=4)
        draw_rect(renderer, cx - 19, cy - 15, 38, 40, r, g, b, a, thickness=4)
        fill_rect(renderer, cx - 11, cy - 7, 4, 24, r, g, b, a)
        fill_rect(renderer, cx - 2, cy - 7, 4, 24, r, g, b, a)
        fill_rect(renderer, cx + 7, cy - 7, 4, 24, r, g, b, a)

    elif act_id == "RES":
        draw_rect(renderer, cx - 28, cy - 23, 56, 36, r, g, b, a, thickness=4)
        fill_rect(renderer, cx - 4, cy + 13, 8, 9, r, g, b, a)
        fill_rect(renderer, cx - 14, cy + 22, 28, 5, r, g, b, a)
        draw_line(renderer, cx - 18, cy + 1, cx + 18, cy + 1, r, g, b, a, thickness=3)

    elif act_id == "REGET":
        draw_line(renderer, cx, cy - 25, cx, cy + 8, r, g, b, a, thickness=5)
        draw_line(renderer, cx - 14, cy - 3, cx, cy + 11, r, g, b, a, thickness=5)
        draw_line(renderer, cx + 14, cy - 3, cx, cy + 11, r, g, b, a, thickness=5)
        draw_line(renderer, cx - 22, cy + 22, cx + 22, cy + 22, r, g, b, a, thickness=5)
        fill_rect(renderer, cx - 22, cy + 11, 5, 11, r, g, b, a)
        fill_rect(renderer, cx + 17, cy + 11, 5, 11, r, g, b, a)

    elif act_id == "CLOSE":
        draw_line(renderer, cx - 19, cy - 19, cx + 19, cy + 19, r, g, b, a, thickness=5)
        draw_line(renderer, cx + 19, cy - 19, cx - 19, cy + 19, r, g, b, a, thickness=5)

    else:
        fill_rect(renderer, cx - 12, cy - 12, 24, 24, r, g, b, a)


def draw_toggle(renderer, font_badge, x, y, is_on, text_texture_cache=None):
    sw_w = 110
    sw_h = 48
    knob_size = 36
    pad = (sw_h - knob_size) // 2

    if is_on:
        fill_rect(renderer, x, y, sw_w, sw_h, 0, 180, 80, 255)
        draw_rect(renderer, x, y, sw_w, sw_h, 0, 255, 140, 255, thickness=2)
        draw_text(renderer, tr("on"), font_badge, x + 30, y + sw_h // 2, 255, 255, 255, center_x=True, center_y=True, text_texture_cache=text_texture_cache)
        knob_x = x + sw_w - knob_size - pad
        knob_y = y + pad
        fill_rect(renderer, knob_x, knob_y, knob_size, knob_size, 255, 255, 255, 255)
    else:
        fill_rect(renderer, x, y, sw_w, sw_h, 45, 55, 75, 255)
        draw_rect(renderer, x, y, sw_w, sw_h, 80, 95, 125, 255, thickness=1)
        knob_x = x + pad
        knob_y = y + pad
        fill_rect(renderer, knob_x, knob_y, knob_size, knob_size, 150, 160, 180, 255)
        draw_text(renderer, tr("off"), font_badge, x + sw_w - 30, y + sw_h // 2, 170, 180, 200, center_x=True, center_y=True, text_texture_cache=text_texture_cache)


def draw_footer_btn(renderer, font_badge, font_footer, x, foot_y, foot_h, key_char, label_str,
                    btn_color=(0, 230, 150), text_color=(220, 225, 235), is_dark_btn=True, text_texture_cache=None):
    kw_raw = measure_text(key_char, font_badge)
    b_w = max(32, kw_raw + 14)
    b_h = 30
    b_y = foot_y + (foot_h - b_h) // 2
    fill_rect(renderer, x, b_y, b_w, b_h, btn_color[0], btn_color[1], btn_color[2], 255)
    font_btn_col = (0, 0, 0) if is_dark_btn else (255, 255, 255)
    draw_text(renderer, key_char, font_badge, x + b_w // 2, b_y + b_h // 2,
              font_btn_col[0], font_btn_col[1], font_btn_col[2], center_x=True, center_y=True, text_texture_cache=text_texture_cache)
    w, h = draw_text(renderer, label_str, font_footer, x + b_w + 8, foot_y + foot_h // 2,
                     text_color[0], text_color[1], text_color[2], center_y=True, text_texture_cache=text_texture_cache)
    return x + b_w + 8 + w + 22
