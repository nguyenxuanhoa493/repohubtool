# -*- coding: utf-8 -*-
"""Picking a UI font that can actually draw the text we are about to draw.

The candidate list used to be trusted on filename alone, which quietly broke
Vietnamese on any device whose themes only ship msyh.ttf - Microsoft YaHei has
no o-horn, no u-horn and none of Latin Extended Additional, so 93 of our 119
Vietnamese letters came out as the .notdef box. Whether a device was affected
came down to which theme folders its owner had kept, hence the same build
looking fine on one machine and broken on the next. So probe the font before
committing to it."""

import glob
import os

from .paths import ASSETS_DIR, SDCARD_PATH

# o-horn, u-horn, e-circumflex-dot, o-circumflex-dot, y-tilde. The first two are
# the letters no Chinese face bothers with; the rest sit in the Latin Extended
# Additional block that a Vietnamese-capable font must carry whole. All are BMP,
# so TTF_GlyphIsProvided (Uint16) is enough - no SDL_ttf 2.0.18 needed.
VIET_PROBE = (0x01A1, 0x01B0, 0x1EC7, 0x1ED9, 0x1EF9)

FALLBACK_FONT = os.path.join(ASSETS_DIR, "fallback.ttf")


def font_candidates():
    """Theme fonts first - they carry the CJK that 5 of the catalogue's 39,971
    titles need - then the firmware's own, then our bundled DejaVu, the only one
    we ship and therefore the only one we know covers Vietnamese."""
    return (sorted(glob.glob(f"{SDCARD_PATH}/Themes/*/wqy-microhei.ttf")) +
            sorted(glob.glob(f"{SDCARD_PATH}/Themes/*/msyh.ttf")) +
            sorted(glob.glob(f"{SDCARD_PATH}/Themes/*/*.ttf")) +
            sorted(glob.glob("/usr/trimui/res/*.ttf")) +
            [FALLBACK_FONT])


def pick_font(candidates, has_viet):
    """First candidate that opens AND draws Vietnamese; failing that, the first
    that merely opens.

    `has_viet(path)` returns True/False, or None when the font will not open.
    The second pass matters because a device with no readable font at all shows
    nothing and looks bricked - tofu beats a blank screen. A path that has since
    vanished simply fails to open, so it needs no separate existence check.
    """
    openable = None
    for cand in candidates:
        ok = has_viet(cand)
        if ok:
            return cand
        if ok is not None and openable is None:
            openable = cand
    return openable
