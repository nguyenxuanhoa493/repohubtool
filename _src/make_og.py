#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the social sharing cards.

    python3 _src/make_og.py

1200x630 is the 1.91:1 box Facebook, Telegram and Zalo all crop to. Feeding
them a 4:3 screenshot instead means each one crops it differently and the
title ends up half cut off.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630
BG, PANEL, ACCENT, TEXT, MUTED = (13, 18, 32), (22, 34, 58), (0, 246, 246), (238, 243, 251), (147, 164, 192)
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"

CARDS = {
    "en": ("Games and tools for handheld consoles",
           "40,090 games  ·  Java J2ME  ·  Wi-Fi transfer  ·  self-updating"),
    "vi": ("Kho game và tiện ích cho máy chơi game cầm tay",
           "40.090 game  ·  Java J2ME  ·  Truyền file Wi-Fi  ·  Tự cập nhật"),
}


def glow(img, cx, cy, r, colour, strength=0.16):
    """Soft radial light behind the logo, matching the page header."""
    d = ImageDraw.Draw(img, "RGBA")
    steps = 26
    for i in range(steps, 0, -1):
        rr = int(r * i / steps)
        a = int(255 * strength * (1 - i / steps) ** 2)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=colour + (a,))


def main():
    logo = Image.open(os.path.join(ROOT, "logo.png")).convert("RGBA")
    for lang, (tagline, stats) in CARDS.items():
        im = Image.new("RGB", (W, H), BG)
        glow(im, 250, 250, 460, ACCENT)
        d = ImageDraw.Draw(im)
        d.rectangle([0, H - 7, W, H], fill=ACCENT)

        side = 250
        lg = logo.resize((side, side), Image.LANCZOS)
        im.paste(lg, (96, (H - side) // 2 - 12), lg)

        x = 96 + side + 62
        d.text((x, 214), "RetroHub", font=ImageFont.truetype(BOLD, 92), fill=TEXT)
        d.text((x, 326), tagline, font=ImageFont.truetype(REG, 31), fill=MUTED)
        d.text((x, 386), stats, font=ImageFont.truetype(BOLD, 23), fill=ACCENT)

        out = os.path.join(ROOT, "og-%s.png" % lang)
        im.save(out, optimize=True)
        print("  og-%s.png  %dx%d  %d KB" % (lang, W, H, os.path.getsize(out) // 1024))


if __name__ == "__main__":
    main()
