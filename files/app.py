#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import ssl
import shlex
import random
import urllib.request
import subprocess
import threading
import hashlib
import ctypes
import json
try:
    import db
except Exception:
    db = None

# pysdl2 is pure Python - the actual SDL libraries come from /usr/trimui/lib -
# so it ships inside the app. Before this, RetroHub only ran on a device that
# already had PortMaster installed, and failed with a blank screen otherwise.
# PortMaster's copy stays as a fallback, searched after the bundled one so
# everybody exercises the same code.
EXLIBS_PATH = "/mnt/SDCARD/Apps/PortMaster/PortMaster/exlibs"
if os.path.exists(EXLIBS_PATH):
    sys.path.insert(0, EXLIBS_PATH)
VENDOR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(VENDOR_PATH):
    sys.path.insert(0, VENDOR_PATH)

os.environ["PYSDL2_DLL_PATH"] = "/usr/trimui/lib"

try:
    import sdl2
    import sdl2.ext
    import sdl2.sdlttf as sdlttf
    import sdl2.sdlimage as sdlimage
except ImportError as _e:
    # pysdl2 lives in PortMaster's exlibs, not in the stock firmware python. On a
    # handheld an unhandled ImportError just bounces straight back to the menu
    # with nothing on screen, so say what is wrong for anyone who reads the log.
    sys.stderr.write(
        "\nRetroHub khong khoi dong duoc: thieu thu vien SDL2 (%s).\n"
        "Ban cai co the bi thieu thu muc vendor/. Hay tai lai va chep de len.\n"
        "Da tim o: %s\n         va: %s\n\n" % (_e, VENDOR_PATH, EXLIBS_PATH))
    sys.exit(1)

# ==============================================================================
# CONFIG & PATHS
# ==============================================================================

# ==============================================================================
# INTERNALS (split out of this file - see rh/)
# ==============================================================================
from rh import state
from rh.paths import (FLAG_FILES, is_nextui, QR_BMC_FILE, QR_DONATE_FILE,
    QR_TELEGRAM_FILE, SDCARD_PATH, SPLASH_BACKUP_FILE, SPLASH_TEMP_PREVIEW,
    YT_CACHE_DIR)
from rh import corepicker, yt
from rh.i18n import tr, wrap_title_2lines
from rh.sysinfo import (get_battery_info,
    get_device_info_rows,
    get_storage_info_rows)
from rh.services import (get_sftp_guide_rows,
    get_ssh_guide_rows,
    get_stream_guide_rows,
    is_adb_running,
    is_mtp_running,
    is_sftpgo_running,
    is_ssh_running,
    is_streamer_running,
    is_wifi_awake,
    stream_supported,
    toggle_adb,
    toggle_mtp,
    toggle_sftpgo,
    toggle_ssh,
    toggle_streamer,
    toggle_wifi_awake)
from rh.splash import (apply_splash_update,
    convert_and_fit_splash,
    restore_original_splash,
    scan_directory_for_images,
    scan_splash_images)
from rh.j2me import (RENDER_MODES, RESOLUTIONS,
    install_j2me_emulator, is_j2me_runtime_ready, j2me_missing_parts,
    load_render_mode, move_to_resolution, pretty_resolution, resolution_of_path,
    repair_encrypted_jars, repair_unsafe_jar_names, rom_dir_for, runtime_is_stale,
    runtime_supports_renderer, safe_jar_name, save_render_mode)
from rh.emulators import resolve as resolve_emulator
from rh import led, ledconf, ledctl, ledthemes
from rh.fonts import VIET_PROBE, font_candidates, pick_font
from rh.updater import (apply_catalog, apply_runtime, apply_update,
    CATALOG_FAILED, catalog_entry, catalog_pending, CatalogError,
    check_for_update, download_catalog, download_runtime, download_update,
    release_note, request_restart, RUNTIME_FAILED, runtime_pending,
    RuntimeUpdateError, skip_version)
from rh.storage import human_bytes
from rh.version import APP_VERSION, is_newer
from rh.boxart import is_real_boxart_url
from db import CAT_GIAITRI321, CAT_LANDSCAPE
from rh.catalog import (VALID_EXTS, alpha_index, get_java_category_list,
    get_games_for_view,
    get_source_systems_list,
    get_system_display_name,
    scan_all_downloaded_games)
from rh.downloader import (cancel_active_download, clear_download_queue, dl_state,
    download_state_for, enqueue_download, pop_notification, queued_items,
    start_next_queued)

# Range-resume budget for a single part of a parallel download.

# Preferred ROM extensions per system, best first. Disc-based sets must resolve to the
# playlist/descriptor, not a raw data track, or the emulator is handed the wrong file.




# ==============================================================================
# LOCALIZATION (TIẾNG VIỆT CÓ DẤU CHUẨN & ENGLISH) - ZERO EMOJIS (NO TOFU □)
# ==============================================================================

# Split / Wrap Game Title across 2 clean lines (Cached)

# ==============================================================================
# SYSTEM HELPER FUNCTIONS & SERVICE CONTROLS
# ==============================================================================



# ==============================================================================
# BOOT SPLASH MANAGER & CONVERTER
# ==============================================================================



# Fallback boxart: short system tag and accent colour, nothing else. Module level
# because the library grid redraws every tile each frame, and rebuilding this dict
# per tile was pure waste.
# Header bar and where page content starts underneath it. The subtitle line was
# dropped, so the bar lost the 32px it occupied and everything below moved up.
HEADER_H = 64
CONTENT_TOP = HEADER_H + 14

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
    "JAVA": ("JAVA", (205, 97, 85)),
}

# Written by the startup repair thread, drained by the main loop into a toast: a
# background thread has no business touching the UI's own state.
startup_notice = {"msg": None}


def auto_check_and_supplement_environment():
    """Silently checks and auto-supplements missing libraries, emulator cores, and fixes permissions."""
    repaired_items = []
    
    # 1. Rewrite the JAVA system glue when it is missing or stale. Gate on the
    # config file, not on a core binary: the previous check keyed off SquirrelJME,
    # which is not the runtime in use, so deleting that stale core would have
    # retriggered a full reinstall.
    java_cfg = f"{SDCARD_PATH}/Emus/JAVA/config.json"
    java_launch = f"{SDCARD_PATH}/Emus/JAVA/launch.sh"
    if is_j2me_runtime_ready() and not (os.path.exists(java_cfg) and os.path.exists(java_launch)):
        try:
            install_j2me_emulator()
            repaired_items.append("Đã bổ sung cấu hình hệ máy Java J2ME" if state.current_lang == "VI" else "Restored Java J2ME system config")
        except Exception as e:
            print(f"Error restoring J2ME config: {e}")

    # 1b. An emulator older than the archive shipped inside the app. This is what
    # a newer full package dropped over an existing install leaves behind, and
    # nothing used to notice: the old emulator still ran, so the card looked
    # healthy while every feature the new build added was unreachable. Saves are
    # kept. This runs off the startup thread, so the notice goes through
    # startup_notice rather than straight to a toast.
    try:
        if runtime_is_stale():
            ok_up, msg_up = install_j2me_emulator()
            if ok_up:
                startup_notice["msg"] = msg_up
                repaired_items.append(msg_up)
    except Exception as e:
        print(f"Error upgrading J2ME runtime: {e}")

    # 1c. Jars the emulator cannot open. It builds a "jar:file:<path>" URI and
    # never escapes it, so one space in the name and it cannot read the manifest
    # - the game dies before drawing a frame. Games downloaded before this was
    # fixed are already on the card under those names, and re-downloading would
    # not help, so the files themselves get renamed here. Saves follow.
    try:
        n_fixed = repair_unsafe_jar_names()
        if n_fixed:
            msg_fix = (f"Đã sửa tên {n_fixed} game Java để mở được"
                       if state.current_lang == "VI"
                       else f"Renamed {n_fixed} Java games so they will open")
            startup_notice["msg"] = msg_fix
            repaired_items.append(msg_fix)
    except Exception as e:
        print(f"Error repairing J2ME jar names: {e}")

    # 1d. Jars the emulator refuses to open. Java's zip filesystem rejects a whole
    # archive when any entry carries the encryption bit, even a zero-byte marker
    # some packers leave behind, so one such entry makes an otherwise perfect
    # game unopenable. Cheap to check: it reads each jar's central directory, not
    # its contents.
    try:
        n_jar = repair_encrypted_jars()
        if n_jar:
            msg_jar = (f"Đã sửa {n_jar} game Java bị khoá sai để mở được"
                       if state.current_lang == "VI"
                       else f"Repaired {n_jar} Java games the emulator refused to open")
            startup_notice["msg"] = msg_jar
            repaired_items.append(msg_jar)
    except Exception as e:
        print(f"Error repairing encrypted J2ME jars: {e}")

    # 2. Wi-Fi power save is a runtime kernel setting that resets on reboot, so the
    # user's saved choice has to be reapplied here or the toggle would not stick.
    try:
        if state.wifi_awake and not is_wifi_awake():
            from rh.services import apply_wifi_awake
            if apply_wifi_awake(True):
                repaired_items.append("Đã giữ WiFi luôn thức theo cài đặt" if state.current_lang == "VI"
                                      else "Reapplied keep-Wi-Fi-awake setting")
    except Exception as e:
        print(f"Error reapplying Wi-Fi power save: {e}")

    # 3. Check and Create standard ROMs & Imgs directories
    for d in [f"{SDCARD_PATH}/Roms/JAVA", f"{SDCARD_PATH}/Imgs/JAVA", f"{SDCARD_PATH}/Apps/RetroHub/catalog"]:
        try:
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
        except Exception:
            pass

    # 3. Ensure launch script permissions
    try:
        if os.path.exists(f"{SDCARD_PATH}/Emus/JAVA/launch.sh"):
            os.chmod(f"{SDCARD_PATH}/Emus/JAVA/launch.sh", 0o755)
    except Exception:
        pass

    return repaired_items

# ==============================================================================
# BATTERY & POWER SUPPLY STATUS
# ==============================================================================

# ==============================================================================
# SCAN DOWNLOADED LOCAL GAMES WITH BOXART
# ==============================================================================

# ==============================================================================
# SYSTEM NAMES & MULTI-SOURCE RETRIEVAL HELPERS
# ==============================================================================

# ==============================================================================
# DOWNLOAD & UNZIP WORKER THREAD (RESILIENT STREAM + RANGE RESUME + CANCEL)
# ==============================================================================

# ==============================================================================
# MAIN GUI
# ==============================================================================
def main():
    sdl2.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)
    sdlttf.TTF_Init()
    sdlimage.IMG_Init(sdlimage.IMG_INIT_PNG | sdlimage.IMG_INIT_JPG)

    display_mode = sdl2.SDL_DisplayMode()
    if sdl2.SDL_GetCurrentDisplayMode(0, display_mode) == 0:
        state.SCREEN_W = display_mode.w
        state.SCREEN_H = display_mode.h
    else:
        state.SCREEN_W = 1024
        state.SCREEN_H = 768

    controllers = []
    joysticks = []
    has_controller = False

    for i in range(sdl2.SDL_NumJoysticks()):
        if sdl2.SDL_IsGameController(i) == sdl2.SDL_TRUE:
            pad = sdl2.SDL_GameControllerOpen(i)
            if pad:
                controllers.append(pad)
                has_controller = True
        else:
            joy = sdl2.SDL_JoystickOpen(i)
            if joy:
                joysticks.append(joy)

    window = sdl2.SDL_CreateWindow(
        b"RetroHub",
        0, 0,
        state.SCREEN_W,
        state.SCREEN_H,
        sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_FULLSCREEN
    )
    if not window:
        window = sdl2.SDL_CreateWindow(b"RetroHub", 0, 0, state.SCREEN_W, state.SCREEN_H, sdl2.SDL_WINDOW_SHOWN)
    renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.SDL_RENDERER_ACCELERATED)

    # The font used to be pinned to the TRIMUI Blue theme, then to whichever
    # .ttf a theme happened to carry. Both trusted a filename. Microsoft YaHei -
    # the face every stock theme ships - has no o-horn, no u-horn and nothing
    # from Latin Extended Additional, so on a device whose themes had lost
    # wqy-microhei, 93 of the 119 Vietnamese letters drew as .notdef boxes. Open
    # each candidate and ask it for Vietnamese before committing. A theme font
    # is still tried first: assets/fallback.ttf answers yes but has no CJK, and
    # a handful of Chinese titles in the catalogue need it.
    def _font_has_vietnamese(path):
        probe = sdlttf.TTF_OpenFont(path.encode("utf-8"), 16)
        if not probe:
            return None
        try:
            return all(sdlttf.TTF_GlyphIsProvided(probe, cp) for cp in VIET_PROBE)
        finally:
            sdlttf.TTF_CloseFont(probe)

    picked = pick_font(font_candidates(), _font_has_vietnamese)
    if not picked:
        sys.stderr.write("\nRetroHub khong khoi dong duoc: khong mo duoc font .ttf nao, "
                         "ke ca font du phong trong assets/.\n\n")
        return
    font_path = picked.encode("utf-8")

    font_title = sdlttf.TTF_OpenFont(font_path, 40)
    font_sub = sdlttf.TTF_OpenFont(font_path, 26)
    font_item = sdlttf.TTF_OpenFont(font_path, 32)
    font_badge = sdlttf.TTF_OpenFont(font_path, 26)
    font_grid_title = sdlttf.TTF_OpenFont(font_path, 24)
    font_footer = sdlttf.TTF_OpenFont(font_path, 22)
    font_btn_badge = sdlttf.TTF_OpenFont(font_path, 24)
    font_toast = sdlttf.TTF_OpenFont(font_path, 24)
    font_modal_lbl = sdlttf.TTF_OpenFont(font_path, 26)
    font_modal_val = sdlttf.TTF_OpenFont(font_path, 24)
    font_kb = sdlttf.TTF_OpenFont(font_path, 28)
    # For the one value a screen exists to show - the stream address someone is
    # about to type into a browser.
    font_huge = sdlttf.TTF_OpenFont(font_path, 54)

    if not font_title:
        sys.stderr.write("\nRetroHub khong khoi dong duoc: khong mo duoc font %s\n\n"
                         % font_path.decode("utf-8", "ignore"))
        return

    # High-Performance Text Texture LRU Cache
    text_texture_cache = {}
    MAX_TEXT_CACHE = 280

    def draw_text(text, font, x, y, r, g, b, a=255, center_x=False, center_y=False):
        if not text:
            return 0, 0
        now_ts = time.time()
        key = (text, id(font), r, g, b, a)
        cached = text_texture_cache.get(key)
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
            
            # Evict oldest 50 items if cache is full
            if len(text_texture_cache) >= MAX_TEXT_CACHE:
                old_keys = sorted(text_texture_cache.keys(), key=lambda k: text_texture_cache[k][3])[:50]
                for ok in old_keys:
                    item = text_texture_cache.pop(ok, None)
                    if item and item[0]:
                        sdl2.SDL_DestroyTexture(item[0])
            
            text_texture_cache[key] = [tex, w, h, now_ts]

        dest_x = x - (w // 2) if center_x else x
        dest_y = y - (h // 2) if center_y else y
        dest = sdl2.SDL_Rect(dest_x, dest_y, w, h)
        sdl2.SDL_RenderCopy(renderer, tex, None, dest)
        return w, h

    _text_w_cache = {}

    def measure_text(text, font):
        """Pixel width of text in this font, without drawing it.

        Character counts are a poor proxy here: Vietnamese diacritics and the
        proportional font make identical-length strings render very differently.
        """
        if not text:
            return 0
        key = (text, id(font))
        cached = _text_w_cache.get(key)
        if cached is not None:
            return cached
        w = ctypes.c_int(0)
        h = ctypes.c_int(0)
        sdlttf.TTF_SizeUTF8(font, text.encode("utf-8"), ctypes.byref(w), ctypes.byref(h))
        if len(_text_w_cache) > 600:
            _text_w_cache.clear()
        _text_w_cache[key] = w.value
        return w.value

    def wrap_text_to_width(text, font, max_w, max_lines=2):
        """Break text into at most max_lines that each fit within max_w pixels.

        Falls back to a hard character split for a single word longer than the
        line, and ellipsises whatever still does not fit on the final line.
        """
        text = (text or "").strip()
        if not text or measure_text(text, font) <= max_w:
            return [text]

        words = text.split()
        lines = []
        cur = ""
        for i, word in enumerate(words):
            cand = (cur + " " + word).strip()
            if cur and measure_text(cand, font) > max_w:
                lines.append(cur)
                if len(lines) == max_lines - 1:
                    # Everything left goes on the final line; index the word list
                    # rather than slicing the original string, which would be off
                    # whenever the title contains repeated spaces.
                    cur = " ".join(words[i:])
                    break
                cur = word
            else:
                cur = cand

        if measure_text(cur, font) > max_w:
            while cur and measure_text(cur + "...", font) > max_w:
                cur = cur[:-1]
            cur = cur.rstrip() + "..."
        lines.append(cur)
        return lines[:max_lines]

    def fill_rect(x, y, w, h, r, g, b, a=255):
        rect = sdl2.SDL_Rect(x, y, w, h)
        sdl2.SDL_SetRenderDrawColor(renderer, r, g, b, a)
        sdl2.SDL_RenderFillRect(renderer, rect)

    def draw_rect(x, y, w, h, r, g, b, a=255, thickness=1):
        sdl2.SDL_SetRenderDrawColor(renderer, r, g, b, a)
        for i in range(thickness):
            rect = sdl2.SDL_Rect(x + i, y + i, w - 2*i, h - 2*i)
            sdl2.SDL_RenderDrawRect(renderer, rect)

    def draw_toggle(x, y, is_on):
        sw_w = 110
        sw_h = 48
        knob_size = 36
        pad = (sw_h - knob_size) // 2

        if is_on:
            fill_rect(x, y, sw_w, sw_h, 0, 180, 80, 255)
            draw_rect(x, y, sw_w, sw_h, 0, 255, 140, 255, thickness=2)
            draw_text(tr("on"), font_badge, x + 30, y + sw_h // 2, 255, 255, 255, center_x=True, center_y=True)
            knob_x = x + sw_w - knob_size - pad
            knob_y = y + pad
            fill_rect(knob_x, knob_y, knob_size, knob_size, 255, 255, 255, 255)
        else:
            fill_rect(x, y, sw_w, sw_h, 45, 55, 75, 255)
            draw_rect(x, y, sw_w, sw_h, 80, 95, 125, 255, thickness=1)
            knob_x = x + pad
            knob_y = y + pad
            fill_rect(knob_x, knob_y, knob_size, knob_size, 150, 160, 180, 255)
            draw_text(tr("off"), font_badge, x + sw_w - 30, y + sw_h // 2, 170, 180, 200, center_x=True, center_y=True)

    # State
    screen_stack = ["home"]
    selected_indices = {
        "home": 0,
        "network": 0,
        "utilities": 0,
        "rom_store_menu": 0,
        "rom_source_systems": 0,
        "downloaded_games": 0,
        "search_input": 0,
        "search_results": 0,
        "rom_systems": 0,
        "rom_games": 0,
        "yt_grid": 0,
        "yt_search_input": 0
    }
    scroll_offsets = {
        "home": 0,
        "network": 0,
        "utilities": 0,
        "rom_store_menu": 0,
        "rom_source_systems": 0,
        "downloaded_games": 0,
        "search_input": 0,
        "search_results": 0,
        "rom_systems": 0,
        "rom_games": 0,
        "file_browser": 0,
        "splash_manager": 0,
        "yt_grid": 0,
        "yt_search_input": 0
    }
    current_source = "VIET"
    current_rom_system = "ALL"
    # Which J2ME shelf is being browsed; "ALL" means every Java game.
    current_java_cat = "ALL"
    # The shelf list costs ~96ms to query and the screen rebuilds every frame,
    # so it is fetched once per visit rather than 60 times a second.
    java_cats_cache = []
    # Same reason: the systems list for a source is a DB aggregate over 40k rows.
    src_sys_cache = []
    src_sys_cache_key = None
    # The rom_games screen previously rebuilt its list on every frame, which caused
    # thousands of filesystem calls and dropped framerate to 1-2 FPS.
    # We now memoise the raw games and cache the built items, resolving boxarts on demand.
    rom_games_cache = []
    rom_games_cache_key = None
    rom_games_items_cache = None
    rom_games_items_key = None
    search_results_items_cache = None
    search_results_items_key = None
    downloaded_items_cache = None
    downloaded_items_key = None
    cached_lib_games_list = []
    cached_lib_games_key = None
    state.rom_sort_mode = "downloads"  # "downloads" (Default) or "alpha"

    def resolve_game_img_path(sys_code, filename):
        """Find local boxart path (.png or .jpg) on-demand when opening modal."""
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

    # Search Systems Filter Options. These come from the catalogue DB rather than
    # the static catalogs.json: the DB carries 29 systems where the JSON listed only
    # 13, so PS, PSP, DC, SS, N64 and friends were missing from the filter entirely.
    j2me_render_mode = None     # filled when the display screen is opened
    core_sys_rows = []          # cac he doi core duoc, doc khi mo man hinh do
    core_sys_pick = None        # he dang chon, cho man hinh chon giai lap
    # DEN LED: doc mot lan luc khoi dong, sau do man hinh cai dat la nguon su
    # that. Ghi vao led.json la cach duy nhat noi chuyen voi daemon.
    led_cfg = ledconf.load()
    led_zones = led.detect_zones()
    # Bo mau dang duoc xem thu tren man hinh chon bo mau. Rieng voi
    # led_cfg["theme"], vi led_cfg giu lua chon da chot - ban de tra ve khi
    # nguoi dung roi man hinh ma khong chon.
    led_preview = None
    _sys_rows = get_source_systems_list("ALL")
    _sys_counts = dict(_sys_rows)
    sys_keys_list = ["ALL"] + [c for c, _ in _sys_rows if c != "ALL"]
    search_sys_idx = 0
    # Which catalogue source the search is narrowed to; "ALL" means every source.
    search_source = "ALL"
    SEARCH_SOURCES = ["ALL", "VIET", "HITS", "JAVA", "HACK", "RETROSTIC", "ARCHIVE"]

    # Virtual Keyboard & Search State
    kb_rows = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", "-"],
        ["Z", "X", "C", "V", "B", "N", "M", ".", "_", "/"],
        ["SPACE", "DEL", "CLEAR", "SEARCH"]
    ]
    kb_cursor = [1, 0]
    search_query = ""
    search_results_list = []

    # YouTube InnerTube state
    yt_trending_list = []
    yt_search_query = ""
    yt_search_results_list = []
    yt_mode = "trending" # "trending" or "search"
    yt_recent_queries = yt.load_search_history()
    yt_query_idx = 0
    yt_query_cache = {}
    yt_input_text = ""
    yt_last_hover_id = None
    yt_hover_start_time = 0
    yt_prefetch_thread = None
    yt_loading_state = {
        "active": False,
        "query": "",
        "id": 0,
        "start_time": 0.0,
    }

    # Khởi chạy giải nén và nạp trước yt-dlp vào bộ nhớ RAM ngầm
    import rh.yt_player as yt_player
    threading.Thread(target=yt_player.ensure_ytdlp_ready, daemon=True).start()

    # Restore session state when returning from video playback
    _resume_file = "/tmp/retrohub_resume.json"
    if os.path.exists(_resume_file):
        try:
            with open(_resume_file, "r", encoding="utf-8") as _rf:
                _r_data = json.load(_rf)
            os.remove(_resume_file)
            if isinstance(_r_data, dict):
                if "screen_stack" in _r_data and isinstance(_r_data["screen_stack"], list) and _r_data["screen_stack"]:
                    screen_stack = _r_data["screen_stack"]
                if "selected_indices" in _r_data and isinstance(_r_data["selected_indices"], dict):
                    selected_indices.update(_r_data["selected_indices"])
                if "scroll_offsets" in _r_data and isinstance(_r_data["scroll_offsets"], dict):
                    scroll_offsets.update(_r_data["scroll_offsets"])
                yt_mode = _r_data.get("yt_mode", yt_mode)
                yt_search_query = _r_data.get("yt_search_query", yt_search_query) or ""
                yt_trending_list = _r_data.get("yt_trending_list", yt_trending_list) or []
                yt_search_results_list = _r_data.get("yt_search_results_list", yt_search_results_list) or []
                saved_queries = _r_data.get("yt_recent_queries")
                if isinstance(saved_queries, list) and saved_queries:
                    yt_recent_queries = saved_queries
                if not yt_recent_queries:
                    yt_recent_queries = list(yt.DEFAULT_QUERIES)
                yt_query_idx = max(0, min(len(yt_recent_queries) - 1, int(_r_data.get("yt_query_idx", 0))))
                saved_cache = _r_data.get("yt_query_cache")
                if isinstance(saved_cache, dict):
                    yt_query_cache = saved_cache
        except Exception as _re:
            print(f"[RetroHub] Error restoring resume state: {_re}")

    def _prefetch_yt_thumbs(video_list):
        if not video_list:
            return
        def _worker():
            for v in video_list[:24]:
                vid = v.get("id")
                thumb_url = v.get("thumb")
                if vid and thumb_url:
                    yt.fetch_thumbnail(thumb_url, YT_CACHE_DIR, vid)
        threading.Thread(target=_worker, daemon=True).start()

    def start_yt_load(query_str, is_trending=False):
        nonlocal yt_search_results_list, yt_trending_list
        yt_loading_state["active"] = True
        yt_loading_state["query"] = query_str
        yt_loading_state["id"] += 1
        req_id = yt_loading_state["id"]
        yt_loading_state["start_time"] = time.time()

        def _worker():
            nonlocal yt_search_results_list, yt_trending_list
            try:
                if is_trending:
                    data = yt.get_trending(limit=30) or []
                else:
                    eff = yt.get_effective_query(query_str)
                    data = yt.search_youtube(eff, limit=30) or []
            except Exception as e:
                print(f"[RetroHub] YouTube bg fetch error: {e}")
                data = []

            if req_id == yt_loading_state["id"]:
                if is_trending:
                    yt_trending_list = data
                else:
                    yt_query_cache[query_str] = data
                    yt_search_results_list = data
                _prefetch_yt_thumbs(data)
                yt_loading_state["active"] = False
                trigger_yt_adjacent_preload()
            else:
                if not is_trending and data:
                    yt_query_cache[query_str] = data

        threading.Thread(target=_worker, daemon=True).start()

    yt_preload_thread = None

    def trigger_yt_adjacent_preload():
        nonlocal yt_preload_thread
        if not yt_recent_queries or len(yt_recent_queries) < 2:
            return

        cur_idx = yt_query_idx
        next_idx = (cur_idx + 1) % len(yt_recent_queries)
        prev_idx = (cur_idx - 1) % len(yt_recent_queries)

        candidates = []
        for idx in (next_idx, prev_idx):
            if 0 <= idx < len(yt_recent_queries):
                q = yt_recent_queries[idx]
                if q == "Nhạc trẻ" or idx == 0:
                    if not yt_trending_list:
                        candidates.append((q, True))
                else:
                    if q not in yt_query_cache or not yt_query_cache[q]:
                        candidates.append((q, False))

        if not candidates:
            return

        def _preload_worker():
            for target_q, is_tr in candidates:
                if yt_loading_state.get("active", False):
                    break
                try:
                    if is_tr:
                        if not yt_trending_list:
                            data = yt.get_trending(limit=30) or []
                            if data and not yt_trending_list:
                                yt_trending_list.extend(data)
                                _prefetch_yt_thumbs(data)
                    else:
                        if target_q not in yt_query_cache or not yt_query_cache[target_q]:
                            eff = yt.get_effective_query(target_q)
                            data = yt.search_youtube(eff, limit=30) or []
                            if data:
                                yt_query_cache[target_q] = data
                                _prefetch_yt_thumbs(data)
                except Exception as e:
                    print(f"[RetroHub] YouTube preload error for {target_q}: {e}")
                time.sleep(0.4)

        if yt_preload_thread is None or not yt_preload_thread.is_alive():
            yt_preload_thread = threading.Thread(target=_preload_worker, daemon=True)
            yt_preload_thread.start()

    # Downloaded Games Cache & Proportional Image Loading
    downloaded_games_list = []
    # Library filter: "ALL" or a single sys_code. Kept out of settings.json on
    # purpose - it is a transient view choice, not a preference.
    current_lib_sys = "ALL"
    # One list picker serving the library filter and both search filters. rows are
    # (code, label, right_text); "current" is the value shown with a filled dot.
    pick_modal = {"active": False, "title": "", "rows": [], "selected_idx": 0,
                  "target": "", "current": ""}
    img_texture_cache = {}
    missing_img_cache = set()
    MAX_IMG_CACHE = 60

    def get_texture_and_size(path, force_reload=False):
        if not path:
            return None, 0, 0
        if not force_reload and path in missing_img_cache:
            return None, 0, 0
        if force_reload:
            missing_img_cache.discard(path)

        now_ts = time.time()
        if force_reload or path == SPLASH_TEMP_PREVIEW:
            if path in img_texture_cache:
                tex, _, _, _ = img_texture_cache.pop(path)
                sdl2.SDL_DestroyTexture(tex)
        elif path in img_texture_cache:
            item = img_texture_cache[path]
            item[3] = now_ts
            return item[0], item[1], item[2]

        if not os.path.exists(path):
            missing_img_cache.add(path)
            return None, 0, 0

        surf = sdlimage.IMG_Load(path.encode("utf-8"))
        if not surf:
            missing_img_cache.add(path)
            return None, 0, 0
        w = surf.contents.w
        h = surf.contents.h
        tex = sdl2.SDL_CreateTextureFromSurface(renderer, surf)
        sdl2.SDL_FreeSurface(surf)
        if tex:
            # Evict oldest 15 textures if cache exceeds limit
            if len(img_texture_cache) >= MAX_IMG_CACHE:
                old_paths = sorted(img_texture_cache.keys(), key=lambda k: img_texture_cache[k][3])[:15]
                for op in old_paths:
                    it = img_texture_cache.pop(op, None)
                    if it and it[0]:
                        sdl2.SDL_DestroyTexture(it[0])
            img_texture_cache[path] = [tex, w, h, now_ts]
            return tex, w, h
        return None, 0, 0

    def draw_proportional_boxart(path, box_x, box_y, box_w, box_h):
        tex, orig_w, orig_h = get_texture_and_size(path)
        if not tex or orig_w <= 0 or orig_h <= 0:
            return False
        scale = min(box_w / float(orig_w), box_h / float(orig_h))
        dest_w = max(1, int(orig_w * scale))
        dest_h = max(1, int(orig_h * scale))
        dest_x = box_x + (box_w - dest_w) // 2
        dest_y = box_y + (box_h - dest_h) // 2
        dest_r = sdl2.SDL_Rect(dest_x, dest_y, dest_w, dest_h)
        sdl2.SDL_RenderCopy(renderer, tex, None, dest_r)
        return True

    def draw_default_boxart_avatar(box_x, box_y, box_w, box_h, sys_code="ROM", game_title="Game"):
        """Placeholder tile for a game with no boxart.

        Deliberately plain: a coloured header with the system tag and a small
        cartridge mark. The mark is drawn from rectangles rather than an emoji
        because the bundled font has no emoji glyphs and would render tofu boxes.
        game_title is unused, kept so existing call sites stay valid.
        """
        if box_w <= 10 or box_h <= 10:
            return False

        s_tag, theme_col = SYS_BADGE.get(sys_code.upper(), (sys_code.upper(), (0, 200, 220)))
        tr_c, tg_c, tb_c = theme_col

        # Card body with a subtle bevel
        fill_rect(box_x, box_y, box_w, box_h, 16, 22, 34, 255)
        fill_rect(box_x + 1, box_y + 1, box_w - 2, 2, 65, 85, 125, 255)
        fill_rect(box_x + 1, box_y + box_h - 3, box_w - 2, 2, 8, 12, 18, 255)
        draw_rect(box_x, box_y, box_w, box_h, 40, 55, 85, 255, thickness=1)

        # Coloured header carrying the system tag - the only text on the tile
        header_h = max(24, int(box_h * 0.16))
        fill_rect(box_x + 2, box_y + 2, box_w - 4, header_h, tr_c, tg_c, tb_c, 255)
        fill_rect(box_x + 2, box_y + header_h, box_w - 4, 1, 255, 255, 255, 90)
        draw_text(s_tag, font_badge, box_x + box_w // 2, box_y + header_h // 2 + 1,
                  255, 255, 255, center_x=True, center_y=True)

        # Small cartridge mark, centred in the remaining space
        body_y = box_y + header_h
        body_h = box_h - header_h
        cw = max(14, min(int(box_w * 0.34), int(body_h * 0.44)))
        ch = int(cw * 1.15)
        cx = box_x + (box_w - cw) // 2
        cy = body_y + (body_h - ch) // 2
        if cw >= 14 and ch >= 14:
            fill_rect(cx, cy, cw, ch, tr_c, tg_c, tb_c, 60)
            draw_rect(cx, cy, cw, ch, tr_c, tg_c, tb_c, 150, thickness=1)
            lx, ly = cx + max(2, cw // 6), cy + max(2, ch // 6)
            lw, lh = cw - 2 * max(2, cw // 6), int(ch * 0.42)
            if lw > 4 and lh > 4:
                fill_rect(lx, ly, lw, lh, tr_c, tg_c, tb_c, 120)
            pin_w = max(2, cw // 7)
            pin_y = cy + ch - max(3, ch // 8)
            for k in range(3):
                px = cx + max(2, cw // 6) + k * (pin_w * 2)
                if px + pin_w <= cx + cw - 2:
                    fill_rect(px, pin_y, pin_w, max(2, ch // 10), tr_c, tg_c, tb_c, 170)
        return True

    # Pre-Download Game Preview & Info Modal (Requirement 5)
    pre_download_modal = {
        "active": False,
        "game_info": None,
        "sys_code": "GBA",
        "img_path": None,
        "img_url": "",
        "preview_cached_path": None,
        "preview_status": "idle",
        "selected_opt": 0
    }

    def open_pre_download_modal(sys_c, g_info, local_img_path=None):
        pre_download_modal["active"] = True
        pre_download_modal["game_info"] = g_info
        pre_download_modal["sys_code"] = sys_c
        pre_download_modal["selected_opt"] = 0
        if not local_img_path and g_info:
            local_img_path = resolve_game_img_path(sys_c, g_info.get("filename"))
        pre_download_modal["img_path"] = local_img_path
        pre_download_modal["preview_cached_path"] = None

        img_url = g_info.get("img_url", "")
        pre_download_modal["img_url"] = img_url

        # Dynamic File Size Resolution for Online Mirrors / Retrostic
        pre_download_modal["dynamic_size_str"] = (g_info.get("file_size_str") or g_info.get("size") or "").strip() if g_info else ""
        if not pre_download_modal["dynamic_size_str"] or pre_download_modal["dynamic_size_str"] in ("TOPO SHOP", "TOPO"):
            pre_download_modal["dynamic_size_str"] = ""
            rom_u = g_info.get("rom_url", "") if g_info else ""
            if rom_u and rom_u.startswith("http"):
                def bg_fetch_rom_size(target_url, g_target):
                    try:
                        c_ctx = ssl._create_unverified_context()
                        p_req = urllib.request.Request(
                            target_url,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                "Range": "bytes=0-0"
                            }
                        )
                        with urllib.request.urlopen(p_req, context=c_ctx, timeout=4) as p_resp:
                            cr = p_resp.headers.get("Content-Range", "")
                            tot = 0
                            if cr and "/" in cr:
                                try:
                                    tot = int(cr.split("/")[-1])
                                except:
                                    pass
                            if tot == 0:
                                tot = int(p_resp.headers.get("Content-Length", 0))
                            if tot > 0:
                                if tot >= 1024 * 1024 * 1024:
                                    s_fmt = f"{tot / (1024*1024*1024):.2f} GB"
                                elif tot >= 1024 * 1024:
                                    s_fmt = f"{tot / (1024*1024):.1f} MB"
                                elif tot >= 1024:
                                    s_fmt = f"{tot / 1024:.1f} KB"
                                else:
                                    s_fmt = f"{tot} B"
                                g_target["file_size_str"] = s_fmt
                                pre_download_modal["dynamic_size_str"] = s_fmt
                                src_id = g_target.get("source_id")
                                if src_id:
                                    try:
                                        db.update_source_file_size(src_id, s_fmt)
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                threading.Thread(target=bg_fetch_rom_size, args=(rom_u, g_info), daemon=True).start()

        if local_img_path and os.path.exists(local_img_path):
            pre_download_modal["preview_status"] = "ready"
        elif is_real_boxart_url(img_url):
            url_hash = hashlib.md5(img_url.encode("utf-8")).hexdigest()[:12]
            ext = ".jpg" if (".jpg" in img_url.lower() or ".jpeg" in img_url.lower()) else ".png"
            tmp_prev = f"/tmp/prev_{url_hash}{ext}"
            if os.path.exists(tmp_prev) and os.path.getsize(tmp_prev) > 1024:
                pre_download_modal["preview_cached_path"] = tmp_prev
                pre_download_modal["preview_status"] = "ready"
            else:
                pre_download_modal["preview_status"] = "loading"
                def bg_fetch(u, dest):
                    try:
                        ctx = ssl._create_unverified_context()
                        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
                            if resp.status == 200:
                                ctype = resp.headers.get("Content-Type", "").lower()
                                if "image" in ctype or not ctype:
                                    data = resp.read()
                                    if len(data) > 1024:
                                        with open(dest, "wb") as f:
                                            f.write(data)
                                        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
                                            pre_download_modal["preview_cached_path"] = dest
                                            pre_download_modal["preview_status"] = "ready"
                                            return
                        pre_download_modal["preview_status"] = "failed"
                    except Exception:
                        pre_download_modal["preview_status"] = "failed"
                threading.Thread(target=bg_fetch, args=(img_url, tmp_prev), daemon=True).start()
        else:
            pre_download_modal["preview_status"] = "failed"

    # Horizontal Action Popup State
    game_action_modal = {
        "active": False,
        "game_info": None,
        "selected_opt": 0,
        "from_downloaded_view": False,
        "img_path": None,
        "size_str": ""
    }

    # Alphabet Quick Jump Modal State (A - Z Grid)
    # Screen-size picker for Java games. A list rather than a cycling button: five
    # sizes is too many to step through blind, and you cannot see what is on offer.
    res_modal = {"active": False, "selected_idx": 0}

    # Java emulator info + reinstall. `pending` defers the actual work by one frame
    # so the "installing" line is on screen before the UI thread blocks on it.
    j2me_modal = {"active": False, "busy": False, "pending": False}

    # Shows a scannable code beside a few lines of text. Used for the donation
    # transfer details and the chat group invite.
    # pages is a list of {title, img, mods, rows}. A single-page call still works:
    # the shoulder hint and the counter only appear when there is more than one.
    qr_modal = {"active": False, "pages": [], "page": 0}

    # Filled in by the startup check thread; the main loop shows it when a newer
    # release is published. selected_opt: 0 install, 1 skip this version, 2
    # later - tru khi cat_only, xem update_modal_labels().
    update_modal = {
        "active": False, "manifest": None, "files": [],
        "selected_opt": 0, "busy": False, "status": "", "failed": False,
        # Set while a manual check is in flight, and used by the worker thread to
        # hand a message back - toast_msg is a local of the main loop.
        "checking": False, "notice": None,
        # True khi phien ban khong doi va chi co catalogue dang cho: man hinh
        # phai noi ve kho game chu khong phai "ban moi" trung voi ban dang
        # chay, va nut giua khong duoc mang nghia "bo qua phien ban" nua.
        "cat_only": False,
    }

    def update_modal_labels():
        """Nhan cac nut modal cap nhat, theo dung thu tu voi selected_opt.

        cat_only bo han nut "Bo qua ban nay": phia duoi skip_version() ghi
        thang so hieu manifest vao skipped_versions, ma o day so hieu do
        chinh la ban dang chay - bam "bo qua" se khoa catalogue toi tan ban
        ke tiep, con lau hon la khong bam gi ca. An nut la cach ro nhat de
        khong con duong bam nham."""
        if update_modal["cat_only"]:
            return [tr("upd_install"), tr("upd_later")]
        return [tr("upd_install"), tr("upd_skip"), tr("upd_later")]

    alphabet_modal = {
        "active": False,
        "selected_idx": 0,
        "letters": ["#"] + [chr(c) for c in range(ord('A'), ord('Z') + 1)],
        "available_map": {},
        "counts_map": {},
        "sys_code": None,
        # Dang xep theo luot tai thi nhay chu cai se doi danh sach ve A-Z.
        "needs_alpha_sort": False
    }

    modal_title = None
    modal_rows = None
    # Layout for the shared info modal. None keeps the stacked label-over-value
    # rows the long device/storage values need; "two_col" is the table form.
    modal_style = None
    toast_msg = None
    toast_timer = 0

    # Kiem tra neu co loi phat YouTube tu lan thoat truoc
    if os.path.exists("/tmp/yt_last_error.txt"):
        try:
            with open("/tmp/yt_last_error.txt", "r", encoding="utf-8") as _f:
                _yt_err = _f.read().strip()
            if _yt_err:
                toast_msg = f"Lỗi YouTube: {_yt_err[:45]}"
                toast_timer = time.time()
            os.remove("/tmp/yt_last_error.txt")
        except Exception:
            pass

    splash_images_list = []
    splash_preview_path = ""
    splash_preview_orig_name = ""
    fb_current_path = "/mnt/SDCARD"
    fb_items = []
    fb_scanned_path = None

    # Auto-check and supplement missing libraries & emulator cores in background
    try:
        threading.Thread(target=auto_check_and_supplement_environment, daemon=True).start()
    except Exception:
        pass

    def bg_check_update():
        """Ask the update repo whether a newer build exists.

        Runs off the main loop: the request can block for the full timeout, and
        the UI must not wait on it. Nothing is downloaded here - the user
        decides first."""
        try:
            found = check_for_update()
        except Exception as e:
            print(f"Update check error: {e}")
            return
        if not found:
            return
        manifest, files = found
        update_modal["manifest"] = manifest
        update_modal["files"] = files
        update_modal["selected_opt"] = 0
        # check_for_update() chi tra viec khi is_newer, catalog_pending hoac
        # runtime_pending; khong is_newer thi day la mot trong hai duong kia.
        update_modal["cat_only"] = not is_newer(manifest["version"], APP_VERSION)
        update_modal["active"] = True

    def run_update():
        """Fetch, verify and install the pending release, then ask for a restart.

        Every file is downloaded and hash-checked before anything is moved, so a
        failure here leaves the running install exactly as it was."""
        m = update_modal["manifest"]
        files = update_modal["files"]

        def prog(done, total, path):
            name = os.path.basename(path) if path else ""
            update_modal["status"] = f"{done}/{total}  {name}".strip()

        ok = False
        try:
            if download_update(m, files, progress=prog):
                update_modal["status"] = tr("upd_installing")
                ok = apply_update(m, files)
        except Exception as e:
            print(f"Update error: {e}")

        # Bo gia lap di truoc kho game: no nho hon nhieu va la thu quyet dinh
        # game Java co chay dung hay khong. Cung nhu kho game, hong o day khong
        # duoc keo theo ban .py - app van len phien ban moi, lan kiem tra sau
        # runtime_pending van dung nen no tu thu lai.
        if ok:
            try:
                rt_pending = runtime_pending(m)
            except Exception as e:
                print(f"Runtime check error: {e}")
                rt_pending = []
            if rt_pending:
                def rt_prog(done, total, path):
                    update_modal["status"] = "%s %d/%d" % (
                        tr("upd_rt_downloading"), done, total)
                try:
                    download_runtime(rt_pending, progress=rt_prog)
                    update_modal["status"] = tr("upd_rt_installing")
                    if not apply_runtime(rt_pending):
                        raise RuntimeUpdateError(RUNTIME_FAILED, "cai dat that bai")
                except RuntimeUpdateError as re_:
                    print(f"Runtime update failed: {re_}")
                    state.pending_catalog_notice = tr(re_.key)
                except Exception as e:
                    print(f"Runtime update error: {e}")
                    state.pending_catalog_notice = tr(RUNTIME_FAILED)

        # Kho game di sau va di rieng: tai hong thi ban .py van giu nguyen va
        # app van len phien ban moi, chi la chua co bia. Lan kiem tra sau
        # catalog_pending van dung nen no tu thu lai.
        if ok and catalog_pending(m):
            # Tai va giai nen deu nam trong download_catalog; on_phase bao dung
            # luc no chuyen tu tai sang giai nen, de nhan tren man hinh khong
            # noi sai dang lam gi. apply_catalog chi la doi ten mot file, tu
            # chua da xong nen khong can nhan rieng.
            def enter_unpack():
                update_modal["status"] = tr("upd_cat_unpacking")
            try:
                update_modal["status"] = tr("upd_cat_downloading")
                staged = download_catalog(m, on_phase=enter_unpack)
                # apply_catalog tra False khi os.replace hong (vd giua duong
                # bi rut the); ep no thanh CatalogError de di chung mot nhanh
                # xu ly voi loi tai - khong the de mot lan cai hong lang le
                # trong khi mot lan tai hong thi nguoi dung duoc bao.
                if not apply_catalog(m, staged):
                    raise CatalogError(CATALOG_FAILED, "cai dat that bai")
            except CatalogError as ce:
                print(f"Catalog update failed: {ce}")
                # Khong ghi thang vao update_modal: request_restart() sap ket
                # thuc vong lap chi mot nhip sau, toast khong kip doc. Ghi vao
                # settings nhu pending_update, hien o lan khoi dong ke tiep.
                # Chi giu key da dich: modal ve mot dong khong xuong dong, va
                # ce.detail (vd "can 111 MB, con 18 MB") thuong dai hon cho
                # con lai duoi tran 34 ky tu.
                state.pending_catalog_notice = tr(ce.key)
            except Exception as e:
                # Bat het con lai: vd os.statvfs trong download_catalog nem
                # OSError truoc ca try cua no, nen no khong di theo nhanh
                # CatalogError o tren. Loi kieu nay van phai co notice, khong
                # duoc im lang nhu truoc.
                print(f"Catalog update error: {e}")
                state.pending_catalog_notice = tr(CATALOG_FAILED)

        if ok:
            update_modal["status"] = tr("upd_done")
            # Leave a marker for the build that is about to start. Confirming
            # success here would be premature - the new bytecode has not run yet.
            state.pending_update = m["version"]
            state.save_settings()
            request_restart()
            update_modal["restart"] = True
        else:
            update_modal["failed"] = True
            update_modal["status"] = tr("upd_failed")
        update_modal["busy"] = False

    def manual_check_update():
        """Check on demand, from the version row in Settings.

        force=True so a version the user skipped earlier still shows: asking by
        hand is a clear signal they want to see whatever is out there."""
        try:
            found = check_for_update(force=True)
        except Exception as e:
            print(f"Manual update check error: {e}")
            update_modal["notice"] = tr("upd_check_failed")
            update_modal["checking"] = False
            return
        if found:
            manifest, files = found
            update_modal["manifest"] = manifest
            update_modal["files"] = files
            update_modal["selected_opt"] = 0
            update_modal["cat_only"] = not is_newer(manifest["version"], APP_VERSION)
            update_modal["failed"] = False
            update_modal["active"] = True
        else:
            update_modal["notice"] = tr("upd_up_to_date")
        update_modal["checking"] = False

    # An update that restarted the app leaves its version behind. Seeing it match
    # the build now running is the proof the swap worked, so report it once and
    # clear the marker.
    if state.pending_update:
        if state.pending_update == APP_VERSION:
            update_modal["notice"] = f"{tr('upd_success')}{APP_VERSION}"
        state.pending_update = ""
        state.save_settings()

    # Cung mot ly do: loi catalogue ghi truoc luc restart vi khong con nhip
    # nao de nguoi dung doc toast. Uu tien no hon "upd_success" o tren neu ca
    # hai cung co - mat kho game la thu dang bao hon la ban vua len phien ban
    # moi thanh cong.
    if state.pending_catalog_notice:
        update_modal["notice"] = state.pending_catalog_notice
        state.pending_catalog_notice = ""
        state.save_settings()

    if state.auto_update:
        try:
            threading.Thread(target=bg_check_update, daemon=True).start()
        except Exception:
            pass

    running = True
    last_user_activity_time = time.time()

    local_cache_map = {}
    last_cache_time = {}

    def resolve_local_name(fn, sys_code, local_files):
        """The name this game actually has on the card.

        Java jars are saved under a cleaned name - the emulator cannot open one
        with a space in it - so the file on disk does not match the catalogue's
        spelling. Without this, all 758 such titles read as never downloaded and
        offer to download again over a copy that is already there.
        """
        if fn in local_files or sys_code not in ("JAVA", "J2ME"):
            return fn
        safe = safe_jar_name(fn)
        return safe if safe in local_files else fn

    def get_local_cache(sys_code):
        now_t = time.time()
        if sys_code in local_cache_map and now_t - last_cache_time.get(sys_code, 0) < 4.0:
            return local_cache_map[sys_code]
        rom_dir = state.catalogs.get(sys_code, {}).get("rom_dir", f"{SDCARD_PATH}/Roms/{sys_code}")
        # Maps filename -> real path. J2ME sorts its jars into one folder per
        # handset resolution, so those roms sit a level below rom_dir: a flat
        # listing saw only the folders and reported every Java game as missing,
        # and joining rom_dir with the filename pointed at a file that is not
        # there. scandir keeps the directory test off the stat path, which
        # matters for systems holding thousands of roms.
        res = {}
        try:
            with os.scandir(rom_dir) as it:
                for e in it:
                    if e.is_dir():
                        try:
                            with os.scandir(e.path) as sub_it:
                                for se in sub_it:
                                    if not se.is_dir():
                                        res.setdefault(se.name, se.path)
                        except OSError:
                            pass
                    else:
                        # A rom sitting directly in rom_dir wins over a same-named
                        # one in a subfolder.
                        res[e.name] = e.path
        except OSError:
            res = {}
        local_cache_map[sys_code] = res
        last_cache_time[sys_code] = now_t
        return res

    def java_cat_label(code):
        """Ten hien ra cho mot ke game Java.

        Hai ke ghim mang ma bat dau bang "@" - chung duoc tinh ra chu khong phai
        thu muc cua nguon - nen phai co nhan rieng, khong the in thang ma ra.
        Mot cho duy nhat, dung cho ca danh sach ke lan tieu de man hinh game."""
        if code == "ALL":
            return tr("java_cat_all")
        if code == CAT_GIAITRI321:
            return tr("java_cat_giaitri321")
        if code == CAT_LANDSCAPE:
            return tr("java_cat_landscape")
        if code == "":
            return tr("java_cat_none")
        return code

    def number_items(rows):
        """Prefix a running number onto the primary rows of a menu.

        Sub-rows (the per-service guides) and the back row are skipped: they are
        not choices in the same sequence. Numbering here rather than inside the
        translated strings is what stops the digits going stale - they already
        had, after the services and utilities menus were regrouped.
        """
        n = 0
        for it in rows:
            if it.get("sub") or it.get("id") == "back":
                continue
            n += 1
            it["title"] = f"{n}. {it['title']}"
        return rows

    def open_picker(title, rows, target, current):
        # An empty list would make the wrap-around navigation divide by zero.
        if not rows:
            return
        pick_modal.update(active=True, title=title, rows=rows, target=target,
                          current=current)
        pick_modal["selected_idx"] = next(
            (i for i, r in enumerate(rows) if r[0] == current), 0)

    def _act_ids(sys_c=None):
        """Ids of the action tiles, in display order.

        Single source of truth for navigation, drawing and the button handler -
        dispatching on a hard-coded index broke as soon as Java gained a fifth tile.
        """
        if sys_c is None:
            sys_c = game_action_modal.get("sys_code")
        ids = ["PLAY", "DEL"]
        if sys_c in ("JAVA", "J2ME"):
            ids.append("RES")
        ids += ["REGET", "CLOSE"]
        return ids

    def _act_count():
        return len(_act_ids())

    def launch_emulator_game(sys_c, rom_p):
        nonlocal running
        if not rom_p or not os.path.exists(rom_p):
            return False, "Không tìm thấy tập tin ROM!" if state.current_lang == "VI" else "ROM file not found!"

        # Ten thu muc gia lap khong nhat thiet trung ten he, va script mo game
        # khong nhat thiet la launch.sh: Emus/PPSSPP phuc vu Roms/PSP bang
        # launch_performance_vulkan.sh. Doc config.json de biet ca hai, thay vi
        # ghep duong dan roi doan.
        emu_dir, emu_script = resolve_emulator(sys_c)
        if not emu_script:
            if sys_c == "JAVA":
                install_j2me_emulator()
                emu_dir, emu_script = resolve_emulator(sys_c)
            if not emu_script:
                return False, f"Chưa cấu hình Giả lập {sys_c}!" if state.current_lang == "VI" else f"{sys_c} Emulator not configured!"
        
        # Write handoff script for launch.sh to execute cleanly after RetroHub releases all GPU/RAM resources
        try:
            with open("/tmp/launch_game.sh", "w", encoding="utf-8") as f:
                # shlex.quote, not plain double quotes: sh expands $ inside them,
                # and three roms in the catalogue carry one - "Mega Microgame$!"
                # would launch with $! replaced by a job id and the file missing.
                f.write("cd %s\nexec sh %s %s\n" % (
                    shlex.quote(emu_dir), shlex.quote(emu_script), shlex.quote(rom_p)))
            subprocess.call("chmod 755 /tmp/launch_game.sh 2>/dev/null", shell=True)
        except Exception as e:
            print(f"Error writing launch_game.sh: {e}")
            
        # Cleanly quit RetroHub main loop
        running = False
        return True, ""

    key_held_state = {
        "up": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
        "down": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
        "left": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
        "right": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0}
    }

    service_states = {
        "sftp": False,
        "ssh": False,
        "adb": False,
        "mtp": False,
        "streamer": False,
        "wifi_awake": False
    }
    last_service_check_time = 0

    while running:
        now = time.time()

        current_screen = screen_stack[-1]
        selected_idx = selected_indices.get(current_screen, 0)

        # Deferred J2ME install: the panel has already drawn its "installing" line by
        # the time we get here, so blocking for a few seconds no longer looks frozen.
        if j2me_modal.get("pending"):
            j2me_modal["pending"] = False
            ok_inst, msg_inst = install_j2me_emulator(force=True)
            j2me_modal["busy"] = False
            toast_msg = msg_inst
            toast_timer = time.time()
            downloaded_games_list = scan_all_downloaded_games()

        # Smart Service State Polling. Only the services screen reads these, and
        # the six checks cost ~260ms together - a visible stall every 3s on every
        # other screen, for values nothing was looking at.
        if current_screen == "network" and now - last_service_check_time > 3.0:
            service_states["sftp"] = is_sftpgo_running()
            service_states["ssh"] = is_ssh_running()
            service_states["adb"] = is_adb_running()
            service_states["mtp"] = is_mtp_running()
            service_states["streamer"] = is_streamer_running()
            service_states["wifi_awake"] = is_wifi_awake()
            last_service_check_time = now

        # A download that ran in the background finishes with no modal, so report it
        # here or the user would never learn it completed.
        _note = pop_notification()
        if _note:
            _n_title, _n_status = _note
            _n_lbl = tr("dl_done_bg") if _n_status == "success" else tr("dl_failed_bg")
            toast_msg = f"{_n_lbl}: {_n_title}"
            toast_timer = time.time()
            downloaded_games_list = scan_all_downloaded_games()
            rom_games_items_cache = None
            search_results_items_cache = None
            downloaded_items_cache = None
            cached_lib_games_key = None

        sftp_on = service_states["sftp"]
        ssh_on = service_states["ssh"]
        adb_on = service_states["adb"]
        mtp_on = service_states["mtp"]
        streamer_on = service_states["streamer"]
        wifi_awake_on = service_states["wifi_awake"]

        # The library screen draws from this rather than the raw scan, so the
        # system filter reaches the item list, both view modes and the shuffle.
        _lkey = (current_lib_sys, len(downloaded_games_list))
        if cached_lib_games_key != _lkey:
            cached_lib_games_key = _lkey
            cached_lib_games_list = (downloaded_games_list if current_lib_sys == "ALL" else
                                     [g for g in downloaded_games_list
                                      if g.get("sys_code") == current_lib_sys])
            downloaded_items_cache = None
        lib_games_list = cached_lib_games_list

        # Build items for current screen
        items = []

        # HOME: ONLY Language has a right status badge!
        if current_screen == "home":
            header_title = tr("app_title")
            items = [
                {"id": "nav_rom_store_menu", "title": tr("home_item2")},
                {"id": "nav_youtube", "title": tr("home_item_youtube")},
                {"id": "nav_network", "title": tr("home_item1")},
                {"id": "nav_utilities", "title": tr("home_item3")},
                {"id": "nav_donate", "title": tr("home_item_donate")},
                {"id": "nav_settings", "title": tr("home_item_settings")},
                {"id": "exit", "title": tr("home_item5")}
            ]
            # Number from position. The labels used to carry the digit in the
            # translated string, so reordering the menu silently mislabelled it.
            number_items(items)

        # UTILITIES: Only Toggle ON/OFF and Guide [XEM] show badges
        elif current_screen == "utilities":
            header_title = tr("util_title")
            items.append({"id": "nav_splash", "title": tr("util_item_splash")})
            
            is_j2me_installed = is_j2me_runtime_ready()
            j2me_label = "ĐÃ CÓ" if is_j2me_installed else "TỰ CÀI"
            if state.current_lang != "VI":
                j2me_label = "READY" if is_j2me_installed else "AUTO"
            # "Installed" is not the same as "current". Without this the row reads
            # as nothing-to-do while the display row below refuses to open.
            if is_j2me_installed and runtime_is_stale():
                j2me_label = tr("j2me_needs_upgrade")
            items.append({"id": "install_j2me_emu", "title": tr("util_j2me_title"), "label": j2me_label})
            if is_j2me_installed:
                # An in-app update does not carry the runtime, so this app can
                # be sitting on the older emulator, which has no renderer.conf.
                can_render = runtime_supports_renderer()
                items.append({"id": "nav_j2me_render", "title": tr("util_j2me_render"),
                              "label": tr("view") if can_render else tr("j2me_render_old"),
                              "sub": True, "render_ok": can_render})
            
            # NextUI khong dung Emus/<he>/config.json de mo game, nen menu doi
            # giai lap o do khong co tac dung gi.
            if not is_nextui():
                items.append({"id": "nav_core_sys", "title": tr("util_core_title"),
                              "label": tr("view")})

            items.append({"id": "nav_led", "title": tr("util_item_led"),
                          "label": tr("view")})

            # Hai muc chi-doc nam canh nhau: chung tra loi cung mot loai cau hoi.
            items.append({"id": "device_info", "title": tr("device_info"), "label": tr("view")})
            items.append({"id": "storage_status", "title": tr("util_storage_item"), "label": tr("view")})
            number_items(items)
            items.append({"id": "back", "title": tr("back_home")})

        # JAVA DISPLAY: one row per render preset. Pad layout is not here - this
        # build takes it from control_profile.cfg, cycled on the device itself.
        elif current_screen == "j2me_render":
            header_title = tr("j2me_render_title")
            for m in RENDER_MODES:
                items.append({"id": f"j2merender_{m}", "render_mode": m,
                              "title": tr(f"j2me_render_{m}"),
                              "label": tr("j2me_render_cur") if m == j2me_render_mode else ""})
            items.append({"id": "j2me_render_note", "title": tr("j2me_render_note"), "sub": True})
            items.append({"id": "back", "title": tr("back_home")})

        # DOI GIAI LAP: mot dong moi he, hien ten giai lap dang chay. Danh sach
        # duoc doc luc mo man hinh chu khong phai moi khung hinh - no cham vao the.
        elif current_screen == "core_sys":
            header_title = tr("core_sys_title")
            for row in core_sys_rows:
                # Ten giai lap nam trong tieu de chu khong phai badge: badge rong
                # co dinh 130px va ve chu can giua, nen "PPSSPP Vulkan Performance
                # Mode" tran ca hai dau. Tieu de thi co 46 ky tu va tu cat bang "...".
                items.append({"id": f"coresys_{row['code']}", "core_row": row,
                              "title": corepicker.row_title(row),
                              "label": tr("view")})
            if not core_sys_rows:
                items.append({"id": "core_none", "title": tr("core_none"), "sub": True})
            items.append({"id": "core_note", "title": tr("core_note"), "sub": True})
            items.append({"id": "back", "title": tr("back_home")})

        # CHON GIAI LAP: mot dong moi lua chon trong launchlist cua he da chon.
        elif current_screen == "core_pick":
            header_title = tr("core_pick_title")
            row = core_sys_pick or {"options": [], "current_launch": ""}
            for opt in row["options"]:
                items.append({"id": f"corepick_{opt['launch']}", "core_opt": opt,
                              "title": opt.get("name") or opt["launch"],
                              "label": tr("core_cur") if opt["launch"] == row["current_launch"] else ""})
            items.append({"id": "back", "title": tr("back_home")})

        # DEN LED: mot man hinh chinh, mot man hinh chon bo mau.
        elif current_screen == "led":
            header_title = tr("led_title")
            items.append({"id": "led_toggle", "title": tr("led_enable"),
                          "type": "toggle", "state": led_cfg.get("enabled", False)})
            items.append({"id": "nav_led_theme", "title": tr("led_theme"),
                          "label": ledthemes.name(led_cfg.get("theme"),
                                                  state.current_lang)})
            items.append({"id": "led_brightness", "title": tr("led_brightness"),
                          "label": "%d%%" % led_cfg.get("brightness", 60)})
            items.append({"id": "led_speed", "title": tr("led_speed"),
                          "label": tr("led_speed_" +
                                      ledconf.speed_name(led_cfg.get("speed", 1.0)))})
            # Hook chay tren ca NextUI lan firmware goc (xem ledctl.hook_kind).
            # Dong nay chi mo tren mot may khong co CA HAI co che - noi ro
            # thay vi de dong nay bam khong an.
            if ledctl.hook_supported():
                # Trang thai lay tu file hook co that su nam tren dia hay
                # khong, chu khong tu led_cfg["boot"]: exfat-fuse tu choi
                # chmod, nen ban cu cua install_hook() bao that bai trong khi
                # hook da cai va van chay moi lan khoi dong - cong tac o lai
                # TAT va lan bam sau lai goi install thay vi remove.
                items.append({"id": "led_boot", "title": tr("led_boot"),
                              "type": "toggle", "state": ledctl.hook_installed()})
            else:
                items.append({"id": "led_boot_off", "title": tr("led_boot"),
                              "label": tr("led_boot_unavailable"), "is_disabled": True})
            if not led_zones:
                items.append({"id": "led_none", "title": tr("led_no_zones"), "sub": True})
            items.append({"id": "back", "title": tr("back_home")})

        # CHON BO MAU: con tro chinh la nut xem thu - xem xu ly btn_up/btn_down.
        elif current_screen == "led_theme":
            header_title = tr("led_theme_title")
            for th in ledthemes.THEMES:
                items.append({"id": "ledtheme_" + th["id"], "theme_id": th["id"],
                              "title": ledthemes.name(th["id"], state.current_lang),
                              "label": tr("led_cur")
                                       if th["id"] == led_cfg.get("theme") else ""})
            items.append({"id": "back", "title": tr("back")})

        # YOUTUBE 3x2 GRID VIEW
        elif current_screen == "yt_grid":
            if yt_mode == "trending":
                header_title = tr("yt_trending_title")
                items = yt_trending_list or []
            else:
                header_title = f"{tr('yt_search_title')}: \"{yt_search_query}\""
                items = yt_search_results_list or []


        # SETTINGS: things that shape the app itself, kept out of Utilities which is
        # about acting on the device.
        elif current_screen == "settings":
            header_title = tr("settings_title")
            items.append({"id": "toggle_lang", "title": tr("set_lang"),
                          "label": tr("lang_badge"), "is_lang": True})
            items.append({"id": "toggle_autoupdate", "title": tr("set_autoupdate"),
                          "type": "toggle", "state": state.auto_update})
            # Read-only: the quickest way to confirm an update actually landed.
            items.append({"id": "app_version", "title": tr("set_version"),
                          "label": tr("upd_checking") if update_modal["checking"]
                                   else APP_VERSION})
            items.append({"id": "nav_author", "title": tr("set_author"),
                          "label": tr("view")})
            items.append({"id": "nav_chat", "title": tr("set_chat"),
                          "label": tr("view")})
            items.append({"id": "back", "title": tr("back_home")})

        # BOOT SPLASH MANAGER: Scanned images + Browse File + Restore default
        elif current_screen == "splash_manager":
            header_title = tr("splash_title")
            items.append({"id": "splash_restore", "title": tr("splash_restore_item"), "is_restore": True})
            items.append({"id": "splash_browse_sd", "title": tr("splash_browse_item"), "is_browse": True})
            for i, simg in enumerate(splash_images_list):
                items.append({
                    "id": f"splash_{i}",
                    "title": simg["filename"],
                    "path": simg["path"],
                    "size_str": simg["size_str"],
                    "dir": simg["dir"],
                    "img_data": simg
                })
            items.append({"id": "back", "title": tr("back")})

        # FILE BROWSER SCREEN (SELECT ANY IMAGE FROM SDCARD)
        elif current_screen == "file_browser":
            header_title = tr("fb_title")
            # Re-scan only when the folder changes. This ran on every frame, so
            # browsing a folder meant a full directory walk sixty times a second.
            if fb_scanned_path != fb_current_path:
                fb_items = scan_directory_for_images(fb_current_path)
                fb_scanned_path = fb_current_path
            if not fb_items:
                items.append({"id": "fb_empty", "title": tr("fb_empty"), "is_disabled": True})
            else:
                items = fb_items

        # BOOT SPLASH FULLSCREEN PREVIEW
        elif current_screen == "splash_preview":
            header_title = tr("splash_preview_title")

        # ROM STORE MENU: 1. Thư viện -> 2. Tìm kiếm -> 3. Kho game online -> 4. Quản lý tải -> 5. Quay lại
        elif current_screen == "rom_store_menu":
            header_title = tr("store_title")
            items = [
                {"id": "nav_downloaded", "title": tr("store_item_library")},
                {"id": "nav_search_global", "title": tr("store_item_search")},
                {"id": "nav_online_categories", "title": tr("store_item_online")},
                {"id": "nav_dl_manager", "title": tr("store_item_dl_mgr")},
                {"id": "back", "title": tr("back_home")}
            ]

        # ONLINE CATEGORIES: 1. Việt Hóa -> 2. Top Game -> 3. Game Java -> 4. ROM Hacks -> 5. Tất cả -> 6. Retrostic -> 7. Archive -> 8. Quay lại
        elif current_screen == "rom_online_categories":
            header_title = tr("online_cat_title")
            items = [
                {"id": "src_viet", "title": tr("store_src_viet")},
                {"id": "src_hits", "title": tr("store_src_hits")},
                {"id": "src_java", "title": tr("store_src_java")},
                {"id": "src_hack", "title": tr("store_src_hack")},
                {"id": "src_all", "title": tr("store_src_all")},
                {"id": "src_retrostic", "title": tr("store_src_retrostic")},
                {"id": "src_archive", "title": tr("store_src_archive")},
                {"id": "back", "title": tr("back_store_menu")}
            ]

        # ROM SOURCE SYSTEMS SELECTION (CHỌN HỆ MÁY)
        # J2ME SHELVES: the source groups its jars into topic folders, and 2713
        # titles in one flat list is unusable.
        elif current_screen == "rom_java_cats":
            header_title = tr("java_cat_title")
            if not java_cats_cache:
                java_cats_cache = get_java_category_list()
            for code, cnt in java_cats_cache:
                label = java_cat_label(code)
                items.append({"id": f"javacat_{code}", "java_cat": code,
                              "title": f"• {label} ({cnt})"})
            items.append({"id": "back", "title": tr("back_store_menu")})

        elif current_screen == "rom_source_systems":
            src_titles = {
                "VIET": "GAME VIỆT HÓA" if state.current_lang == "VI" else "VIETNAMESE GAMES",
                "HACK": "KHO ROM HACKS & MODS" if state.current_lang == "VI" else "ROM HACKS & MODS",
                "HITS": "TOP GAME HAY" if state.current_lang == "VI" else "TOP GAMES",
                "JAVA": "GAME JAVA (J2ME)" if state.current_lang == "VI" else "JAVA GAMES",
                "ALL": "TẤT CẢ HỆ MÁY" if state.current_lang == "VI" else "ALL SYSTEMS",
                "RETROSTIC": "NGUỒN RETROSTIC CDN" if state.current_lang == "VI" else "RETROSTIC CDN",
                "ARCHIVE": "NGUỒN INTERNET ARCHIVE" if state.current_lang == "VI" else "INTERNET ARCHIVE"
            }
            s_name_header = src_titles.get(current_source, "KHO GAME")
            header_title = f"{s_name_header} - CHỌN HỆ MÁY" if state.current_lang == "VI" else f"{s_name_header} - SELECT SYSTEM"

            if src_sys_cache_key != current_source:
                src_sys_cache = get_source_systems_list(current_source)
                src_sys_cache_key = current_source
            sys_list = src_sys_cache
            for sc, count in sys_list:
                if sc == "ALL":
                    items.append({"id": "sys_ALL", "sys_code": "ALL", "title": f"• {tr('source_systems_all')} ({count} Games)"})
                else:
                    disp_name = get_system_display_name(sc)
                    items.append({"id": f"sys_{sc}", "sys_code": sc, "title": f"• {disp_name} ({count} Games)"})
            items.append({"id": "back", "title": "< Quay lại danh mục" if state.current_lang == "VI" else "< Back to Categories"})

        # DOWNLOAD MANAGER SCREEN
        elif current_screen == "download_manager":
            header_title = tr("dl_mgr_title")
            
            is_dl_running = dl_state.get("active") or dl_state.get("status") in ("downloading", "extracting")
            if is_dl_running:
                items.append({
                    "id": "dl_active_card",
                    "title": f"[{dl_state['sys_code']}] {dl_state['title']}",
                    "is_active_dl": True
                })
            else:
                items.append({
                    "id": "dl_no_active",
                    "title": tr("dl_no_active"),
                    "is_disabled": True
                })
                
            q_items = queued_items()
            for q_i, (q_sys, q_game) in enumerate(q_items, start=1):
                items.append({
                    "id": f"dl_queued_{q_i}",
                    "title": f"{q_i}. [{q_game.get('sys_code') or q_sys}] {q_game.get('title', '?')}",
                    "label": tr("dl_queue_badge"),
                    "sub": True,
                    "is_disabled": True
                })
            if q_items:
                items.append({"id": "dl_clear_queue", "title": tr("dl_clear_queue"),
                              "label": str(len(q_items))})

            items.append({"id": "back", "title": tr("back_store_menu")})

        # DOWNLOADED GAMES: List items
        elif current_screen == "downloaded_games":
            _lib_tag = "" if current_lib_sys == "ALL" else f" - {current_lib_sys}"
            header_title = f"{tr('dl_view_title')}{_lib_tag} [{len(lib_games_list)}]"
            _dl_key = (current_lib_sys, len(lib_games_list), state.current_lang)
            if downloaded_items_cache is None or downloaded_items_key != _dl_key:
                downloaded_items_key = _dl_key
                built_items = []
                for idx, dg in enumerate(lib_games_list):
                    sz_str = dg.get("size_str", "")
                    sz_disp = f" [{sz_str}]" if sz_str and sz_str not in ("TOPO SHOP", "TOPO") else ""
                    built_items.append({
                        "id": f"dl_{idx}",
                        "game_idx": idx,
                        "title": f"{idx+1}. [{dg['sys_code']}] {dg['title']}{sz_disp}",
                        "game_data": dg
                    })
                if not built_items:
                    built_items.append({"id": "empty", "title": tr("empty_dl")})
                built_items.append({"id": "back", "title": tr("back_store_menu")})
                downloaded_items_cache = built_items
            items = downloaded_items_cache

        # NETWORK SERVICES: Only Toggles and View Guide / Info [XEM] show badges
        elif current_screen == "network":
            header_title = tr("net_title")
            items.append({"id": "sftp_toggle", "title": tr("sftp_item"), "type": "toggle", "state": sftp_on})
            if sftp_on:
                items.append({"id": "sftp_guide", "title": tr("sftp_guide"), "label": tr("view"), "sub": True})
            items.append({"id": "ssh_toggle", "title": tr("ssh_item"), "type": "toggle", "state": ssh_on})
            if ssh_on:
                items.append({"id": "ssh_guide", "title": tr("ssh_guide"), "label": tr("view"), "sub": True})
            items.append({"id": "adb_toggle", "title": tr("adb_item"), "type": "toggle", "state": adb_on})
            items.append({"id": "mtp_toggle", "title": tr("mtp_item"), "type": "toggle", "state": mtp_on})
            # The streamer is a service you switch on like the rest, so it belongs
            # here rather than among the tools.
            if stream_supported():
                items.append({"id": "stream_toggle", "title": tr("stream_item"), "type": "toggle", "state": streamer_on})
                if streamer_on:
                    items.append({"id": "stream_guide", "title": tr("stream_guide"), "label": tr("view"), "sub": True})
            items.append({"id": "wifi_ps_toggle", "title": tr("wifi_ps_item"), "type": "toggle", "state": wifi_awake_on})
            number_items(items)
            items.append({"id": "back", "title": tr("back_home")})

        # ROM SYSTEMS LIST (LEGACY/FALLBACK)
        elif current_screen == "rom_systems":
            header_title = tr("sys_select_title")
            for code, cnt in get_source_systems_list("ALL"):
                if code == "ALL":
                    continue
                items.append({"id": f"sys_{code}", "sys_code": code,
                              "title": f"{get_system_display_name(code)}  ({cnt})"})
            items.append({"id": "back", "title": tr("back_store_menu")})

        # ROM GAMES LIST: Show status badge [ĐÃ CÓ] / [TẢI]
        elif current_screen == "rom_games":
            _gkey = (current_source, current_rom_system, state.rom_sort_mode, current_java_cat)
            if _gkey != rom_games_cache_key:
                rom_games_cache = get_games_for_view(
                    current_source, current_rom_system,
                    category=current_java_cat if current_source == "JAVA" else None)
                rom_games_cache_key = _gkey
                rom_games_items_cache = None
            games_list = rom_games_cache
            total_g = len(games_list)
            cur_pos = selected_idx + 1 if total_g > 0 else 0

            src_titles = {
                "VIET": "Game Việt Hóa" if state.current_lang == "VI" else "Vietnamese Games",
                "HACK": "ROM Hacks & Mods" if state.current_lang == "VI" else "ROM Hacks",
                "HITS": "Top 100 Game" if state.current_lang == "VI" else "Top 100 Games",
                "JAVA": "Game Java (J2ME)" if state.current_lang == "VI" else "Java Games",
                "RETROSTIC": "Retrostic CDN" if state.current_lang == "VI" else "Retrostic CDN",
                "ARCHIVE": "Internet Archive" if state.current_lang == "VI" else "Internet Archive",
                "ALL": "Kho Game Online" if state.current_lang == "VI" else "Online Games"
            }

            sys_disp = get_system_display_name(current_rom_system) if current_rom_system != "ALL" else ("Tất cả hệ máy" if state.current_lang == "VI" else "All Systems")
            s_name = src_titles.get(current_source, "Game")

            if current_source == "HITS":
                header_title = f"Top 100 Game {sys_disp} [{cur_pos}/{total_g}]"
            elif current_source == "HACK":
                header_title = f"ROM Hacks {sys_disp} [{cur_pos}/{total_g}]"
            elif current_source == "JAVA":
                _jc = "" if current_java_cat == "ALL" else " - " + java_cat_label(current_java_cat)
                header_title = f"Game Java J2ME{_jc} [{cur_pos}/{total_g}]"
            elif current_source == "VIET":
                header_title = f"Game Việt Hóa {sys_disp} [{cur_pos}/{total_g}]"
            else:
                if current_rom_system == "ALL":
                    header_title = f"{s_name} - Tất cả [{cur_pos}/{total_g}]"
                else:
                    header_title = f"{sys_disp} [{cur_pos}/{total_g}]"

            _items_key = (_gkey, state.current_lang, len(games_list))
            if rom_games_items_cache is None or rom_games_items_key != _items_key:
                rom_games_items_key = _items_key
                sys_local_map = {}
                def _get_sys_local(sc):
                    if sc not in sys_local_map:
                        lf = get_local_cache(sc)
                        lb = {os.path.splitext(f)[0]: p for f, p in lf.items()}
                        sys_local_map[sc] = (lf, lb)
                    return sys_local_map[sc]

                built_items = []
                for idx, g in enumerate(games_list):
                    fn = os.path.basename(str(g.get("filename", "")).replace("\\", "/"))
                    g_sys = g.get("sys_code") or (current_rom_system if current_rom_system != "ALL" else "ROM")
                    if g_sys in ("VIET", "HITS", "TOPO", "ARCHIVE", "ALL"):
                        g_sys = g.get("sys_code") or "ROM"

                    rom_dir = state.catalogs.get(g_sys, {}).get("rom_dir", f"{SDCARD_PATH}/Roms/{g_sys}")
                    local_files, local_basenames = _get_sys_local(g_sys)
                    fn = resolve_local_name(fn, g_sys, local_files)
                    base_name = os.path.splitext(fn)[0]

                    if fn in local_files:
                        is_downloaded = True
                        found_rom_path = local_files[fn]
                    elif base_name in local_basenames:
                        is_downloaded = True
                        found_rom_path = local_basenames[base_name]
                    else:
                        is_downloaded = False
                        found_rom_path = None

                    if is_downloaded:
                        badge_lbl = tr("have_badge")
                    else:
                        _dst = download_state_for(g)
                        badge_lbl = (tr("dling_badge") if _dst == "downloading"
                                     else tr("dl_queue_badge") if _dst == "queued"
                                     else tr("download_badge"))

                    g_title = g.get("title", "Game")
                    disp_title = f"{idx+1}. [{g_sys}] {g_title}"

                    dl_count = g.get("download_count", 0)
                    if dl_count and dl_count > 0:
                        dl_str = f"{dl_count/1000:.1f}k" if dl_count >= 1000 else str(dl_count)
                        disp_title += f" [{dl_str} dl]"
                    elif g.get("file_size_str"):
                        disp_title += f" [{g.get('file_size_str')}]"

                    built_items.append({
                        "id": f"game_{idx}",
                        "game_idx": idx,
                        "game_info": g,
                        "sys_code": g_sys,
                        "title": disp_title,
                        "label": badge_lbl,
                        "downloaded": is_downloaded,
                        "rom_path": found_rom_path if found_rom_path else os.path.join(rom_dir, fn),
                        "img_path": None
                    })

                if current_source == "VIET":
                    built_items.append({"id": "back", "title": tr("back_store_menu")})
                else:
                    built_items.append({"id": "back", "title": tr("back_systems")})

                rom_games_items_cache = built_items

            items = rom_games_items_cache

        # SEARCH RESULTS: Show status badge [ĐÃ CÓ] / [TẢI]
        elif current_screen == "search_results":
            cur_filter_sys = sys_keys_list[search_sys_idx]
            header_title = f"{tr('search_res_title')}: '{search_query}' [{len(search_results_list)}]"
            _sr_key = (search_query, search_sys_idx, len(search_results_list), state.current_lang)
            if search_results_items_cache is None or search_results_items_key != _sr_key:
                search_results_items_key = _sr_key
                sys_local_map = {}
                def _get_sys_local(sc):
                    if sc not in sys_local_map:
                        lf = get_local_cache(sc)
                        lb = {os.path.splitext(f)[0]: p for f, p in lf.items()}
                        sys_local_map[sc] = (lf, lb)
                    return sys_local_map[sc]

                built_items = []
                for idx, r in enumerate(search_results_list):
                    g = r["game_info"]
                    s_code = r["sys_code"]
                    rom_dir = state.catalogs.get(s_code, {}).get("rom_dir", f"{SDCARD_PATH}/Roms/{s_code}")
                    local_files, local_basenames = _get_sys_local(s_code)
                    fn = os.path.basename(str(g.get("filename", "")).replace("\\", "/"))
                    fn = resolve_local_name(fn, s_code, local_files)
                    base_name = os.path.splitext(fn)[0]

                    if fn in local_files:
                        is_downloaded = True
                        found_rom_path = local_files[fn]
                    elif base_name in local_basenames:
                        is_downloaded = True
                        found_rom_path = local_basenames[base_name]
                    else:
                        is_downloaded = False
                        found_rom_path = None

                    if is_downloaded:
                        badge_lbl = tr("have_badge")
                    else:
                        _dst = download_state_for(g)
                        badge_lbl = (tr("dling_badge") if _dst == "downloading"
                                     else tr("dl_queue_badge") if _dst == "queued"
                                     else tr("download_badge"))
                    g_title = g.get("title", "Game")
                    disp_title = f"{idx+1}. [{s_code}] {g_title}"
                    sz = (g.get("file_size_str") or g.get("size") or "").strip()
                    if sz and sz not in ("TOPO SHOP", "TOPO"):
                        disp_title += f" [{sz}]"

                    built_items.append({
                        "id": f"res_{idx}",
                        "game_info": g,
                        "sys_code": s_code,
                        "title": disp_title,
                        "label": badge_lbl,
                        "downloaded": is_downloaded,
                        "rom_path": found_rom_path if found_rom_path else os.path.join(rom_dir, fn),
                        "img_path": None
                    })
                if not built_items:
                    built_items.append({"id": "empty", "title": tr("no_res")})
                built_items.append({"id": "back", "title": tr("back_search")})
                search_results_items_cache = built_items

            items = search_results_items_cache

        # Bounds check
        if current_screen not in ("yt_search_input", "search_input"):
            if selected_idx >= len(items):
                selected_idx = len(items) - 1
            if selected_idx < 0:
                selected_idx = 0
            selected_indices[current_screen] = selected_idx

        # ----------------------------------------------------------------------
        # EVENT HANDLING - PRECISE PHYSICAL BUTTON MAPPING
        # ----------------------------------------------------------------------
        btn_up = False
        btn_down = False
        btn_left = False
        btn_right = False
        btn_l1 = False
        btn_r1 = False
        btn_a = False
        btn_b = False
        btn_x = False
        btn_y = False
        btn_start = False
        btn_f1 = False

        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(event) != 0:
            etype = event.type

            if etype == sdl2.SDL_QUIT:
                running = False

            elif etype == sdl2.SDL_CONTROLLERBUTTONDOWN:
                cbtn = event.cbutton.button
                if cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                    btn_up = True
                    key_held_state["up"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                    btn_down = True
                    key_held_state["down"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                    btn_left = True
                    key_held_state["left"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                    btn_right = True
                    key_held_state["right"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
                    btn_l1 = True
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
                    btn_r1 = True
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_B: # Physical A (East)
                    btn_a = True
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_A: # Physical B (South)
                    btn_b = True
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_Y: # Physical X (North)
                    btn_x = True
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_X: # Physical Y (West)
                    btn_y = True
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_START:
                    btn_start = True
                elif cbtn in [sdl2.SDL_CONTROLLER_BUTTON_BACK, sdl2.SDL_CONTROLLER_BUTTON_GUIDE]:
                    btn_f1 = True

            elif etype == sdl2.SDL_CONTROLLERBUTTONUP:
                cbtn = event.cbutton.button
                if cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP: key_held_state["up"]["pressed"] = False
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN: key_held_state["down"]["pressed"] = False
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT: key_held_state["left"]["pressed"] = False
                elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT: key_held_state["right"]["pressed"] = False

            elif etype == sdl2.SDL_CONTROLLERAXISMOTION:
                val = event.caxis.value
                if event.caxis.axis == sdl2.SDL_CONTROLLER_AXIS_LEFTY:
                    if val < -15000:
                        if not key_held_state["up"]["pressed"]:
                            btn_up = True
                            key_held_state["up"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["down"]["pressed"] = False
                    elif val > 15000:
                        if not key_held_state["down"]["pressed"]:
                            btn_down = True
                            key_held_state["down"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["up"]["pressed"] = False
                    elif abs(val) <= 10000:
                        key_held_state["up"]["pressed"] = False
                        key_held_state["down"]["pressed"] = False

                elif event.caxis.axis == sdl2.SDL_CONTROLLER_AXIS_LEFTX:
                    if val < -15000:
                        if not key_held_state["left"]["pressed"]:
                            btn_left = True
                            key_held_state["left"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["right"]["pressed"] = False
                    elif val > 15000:
                        if not key_held_state["right"]["pressed"]:
                            btn_right = True
                            key_held_state["right"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["left"]["pressed"] = False
                    elif abs(val) <= 10000:
                        key_held_state["left"]["pressed"] = False
                        key_held_state["right"]["pressed"] = False

            elif not has_controller and etype == sdl2.SDL_JOYBUTTONDOWN:
                jbtn = event.jbutton.button
                if jbtn == 1:
                    btn_a = True
                elif jbtn == 0:
                    btn_b = True
                elif jbtn in [8, 11, 13]:
                    btn_up = True
                    key_held_state["up"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif jbtn in [9, 12, 14]:
                    btn_down = True
                    key_held_state["down"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif jbtn in [4, 6]:
                    btn_l1 = True
                elif jbtn in [5, 7]:
                    btn_r1 = True
                elif jbtn == 3: # Physical X
                    btn_x = True
                elif jbtn == 2: # Physical Y
                    btn_y = True
                elif jbtn == 10:
                    btn_f1 = True
                elif jbtn == 9:
                    btn_start = True

            elif not has_controller and etype == sdl2.SDL_JOYBUTTONUP:
                jbtn = event.jbutton.button
                if jbtn in [8, 11, 13]: key_held_state["up"]["pressed"] = False
                elif jbtn in [9, 12, 14]: key_held_state["down"]["pressed"] = False

            elif etype == sdl2.SDL_JOYAXISMOTION:
                j_axis = event.jaxis.axis
                j_val = event.jaxis.value
                if j_axis == 1: # Left Y axis
                    if j_val < -15000:
                        if not key_held_state["up"]["pressed"]:
                            btn_up = True
                            key_held_state["up"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["down"]["pressed"] = False
                    elif j_val > 15000:
                        if not key_held_state["down"]["pressed"]:
                            btn_down = True
                            key_held_state["down"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["up"]["pressed"] = False
                    elif abs(j_val) <= 10000:
                        key_held_state["up"]["pressed"] = False
                        key_held_state["down"]["pressed"] = False

                elif j_axis == 0: # Left X axis
                    if j_val < -15000:
                        if not key_held_state["left"]["pressed"]:
                            btn_left = True
                            key_held_state["left"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["right"]["pressed"] = False
                    elif j_val > 15000:
                        if not key_held_state["right"]["pressed"]:
                            btn_right = True
                            key_held_state["right"] = {"pressed": True, "start_time": now, "last_repeat": now}
                            key_held_state["left"]["pressed"] = False
                    elif abs(j_val) <= 10000:
                        key_held_state["left"]["pressed"] = False
                        key_held_state["right"]["pressed"] = False

            elif etype == sdl2.SDL_JOYHATMOTION:
                hat_val = event.jhat.value
                if hat_val & sdl2.SDL_HAT_UP:
                    if not key_held_state["up"]["pressed"]:
                        btn_up = True
                        key_held_state["up"] = {"pressed": True, "start_time": now, "last_repeat": now}
                else:
                    key_held_state["up"]["pressed"] = False

                if hat_val & sdl2.SDL_HAT_DOWN:
                    if not key_held_state["down"]["pressed"]:
                        btn_down = True
                        key_held_state["down"] = {"pressed": True, "start_time": now, "last_repeat": now}
                else:
                    key_held_state["down"]["pressed"] = False

                if hat_val & sdl2.SDL_HAT_LEFT:
                    if not key_held_state["left"]["pressed"]:
                        btn_left = True
                        key_held_state["left"] = {"pressed": True, "start_time": now, "last_repeat": now}
                else:
                    key_held_state["left"]["pressed"] = False

                if hat_val & sdl2.SDL_HAT_RIGHT:
                    if not key_held_state["right"]["pressed"]:
                        btn_right = True
                        key_held_state["right"] = {"pressed": True, "start_time": now, "last_repeat": now}
                else:
                    key_held_state["right"]["pressed"] = False

            elif etype == sdl2.SDL_KEYDOWN:
                sym = event.key.keysym.sym
                if sym in [sdl2.SDLK_UP, sdl2.SDLK_w]:
                    btn_up = True
                    key_held_state["up"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif sym in [sdl2.SDLK_DOWN, sdl2.SDLK_s]:
                    btn_down = True
                    key_held_state["down"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif sym in [sdl2.SDLK_LEFT, sdl2.SDLK_a]:
                    btn_left = True
                    key_held_state["left"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif sym in [sdl2.SDLK_RIGHT, sdl2.SDLK_d]:
                    btn_right = True
                    key_held_state["right"] = {"pressed": True, "start_time": now, "last_repeat": now}
                elif sym in [sdl2.SDLK_PAGEUP, sdl2.SDLK_q]:
                    btn_l1 = True
                elif sym in [sdl2.SDLK_PAGEDOWN, sdl2.SDLK_e]:
                    btn_r1 = True
                elif sym in [sdl2.SDLK_RETURN, sdl2.SDLK_SPACE, sdl2.SDLK_z, sdl2.SDLK_j]:
                    btn_a = True
                elif sym in [sdl2.SDLK_ESCAPE, sdl2.SDLK_BACKSPACE, sdl2.SDLK_k]:
                    btn_b = True
                elif sym == sdl2.SDLK_x:
                    btn_x = True
                elif sym == sdl2.SDLK_y:
                    btn_y = True
                elif sym in [sdl2.SDLK_F1, sdl2.SDLK_m]:
                    btn_f1 = True
                elif current_screen in ("search_input", "yt_search_input"):
                    if sym == sdl2.SDLK_BACKSPACE:
                        if current_screen == "yt_search_input":
                            yt_input_text = yt_input_text[:-1]
                        else:
                            search_query = search_query[:-1]
                    elif sym == sdl2.SDLK_RETURN:
                        btn_start = True

            elif etype == sdl2.SDL_KEYUP:
                sym = event.key.keysym.sym
                if sym in [sdl2.SDLK_UP, sdl2.SDLK_w]: key_held_state["up"]["pressed"] = False
                elif sym in [sdl2.SDLK_DOWN, sdl2.SDLK_s]: key_held_state["down"]["pressed"] = False
                elif sym in [sdl2.SDLK_LEFT, sdl2.SDLK_a]: key_held_state["left"]["pressed"] = False
                elif sym in [sdl2.SDLK_RIGHT, sdl2.SDLK_d]: key_held_state["right"]["pressed"] = False

        # Smooth Hold-to-Scroll Autorepeat (Initial delay 260ms, repeat every 75ms)
        HOLD_DELAY = 0.26
        REPEAT_INTERVAL = 0.075
        for k_dir, k_st in key_held_state.items():
            if k_st["pressed"]:
                if now - k_st["start_time"] > HOLD_DELAY:
                    if now - k_st["last_repeat"] > REPEAT_INTERVAL:
                        if k_dir == "up": btn_up = True
                        elif k_dir == "down": btn_down = True
                        elif k_dir == "left": btn_left = True
                        elif k_dir == "right": btn_right = True
                        k_st["last_repeat"] = now

        if btn_up or btn_down or btn_left or btn_right or btn_a or btn_b or btn_x or btn_y or btn_start or btn_f1 or btn_l1 or btn_r1:
            last_user_activity_time = now

        # ----------------------------------------------------------------------
        # PROCESS UI LOGIC
        # ----------------------------------------------------------------------
        if dl_state["active"] and not dl_state.get("is_background", False):
            if dl_state["status"] in ("downloading", "extracting"):
                if btn_b or btn_y:
                    dl_state["is_background"] = True
                    toast_msg = tr("dl_bg_toast")
                    toast_timer = time.time()
                elif btn_x:
                    cancel_active_download()
                    toast_msg = tr("dl_cancelled_toast")
                    toast_timer = time.time()

            elif dl_state["status"] == "success":
                if btn_left or btn_up:
                    dl_state["selected_opt"] = 0
                elif btn_right or btn_down:
                    dl_state["selected_opt"] = 1
                elif btn_b:
                    dl_state["active"] = False
                    dl_state["status"] = "idle"
                    if start_next_queued():
                        toast_msg = tr("dl_queue_next")
                        toast_timer = time.time()
                elif btn_a:
                    opt = dl_state["selected_opt"]
                    rom_p = dl_state.get("extracted_rom_path", "")
                    sys_c = dl_state.get("sys_code", "")
                    dl_state["active"] = False
                    dl_state["status"] = "idle"

                    launched = False
                    if opt == 0 and rom_p and os.path.exists(rom_p):
                        ok, err_msg = launch_emulator_game(sys_c, rom_p)
                        launched = ok
                        if not ok:
                            toast_msg = err_msg
                            toast_timer = time.time()

                    # Pointless to start a queued download when the app is about to
                    # hand off to the emulator and exit.
                    if not launched and start_next_queued():
                        toast_msg = tr("dl_queue_next")
                        toast_timer = time.time()

            elif dl_state["status"] in ("error", "cancelled"):
                if btn_b or btn_a or btn_x or btn_y or btn_start or btn_f1:
                    dl_state["active"] = False
                    dl_state["status"] = "idle"
                    dl_state["msg"] = ""
                    if start_next_queued():
                        toast_msg = tr("dl_queue_next")
                        toast_timer = time.time()
        elif qr_modal["active"]:
            _np = len(qr_modal["pages"])
            if (btn_l1 or btn_left) and _np > 1:
                qr_modal["page"] = (qr_modal["page"] - 1) % _np
            elif (btn_r1 or btn_right) and _np > 1:
                qr_modal["page"] = (qr_modal["page"] + 1) % _np
            elif btn_a or btn_b:
                qr_modal["active"] = False
        elif pick_modal["active"]:
            rows = pick_modal["rows"]
            if btn_up:
                pick_modal["selected_idx"] = (pick_modal["selected_idx"] - 1) % len(rows)
            elif btn_down:
                pick_modal["selected_idx"] = (pick_modal["selected_idx"] + 1) % len(rows)
            elif btn_b or btn_f1:
                pick_modal["active"] = False
            elif btn_a:
                chosen = rows[pick_modal["selected_idx"]][0]
                target = pick_modal["target"]
                pick_modal["active"] = False
                if target == "lib_sys":
                    current_lib_sys = chosen
                    # The cursor indexes the filtered list, so a narrower filter
                    # would leave it pointing past the end.
                    selected_idx = 0
                    selected_indices["downloaded_games"] = 0
                    scroll_offsets["downloaded_games"] = 0
                    toast_msg = (tr("lib_filter_all") if chosen == "ALL"
                                 else f"{tr('lib_filter_on')}{chosen}")
                    toast_timer = time.time()
                elif target == "search_sys":
                    search_sys_idx = sys_keys_list.index(chosen) if chosen in sys_keys_list else 0
                elif target == "search_src":
                    search_source = chosen
        elif update_modal["active"]:
            if update_modal["busy"]:
                # The install thread owns the modal; swallow input so a stray
                # press cannot dismiss it while files are being replaced.
                pass
            elif update_modal["failed"]:
                if btn_a or btn_b:
                    update_modal["active"] = False
            elif btn_left:
                n_opts = len(update_modal_labels())
                update_modal["selected_opt"] = (update_modal["selected_opt"] - 1) % n_opts
            elif btn_right:
                n_opts = len(update_modal_labels())
                update_modal["selected_opt"] = (update_modal["selected_opt"] + 1) % n_opts
            elif btn_b:
                update_modal["active"] = False
            elif btn_a:
                labels = update_modal_labels()
                opt = update_modal["selected_opt"]
                # cat_only khong co nut skip (xem update_modal_labels), nen
                # "opt == 1" o day chi con dung nghia "bo qua ban nay" khi
                # dang o modal 3 nut - o modal 2 nut, opt == 1 la "De sau".
                if not update_modal["cat_only"] and opt == 1:
                    skip_version(update_modal["manifest"]["version"])
                    update_modal["active"] = False
                    toast_msg = tr("upd_skipped")
                    toast_timer = time.time()
                elif opt == len(labels) - 1:
                    update_modal["active"] = False
                else:
                    update_modal["busy"] = True
                    update_modal["status"] = tr("upd_downloading")
                    threading.Thread(target=run_update, daemon=True).start()
        elif pre_download_modal["active"]:
            if btn_left or btn_up:
                pre_download_modal["selected_opt"] = 0
            elif btn_right or btn_down:
                pre_download_modal["selected_opt"] = 1
            elif btn_b:
                pre_download_modal["active"] = False
            elif btn_a:
                opt = pre_download_modal["selected_opt"]
                g_info = pre_download_modal["game_info"]
                sys_c = pre_download_modal["sys_code"]
                pre_download_modal["active"] = False
                if opt == 0:
                    q_msg = enqueue_download(sys_c, g_info)
                    if q_msg:
                        toast_msg = q_msg
                        toast_timer = time.time()
        elif alphabet_modal["active"]:
            if btn_left:
                alphabet_modal["selected_idx"] = (alphabet_modal["selected_idx"] - 1) % 27
            elif btn_right:
                alphabet_modal["selected_idx"] = (alphabet_modal["selected_idx"] + 1) % 27
            elif btn_up:
                alphabet_modal["selected_idx"] = (alphabet_modal["selected_idx"] - 9) % 27
            elif btn_down:
                alphabet_modal["selected_idx"] = (alphabet_modal["selected_idx"] + 9) % 27
            elif btn_b or btn_x:
                alphabet_modal["active"] = False
            elif btn_a:
                sel_let = alphabet_modal["letters"][alphabet_modal["selected_idx"]]
                if sel_let in alphabet_modal["available_map"]:
                    target_idx = alphabet_modal["available_map"][sel_let]
                    # Index duoc tinh theo thu tu A-Z, nen danh sach phai ve A-Z
                    # thi no moi tro dung game. Doi khoa cache khien man hinh nap
                    # lai dung thu tu do ngay khung hinh sau.
                    switched = alphabet_modal.get("needs_alpha_sort", False)
                    if switched:
                        state.rom_sort_mode = "alpha"
                        rom_games_items_cache = None
                    selected_idx = target_idx
                    selected_indices["rom_games"] = target_idx
                    scroll_offsets["rom_games"] = target_idx
                    alphabet_modal["active"] = False
                    cnt = alphabet_modal["counts_map"].get(sel_let, 0)
                    unit = "game" if state.current_lang == "VI" else "games"
                    toast_msg = f"{tr('alpha_jump_toast')}{sel_let} ({cnt} {unit})"
                    if switched:
                        toast_msg += tr("alpha_jump_sorted")
                    toast_timer = time.time()
                else:
                    toast_msg = f"{tr('alpha_no_games')}'{sel_let}'"
                    toast_timer = time.time()

        elif j2me_modal["active"]:
            if btn_b or btn_x:
                if not j2me_modal["busy"]:
                    j2me_modal["active"] = False
            elif btn_a and not j2me_modal["busy"]:
                j2me_modal["busy"] = True
                j2me_modal["pending"] = True

        elif res_modal["active"]:
            if btn_up or btn_left:
                res_modal["selected_idx"] = (res_modal["selected_idx"] - 1) % len(RESOLUTIONS)
            elif btn_down or btn_right:
                res_modal["selected_idx"] = (res_modal["selected_idx"] + 1) % len(RESOLUTIONS)
            elif btn_b or btn_x:
                res_modal["active"] = False
            elif btn_a:
                pick = RESOLUTIONS[res_modal["selected_idx"]]
                cur_path = game_action_modal.get("rom_path", "")
                res_modal["active"] = False
                if resolution_of_path(cur_path) != pick:
                    new_path = move_to_resolution(cur_path, pick)
                    if new_path:
                        game_action_modal["rom_path"] = new_path
                        downloaded_games_list = scan_all_downloaded_games()
                        toast_msg = f"{tr('res_changed')} {pretty_resolution(pick)}"
                    else:
                        toast_msg = "Không di chuyển được" if state.current_lang == "VI" else "Could not move file"
                    toast_timer = time.time()

        elif game_action_modal["active"]:
            if btn_left:
                game_action_modal["selected_opt"] = (game_action_modal["selected_opt"] - 1) % _act_count()
            elif btn_right:
                game_action_modal["selected_opt"] = (game_action_modal["selected_opt"] + 1) % _act_count()
            elif btn_up:
                game_action_modal["selected_opt"] = (game_action_modal["selected_opt"] - 1) % _act_count()
            elif btn_down:
                game_action_modal["selected_opt"] = (game_action_modal["selected_opt"] + 1) % _act_count()
            elif btn_b:
                game_action_modal["active"] = False
            elif btn_a:
                opt = game_action_modal["selected_opt"]
                g_info = game_action_modal["game_info"]
                rom_p = game_action_modal.get("rom_path", "")
                sys_c = game_action_modal.get("sys_code", current_rom_system)
                game_action_modal["active"] = False

                act = _act_ids(sys_c)[opt] if opt < len(_act_ids(sys_c)) else "CLOSE"
                if act == "PLAY":
                    ok, err_msg = launch_emulator_game(sys_c, rom_p)
                    if not ok:
                        toast_msg = err_msg
                        toast_timer = time.time()

                elif act == "DEL":
                    if rom_p and os.path.exists(rom_p):
                        try:
                            os.remove(rom_p)
                            toast_msg = tr("deleted_toast")
                            toast_timer = time.time()
                            if current_screen == "downloaded_games":
                                downloaded_games_list = scan_all_downloaded_games()
                        except Exception as e:
                            toast_msg = f"Error: {e}"
                            toast_timer = time.time()

                elif act == "RES":
                    cur = resolution_of_path(game_action_modal.get("rom_path", ""))
                    res_modal["selected_idx"] = (RESOLUTIONS.index(cur)
                                                 if cur in RESOLUTIONS else 0)
                    res_modal["active"] = True
                elif act == "REGET":
                    if g_info:
                        q_msg = enqueue_download(sys_c, g_info)
                        if q_msg:
                            toast_msg = q_msg
                            toast_timer = time.time()
                    else:
                        toast_msg = "Không thể tải lại từ mục này" if state.current_lang == "VI" else "Cannot re-download from here"
                        toast_timer = time.time()

        # SEARCH INPUT: PHYSICAL X = SPACE, PHYSICAL Y = DEL, L1/R1 = SYSTEM FILTER
        elif current_screen == "search_input":
            if btn_l1:
                # Cycling with the shoulders meant stepping through 30 systems one
                # press at a time; a list is one press to the one you want.
                rows = [(c, tr("search_scope_all") if c == "ALL" else get_system_display_name(c),
                         str(_sys_counts.get(c, 0)) if c != "ALL" else "")
                        for c in sys_keys_list]
                open_picker(tr("search_pick_sys"), rows, "search_sys",
                            sys_keys_list[search_sys_idx])
            elif btn_r1:
                rows = [(c, tr(f"src_{c.lower()}"), "") for c in SEARCH_SOURCES]
                open_picker(tr("search_pick_src"), rows, "search_src", search_source)
            elif btn_up:
                r, c = kb_cursor
                r = (r - 1) % len(kb_rows)
                c = min(c, len(kb_rows[r]) - 1)
                kb_cursor = [r, c]
            elif btn_down:
                r, c = kb_cursor
                r = (r + 1) % len(kb_rows)
                c = min(c, len(kb_rows[r]) - 1)
                kb_cursor = [r, c]
            elif btn_left:
                r, c = kb_cursor
                c = (c - 1) % len(kb_rows[r])
                kb_cursor = [r, c]
            elif btn_right:
                r, c = kb_cursor
                c = (c + 1) % len(kb_rows[r])
                kb_cursor = [r, c]
            elif btn_x: # Physical X = Space
                search_query += " "
            elif btn_y: # Physical Y = Delete
                search_query = search_query[:-1]
            elif btn_b:
                screen_stack.pop()
            elif btn_start:
                q_clean = search_query.strip().lower()
                if q_clean:
                    target_sys = sys_keys_list[search_sys_idx]
                    if db and os.path.exists(db.DB_PATH):
                        raw_fts = db.search_games_fts(q_clean, sys_code=target_sys, limit=150,
                                                      source_type=search_source)
                        search_results_list = [{"sys_code": g["sys_code"], "game_info": g} for g in raw_fts]
                    else:
                        seen_keys = set()
                        search_results_list = []
                        target_systems = ["GBA", "SFC", "FC", "MD", "GB", "GBC", "GG", "MS", "NDS", "PICO8", "ARCADE"] if target_sys == "ALL" else [target_sys]
                        for sc in target_systems:
                            s_data = state.catalogs.get(sc, {})
                            for g in s_data.get("games", []):
                                fn = g.get("filename", "")
                                if q_clean in g.get("_s_idx", ""):
                                    dedup_key = (g.get("sys_code", sc), fn)
                                    if dedup_key not in seen_keys:
                                        seen_keys.add(dedup_key)
                                        search_results_list.append({"sys_code": g.get("sys_code", sc), "game_info": g})
                    search_results_items_cache = None
                    selected_indices["search_results"] = 0
                    screen_stack.append("search_results")
                else:
                    toast_msg = "Vui lòng nhập từ khóa!" if state.current_lang == "VI" else "Please enter search keyword!"
                    toast_timer = time.time()
            elif btn_a:
                r, c = kb_cursor
                key_val = kb_rows[r][c]
                if key_val == "SPACE":
                    search_query += " "
                elif key_val == "DEL":
                    search_query = search_query[:-1]
                elif key_val == "CLEAR":
                    search_query = ""
                elif key_val == "SEARCH":
                    q_clean = search_query.strip().lower()
                    if q_clean:
                        target_sys = sys_keys_list[search_sys_idx]
                        if db and os.path.exists(db.DB_PATH):
                            raw_fts = db.search_games_fts(q_clean, sys_code=target_sys, limit=150,
                                                      source_type=search_source)
                            search_results_list = [{"sys_code": g["sys_code"], "game_info": g} for g in raw_fts]
                        else:
                            seen_keys = set()
                            search_results_list = []
                            target_systems = ["GBA", "SFC", "FC", "MD", "GB", "GBC", "GG", "MS", "NDS", "PICO8", "ARCADE"] if target_sys == "ALL" else [target_sys]
                            for sc in target_systems:
                                s_data = state.catalogs.get(sc, {})
                                for g in s_data.get("games", []):
                                    fn = g.get("filename", "")
                                    if q_clean in g.get("_s_idx", ""):
                                        dedup_key = (g.get("sys_code", sc), fn)
                                        if dedup_key not in seen_keys:
                                            seen_keys.add(dedup_key)
                                            search_results_list.append({"sys_code": g.get("sys_code", sc), "game_info": g})
                        search_results_items_cache = None
                        selected_indices["search_results"] = 0
                        screen_stack.append("search_results")
                    else:
                        toast_msg = "Vui lòng nhập từ khóa!" if state.current_lang == "VI" else "Please enter search keyword!"
                        toast_timer = time.time()
                else:
                    search_query += key_val.lower()

        # YOUTUBE SEARCH INPUT: PHYSICAL X = SPACE, PHYSICAL Y = DEL, START/A = SEARCH
        elif current_screen == "yt_search_input":
            if btn_up:
                r, c = kb_cursor
                r = (r - 1) % len(kb_rows)
                c = min(c, len(kb_rows[r]) - 1)
                kb_cursor = [r, c]
            elif btn_down:
                r, c = kb_cursor
                r = (r + 1) % len(kb_rows)
                c = min(c, len(kb_rows[r]) - 1)
                kb_cursor = [r, c]
            elif btn_left:
                r, c = kb_cursor
                c = (c - 1) % len(kb_rows[r])
                kb_cursor = [r, c]
            elif btn_right:
                r, c = kb_cursor
                c = (c + 1) % len(kb_rows[r])
                kb_cursor = [r, c]
            elif btn_x: # Physical X = Space
                yt_input_text += " "
            elif btn_y: # Physical Y = Delete
                yt_input_text = yt_input_text[:-1]
            elif btn_b:
                screen_stack.pop()
            elif (btn_start or (btn_a and kb_rows[kb_cursor[0]][kb_cursor[1]] == "SEARCH")):
                q_clean = yt_input_text.strip()
                if q_clean:
                    yt_mode = "search"
                    yt_search_query = q_clean
                    selected_idx = 0
                    selected_indices["yt_grid"] = 0
                    scroll_offsets["yt_grid"] = 0
                    yt_search_results_list = []

                    # Update recent search queries list
                    matched_preset_idx = -1
                    for idx, p in enumerate(yt.DEFAULT_PRESET_QUERIES):
                        if q_clean.lower() == p.lower():
                            matched_preset_idx = idx
                            break

                    if matched_preset_idx >= 0:
                        yt_query_idx = matched_preset_idx
                    else:
                        yt_recent_queries = [q for q in yt_recent_queries if q.lower() != q_clean.lower()]
                        insert_pos = min(len(yt.DEFAULT_PRESET_QUERIES), len(yt_recent_queries))
                        yt_recent_queries.insert(insert_pos, q_clean)
                        if len(yt_recent_queries) > 10:
                            yt_recent_queries = yt_recent_queries[:10]
                        yt.save_search_history(yt_recent_queries)
                        yt_query_idx = insert_pos

                    screen_stack.pop()
                    start_yt_load(q_clean, is_trending=False)
                else:
                    toast_msg = "Vui lòng nhập từ khóa!" if state.current_lang == "VI" else "Please enter search keyword!"
                    toast_timer = time.time()
            elif btn_a:
                r, c = kb_cursor
                key_val = kb_rows[r][c]
                if key_val == "SPACE":
                    yt_input_text += " "
                elif key_val == "DEL":
                    yt_input_text = yt_input_text[:-1]
                elif key_val == "CLEAR":
                    yt_input_text = ""
                elif key_val == "SEARCH":
                    pass
                else:
                    yt_input_text += key_val.lower()

        # YOUTUBE 3x2 GRID NAVIGATION: A=PLAY, B=BACK, X=SEARCH, Y=TRENDING, LR=PAGE 6
        elif current_screen == "yt_grid":
            cur_videos = yt_trending_list if yt_mode == "trending" else yt_search_results_list
            total_v = len(cur_videos)

            if total_v > 0:
                cols = 3
                rows = 2
                per_page = 6
                scroll_row = scroll_offsets.get("yt_grid", 0)

                if btn_left:
                    if selected_idx > 0:
                        selected_idx -= 1
                elif btn_right:
                    if selected_idx < total_v - 1:
                        selected_idx += 1
                elif btn_up:
                    if selected_idx - cols >= 0:
                        selected_idx -= cols
                elif btn_down:
                    if selected_idx + cols < total_v:
                        selected_idx += cols
                # Keep selected card visible in 2 rows
                cur_row = selected_idx // cols
                if cur_row < scroll_row:
                    scroll_row = cur_row
                elif cur_row >= scroll_row + rows:
                    scroll_row = cur_row - rows + 1

                scroll_offsets["yt_grid"] = scroll_row
                selected_indices["yt_grid"] = selected_idx

                # Tự động nạp trước luồng phát (Speculative Pre-fetch) khi người dùng dừng con trỏ ở 1 video > 0.5s
                cur_v_sel = cur_videos[selected_idx] if (0 <= selected_idx < total_v) else None
                sel_id = cur_v_sel.get("id") if cur_v_sel else None
                if sel_id:
                    if sel_id != yt_last_hover_id:
                        yt_last_hover_id = sel_id
                        yt_hover_start_time = time.time()
                    elif (time.time() - yt_hover_start_time > 0.5) and (sel_id not in yt_player._STREAM_CACHE):
                        if yt_prefetch_thread is None or not yt_prefetch_thread.is_alive():
                            def _bg_prefetch(vid_fetch):
                                try:
                                    yt_player.extract_stream_fast(vid_fetch)
                                except Exception:
                                    pass
                            yt_prefetch_thread = threading.Thread(target=_bg_prefetch, args=(sel_id,), daemon=True)
                            yt_prefetch_thread.start()

                if btn_a and 0 <= selected_idx < total_v:
                    cur_v = cur_videos[selected_idx]
                    v_id = cur_v.get("id")
                    if v_id:
                        ra_bin = "/mnt/SDCARD/RetroArch/ra64.trimui"
                        ff_core = "/mnt/SDCARD/Emus/FFMPEG/ffmpeg_libretro.so"
                        if not (os.path.exists(ra_bin) and os.path.exists(ff_core)):
                            toast_msg = tr("yt_no_player")
                            toast_timer = time.time()
                        else:
                            # 1. Nếu chưa có trong cache, hiển thị hộp thoại loading để người dùng thấy phản hồi
                            if v_id not in yt_player._STREAM_CACHE:
                                v_title = cur_v.get("title", v_id)
                                fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 185)
                                mw = 720
                                mh = 200
                                mx = (state.SCREEN_W - mw) // 2
                                my = (state.SCREEN_H - mh) // 2
                                fill_rect(mx, my, mw, mh, 20, 26, 38, 245)
                                draw_rect(mx, my, mw, mh, 59, 130, 246, 255, thickness=2)
                                draw_text("YouTube Stream", font_badge, mx + 30, my + 25, 239, 68, 68)
                                t_lines = wrap_text_to_width(v_title, font_sub, mw - 60, max_lines=2)
                                ty = my + 65
                                for tl in t_lines:
                                    draw_text(tl, font_sub, mx + 30, ty, 255, 255, 255)
                                    ty += 32
                                load_text = "Đang kết nối luồng phát tốc độ cao..." if state.current_lang == "VI" else "Connecting high-speed stream..."
                                draw_text(load_text, font_modal_val, mx + 30, my + mh - 42, 56, 189, 248)
                                sdl2.SDL_RenderPresent(renderer)

                            # 2. Lấy link phát từ cache tức thì (0s) hoặc hoàn tất tải
                            from rh.yt_player import extract_stream_fast
                            s_url, s_title = extract_stream_fast(v_id)

                            if not s_url:
                                toast_msg = "Không lấy được luồng phát video!" if state.current_lang == "VI" else "Failed to extract stream URL!"
                                toast_timer = time.time()
                            else:
                                try:
                                    # Luu thong tin stream vao /tmp/yt_stream_info.json de yt_player khong phai chay lai yt-dlp
                                    info_file = "/tmp/yt_stream_info.json"
                                    stream_info = {
                                        "video_id": v_id,
                                        "stream_url": s_url,
                                        "title": s_title or v_title
                                    }
                                    with open(info_file, "w", encoding="utf-8") as _sf:
                                        json.dump(stream_info, _sf)

                                    # Save resume state so returning from video playback resumes at exact YouTube screen & cursor
                                    _resume_state = {
                                        "screen_stack": screen_stack if len(screen_stack) > 1 else ["home", "yt_grid"],
                                        "selected_indices": selected_indices,
                                        "scroll_offsets": scroll_offsets,
                                        "yt_mode": yt_mode,
                                        "yt_search_query": yt_search_query,
                                        "yt_trending_list": yt_trending_list,
                                        "yt_search_results_list": yt_search_results_list,
                                        "yt_recent_queries": yt_recent_queries,
                                        "yt_query_idx": yt_query_idx,
                                        "yt_query_cache": yt_query_cache,
                                    }
                                    with open("/tmp/retrohub_resume.json", "w", encoding="utf-8") as _rf:
                                        json.dump(_resume_state, _rf)

                                    play_cmd = yt.build_play_command(v_id, info_file=info_file)
                                    with open("/tmp/launch_game.sh", "w", encoding="utf-8") as f:
                                        f.write(play_cmd)
                                    subprocess.call("chmod 755 /tmp/launch_game.sh 2>/dev/null", shell=True)
                                    running = False
                                except Exception as e:
                                    toast_msg = f"Error: {e}"
                                    toast_timer = time.time()

            # L1 / R1: Switch recent search keywords
            if (btn_l1 or btn_r1) and yt_recent_queries:
                if btn_l1:
                    yt_query_idx = (yt_query_idx - 1) % len(yt_recent_queries)
                else:
                    yt_query_idx = (yt_query_idx + 1) % len(yt_recent_queries)

                new_q = yt_recent_queries[yt_query_idx]
                selected_idx = 0
                selected_indices["yt_grid"] = 0
                scroll_offsets["yt_grid"] = 0

                if new_q == "Nhạc trẻ" or yt_query_idx == 0:
                    yt_mode = "trending"
                    if not yt_trending_list:
                        start_yt_load("Nhạc trẻ", is_trending=True)
                    else:
                        yt_loading_state["active"] = False
                        _prefetch_yt_thumbs(yt_trending_list)
                        trigger_yt_adjacent_preload()
                    toast_msg = "Chủ đề: Nhạc trẻ (Thịnh hành)" if state.current_lang == "VI" else "Topic: Trending"
                    toast_timer = time.time()
                else:
                    yt_mode = "search"
                    yt_search_query = new_q
                    if new_q in yt_query_cache and yt_query_cache[new_q]:
                        yt_search_results_list = yt_query_cache[new_q]
                        yt_loading_state["active"] = False
                        _prefetch_yt_thumbs(yt_search_results_list)
                        trigger_yt_adjacent_preload()
                    else:
                        yt_search_results_list = []
                        start_yt_load(new_q, is_trending=False)
                    toast_msg = f"Từ khóa: {new_q}" if state.current_lang == "VI" else f"Keyword: {new_q}"
                    toast_timer = time.time()

                items = yt_trending_list if yt_mode == "trending" else yt_search_results_list
                cur_videos = items
                total_v = len(cur_videos)

            if btn_x: # Press X to open Search
                selected_indices["yt_search_input"] = 0
                yt_input_text = ""
                kb_cursor = [0, 0]
                screen_stack.append("yt_search_input")

            elif btn_y: # Press Y to return to trending Nhạc trẻ
                if yt_mode == "search" or yt_query_idx != 0:
                    yt_query_idx = 0
                    yt_mode = "trending"
                    selected_idx = 0
                    selected_indices["yt_grid"] = 0
                    scroll_offsets["yt_grid"] = 0
                    if not yt_trending_list:
                        start_yt_load("Nhạc trẻ", is_trending=True)
                    else:
                        yt_loading_state["active"] = False
                        _prefetch_yt_thumbs(yt_trending_list)
                        trigger_yt_adjacent_preload()
                    toast_msg = "Đã chuyển về Nhạc trẻ Thịnh hành" if state.current_lang == "VI" else "Switched to Trending"
                    toast_timer = time.time()
                    items = yt_trending_list or []
                    cur_videos = items
                    total_v = len(cur_videos)

            elif btn_b:
                if len(screen_stack) > 1:
                    screen_stack.pop()
                else:
                    running = False


        elif modal_title:
            if btn_a or btn_b:
                modal_title = None
                modal_rows = None
                modal_style = None

        else:
            # Downloaded Games: X = Toggle View Mode, Y = Random Play
            if current_screen == "download_manager" and btn_x:
                if dl_state.get("active") or dl_state.get("status") in ("downloading", "extracting"):
                    cancel_active_download()
                    toast_msg = tr("dl_cancelled_toast")
                    toast_timer = time.time()

            elif dl_state.get("active") and dl_state.get("is_background") and btn_f1 and current_screen != "search_input":
                dl_state["is_background"] = False

            elif current_screen == "downloaded_games" and btn_x:
                state.downloaded_view_mode = "grid" if state.downloaded_view_mode == "list" else "list"
                state.save_settings()
                toast_msg = tr("view_mode_grid") if state.downloaded_view_mode == "grid" else tr("view_mode_list")
                toast_timer = time.time()

            elif current_screen == "downloaded_games" and btn_f1:
                # Build the rows from what is actually on the card, so the list
                # never offers a system with nothing behind it.
                counts = {}
                for g in downloaded_games_list:
                    sc = g.get("sys_code") or "?"
                    counts[sc] = counts.get(sc, 0) + 1
                rows = [("ALL", tr("lib_filter_all_row"), str(len(downloaded_games_list)))]
                rows += [(c, get_system_display_name(c), str(n))
                         for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
                open_picker(tr("lib_filter_title"), rows, "lib_sys", current_lib_sys)

            elif current_screen == "downloaded_games" and btn_y and len(lib_games_list) > 0:
                rand_game = random.choice(lib_games_list)
                sys_c = rand_game["sys_code"]
                rom_p = rand_game["rom_path"]
                toast_msg = f"Random: {rand_game['title']}"
                toast_timer = time.time()
                ok, err_msg = launch_emulator_game(sys_c, rom_p)
                if not ok:
                    toast_msg = err_msg
                    toast_timer = time.time()

            elif current_screen == "rom_games" and btn_x:
                if current_source != "HITS":
                    state.rom_sort_mode = "alpha" if state.rom_sort_mode == "downloads" else "downloads"
                    selected_indices["rom_games"] = 0
                    scroll_offsets["rom_games"] = 0
                    rom_games_items_cache = None
                    toast_msg = "Sắp xếp theo Bảng chữ cái (A-Z)" if state.rom_sort_mode == "alpha" else "Sắp xếp theo Lượt tải nhiều nhất"
                    toast_timer = time.time()

            elif current_screen == "rom_games" and btn_y:
                # Open Alphabet Quick Jump Modal A-Z.
                # Ban do chu cai chi co nghia tren danh sach xep A-Z, nen no phai
                # duoc tinh tren chinh danh sach se hien sau khi nhay - dung ca
                # the loai dang loc. Dang xep theo luot tai thi cu nhay se doi
                # danh sach ve A-Z.
                _alpha_cat = current_java_cat if current_source == "JAVA" else None
                _alpha_key = (current_source, current_rom_system, "alpha", current_java_cat)
                if _alpha_key == rom_games_cache_key:
                    games_list = rom_games_cache
                else:
                    games_list = get_games_for_view(current_source, current_rom_system,
                                                    sort_by="title", category=_alpha_cat)
                avail, counts = alpha_index(games_list)
                alphabet_modal["available_map"] = avail
                alphabet_modal["counts_map"] = counts
                alphabet_modal["sys_code"] = current_rom_system
                alphabet_modal["needs_alpha_sort"] = state.rom_sort_mode != "alpha"
                alphabet_modal["selected_idx"] = 0
                alphabet_modal["active"] = True

            elif current_screen == "rom_games" and btn_f1:
                if current_rom_system in sys_keys_list:
                    search_sys_idx = sys_keys_list.index(current_rom_system)
                search_query = ""
                screen_stack.append("search_input")

            # Grid Navigation in Downloaded Games
            elif current_screen == "downloaded_games" and state.downloaded_view_mode == "grid" and len(lib_games_list) > 0:
                cols = 3
                total_dl = len(lib_games_list)

                if btn_up:
                    selected_idx = max(0, selected_idx - cols)
                    selected_indices[current_screen] = selected_idx
                elif btn_down:
                    selected_idx = min(total_dl - 1, selected_idx + cols)
                    selected_indices[current_screen] = selected_idx
                elif btn_left:
                    selected_idx = max(0, selected_idx - 1)
                    selected_indices[current_screen] = selected_idx
                elif btn_right:
                    selected_idx = min(total_dl - 1, selected_idx + 1)
                    selected_indices[current_screen] = selected_idx
                elif btn_l1: # Page backward 10
                    selected_idx = max(0, selected_idx - 10)
                    selected_indices[current_screen] = selected_idx
                elif btn_r1: # Page forward 10
                    selected_idx = min(total_dl - 1, selected_idx + 10)
                    selected_indices[current_screen] = selected_idx
                elif btn_b:
                    screen_stack.pop()
                elif btn_a:
                    dg = lib_games_list[selected_idx]
                    game_action_modal["active"] = True
                    game_action_modal["game_info"] = {"title": dg["title"], "filename": dg["filename"]}
                    game_action_modal["rom_path"] = dg["rom_path"]
                    game_action_modal["sys_code"] = dg["sys_code"]
                    game_action_modal["img_path"] = dg.get("img_path")
                    game_action_modal["size_str"] = dg.get("size_str", "")
                    game_action_modal["selected_opt"] = 0
                    game_action_modal["from_downloaded_view"] = True

            # Standard List Navigation (Supports D-pad & L1 / R1 for 10-item fast scroll)
            elif btn_up:
                if selected_idx == 0:
                    selected_idx = len(items) - 1
                    scroll_offsets[current_screen] = max(0, len(items) - 6)
                else:
                    selected_idx -= 1
                selected_indices[current_screen] = selected_idx
            elif btn_down:
                if selected_idx >= len(items) - 1:
                    selected_idx = 0
                    scroll_offsets[current_screen] = 0
                else:
                    selected_idx += 1
                selected_indices[current_screen] = selected_idx
            # DEN LED: trai/phai chinh ngay gia tri tren dong dang chon, thay
            # vi nhay 10 dong nhu danh sach dai. Man hinh nay co sau dong, cu
            # chi nhay 10 o day khong co nghia gi.
            elif current_screen == "led" and (btn_left or btn_right):
                row_id = items[selected_idx].get("id") if items else ""
                if row_id == "led_brightness":
                    step = 10 if btn_right else -10
                    led_cfg["brightness"] = max(0, min(100,
                        led_cfg.get("brightness", 60) + step))
                    if not ledconf.save(led_cfg):
                        toast_msg = tr("led_save_failed")
                        toast_timer = time.time()
                elif row_id == "led_speed":
                    led_cfg["speed"] = ledconf.cycle_speed(
                        led_cfg.get("speed", 1.0), 1 if btn_right else -1)
                    if not ledconf.save(led_cfg):
                        toast_msg = tr("led_save_failed")
                        toast_timer = time.time()
            elif btn_left or btn_l1: # L1 or Left: Jump back 10
                selected_idx = max(0, selected_idx - 10)
                selected_indices[current_screen] = selected_idx
            elif btn_right or btn_r1: # R1 or Right: Jump forward 10
                selected_idx = min(len(items) - 1, selected_idx + 10)
                selected_indices[current_screen] = selected_idx
            # Bo mau da xem thu nhung khong chon: ghi lai led_cfg de tra den
            # ve nguyen trang. led_cfg chua bao gio bi preview dung toi, nen no
            # van la bo mau nguoi dung chot lan cuoi - khong can bien nho rieng.
            elif current_screen == "led_theme" and btn_b:
                if not ledconf.save(led_cfg):
                    toast_msg = tr("led_save_failed")
                    toast_timer = time.time()
                led_preview = None
                screen_stack.pop()
            elif btn_b:
                if modal_rows is not None:
                    modal_rows = None
                    modal_title = None
                    modal_style = None
                elif current_screen == "file_browser":
                    if fb_current_path.rstrip("/") != "/mnt/SDCARD" and fb_current_path.rstrip("/") != "":
                        parent = os.path.dirname(fb_current_path.rstrip("/"))
                        fb_current_path = parent if parent else "/mnt/SDCARD"
                        selected_indices["file_browser"] = 0
                    else:
                        screen_stack.pop()
                elif len(screen_stack) > 1:
                    screen_stack.pop()
                else:
                    running = False
            elif btn_a:
                # items is rebuilt every frame and can shrink - or be empty for a
                # frame - while the cursor still points past its end. Clamp before
                # indexing: unguarded, this raised IndexError and killed the app.
                if selected_idx >= len(items):
                    selected_idx = max(0, len(items) - 1)
                    selected_indices[current_screen] = selected_idx
                cur_item = items[selected_idx] if items else {}
                item_id = cur_item.get("id", "")

                if item_id == "nav_network":
                    screen_stack.append("network")
                elif item_id == "nav_rom_store_menu":
                    bat_cap, bat_chg = get_battery_info()
                    if bat_cap < 30 and not bat_chg:
                        toast_msg = tr("low_battery_warn")
                        toast_timer = time.time()
                    screen_stack.append("rom_store_menu")
                elif item_id == "nav_utilities":
                    selected_indices["utilities"] = 0
                    screen_stack.append("utilities")
                elif item_id == "nav_j2me_render":
                    if not cur_item.get("render_ok"):
                        # Opening it would offer settings the installed emulator
                        # cannot act on; say why instead.
                        toast_msg = tr("j2me_render_old_hint")
                        toast_timer = time.time()
                    else:
                        # Read fresh: START+R3 on the device rewrites the same file,
                        # so a value cached from an earlier visit shows the wrong row.
                        j2me_render_mode = load_render_mode()
                        selected_indices["j2me_render"] = 0
                        screen_stack.append("j2me_render")
                elif item_id.startswith("j2merender_"):
                    m = cur_item.get("render_mode")
                    if save_render_mode(m):
                        j2me_render_mode = m
                        toast_msg = tr("j2me_render_saved")
                        toast_timer = time.time()
                elif item_id == "nav_core_sys":
                    core_sys_rows = corepicker.list_systems()
                    selected_indices["core_sys"] = 0
                    screen_stack.append("core_sys")
                elif item_id.startswith("coresys_"):
                    core_sys_pick = cur_item.get("core_row")
                    selected_indices["core_pick"] = 0
                    screen_stack.append("core_pick")
                elif item_id.startswith("corepick_"):
                    opt = cur_item.get("core_opt") or {}
                    code = (core_sys_pick or {}).get("code")
                    if code and corepicker.set_core(code, opt.get("launch")):
                        # Doc lai tu the chu khong tu suy: neu ghi hong ma van ve
                        # dau "dang dung" thi nguoi dung tin nham.
                        core_sys_rows = corepicker.list_systems()
                        core_sys_pick = next((r for r in core_sys_rows
                                              if r["code"] == code), core_sys_pick)
                        toast_msg = tr("core_saved")
                    else:
                        toast_msg = tr("core_failed")
                    toast_timer = time.time()
                elif item_id == "nav_led":
                    # Dong bo truoc khi ve: file co the dang noi doi. Tren
                    # firmware goc khong he co tu chay khi khoi dong (co y nhu
                    # vay), nen sau moi lan khoi dong lai may, led.json van noi
                    # enabled=true trong khi khong co daemon nao - cong tac hien
                    # BAT, den tat, bam mot cai thanh TAT va khong co gi xay ra.
                    # reconcile() cung don not den con sang sot lai tu mot daemon
                    # bi kill -9, dung nhu bang rui ro cua ban thiet ke hua.
                    led_cfg = ledctl.reconcile(ledconf.load())
                    led_zones = led.detect_zones()
                    if ledctl.conflicting_daemon():
                        toast_msg = tr("led_conflict")
                        toast_timer = time.time()
                    selected_indices["led"] = 0
                    screen_stack.append("led")
                elif item_id == "led_toggle":
                    want = not led_cfg.get("enabled", False)
                    if want:
                        # Ghi file TRUOC khi tha daemon. Daemon doc cau hinh
                        # ngay khi khoi dong va tu thoat neu no noi TAT (xem
                        # rh/leddaemon.run), nen tha truoc roi ghi sau la mot
                        # cuoc dua ma ben thua la den khong bao gio sang.
                        new_cfg = dict(led_cfg, enabled=True)
                        if not ledconf.save(new_cfg):
                            toast_msg = tr("led_save_failed")
                            toast_timer = time.time()
                        elif ledctl.start():
                            led_cfg = new_cfg
                        else:
                            # Khong tha duoc: tra file ve nguyen trang, neu
                            # khong thi may se tin la dang bat.
                            ledconf.save(led_cfg)
                    elif ledctl.stop():
                        # Chieu tat thi nguoc lai: daemon tu don den luc nhan
                        # SIGTERM, va neu no khong con song thi stop() da tat
                        # den ho. Ghi sau nen mot lan ghi hong khong de lai
                        # den sang - lan mo man hinh sau reconcile() se don.
                        led_cfg["enabled"] = False
                        if not ledconf.save(led_cfg):
                            toast_msg = tr("led_save_failed")
                            toast_timer = time.time()
                elif item_id == "led_boot":
                    # Hoi dia chu khong hoi led_cfg, cung ly do voi dong ve
                    # cong tac o tren: neu hai nguon lech nhau thi bam mot cai
                    # se cai lai cai da cai, mai mai.
                    want = not ledctl.hook_installed()
                    ok = ledctl.install_hook() if want else ledctl.remove_hook()
                    if ok:
                        # led_cfg["boot"] chi duoc gan sau khi ghi file thanh
                        # cong - neu khong the trang thai trong bo nho se noi
                        # BAT trong khi hook da cai nhung file van ghi false.
                        new_cfg = dict(led_cfg, boot=want)
                        if ledconf.save(new_cfg):
                            led_cfg = new_cfg
                        else:
                            toast_msg = tr("led_save_failed")
                            toast_timer = time.time()
                elif item_id == "nav_led_theme":
                    # Mo ra dung o bo mau dang dung, khong phai dong dau: xem
                    # thu bat dau tu cai nguoi ta dang nghe, khong phai tu dau
                    # danh sach.
                    selected_indices["led_theme"] = next(
                        (i for i, th in enumerate(ledthemes.THEMES)
                         if th["id"] == led_cfg.get("theme")), 0)
                    # Con tro dang dung tren bo mau hien tai, tuc dang xem thu
                    # chinh no: khong can ghi lai gi khi chua ai bam gi.
                    led_preview = led_cfg.get("theme")
                    screen_stack.append("led_theme")
                elif item_id.startswith("ledtheme_"):
                    led_cfg = ledconf.apply_theme(led_cfg, cur_item.get("theme_id"))
                    if not ledconf.save(led_cfg):
                        toast_msg = tr("led_save_failed")
                        toast_timer = time.time()
                    led_preview = None
                    screen_stack.pop()
                elif item_id == "led_none":
                    toast_msg = tr("led_no_zones")
                    toast_timer = time.time()
                elif item_id == "led_boot_off":
                    # "is_disabled" duoc dat o bon cho trong file nay nhung
                    # khong cho nao doc: dong nay khong mo, van chon duoc, va
                    # bam A truoc day khong roi vao nhanh nao - khong toast,
                    # khong gi ca. Lam nhu led_none o tren: tu giai thich.
                    toast_msg = tr("led_boot_unavailable_detail")
                    toast_timer = time.time()
                elif item_id in ("core_note", "core_none"):
                    toast_msg = tr("core_note") if item_id == "core_note" else tr("core_none")
                    toast_timer = time.time()
                elif item_id == "j2me_render_note":
                    toast_msg = tr("j2me_render_note")
                    toast_timer = time.time()
                elif item_id == "nav_youtube":
                    yt_recent_queries = yt.load_search_history()
                    yt_query_idx = 0
                    yt_mode = "trending"
                    selected_indices["yt_grid"] = 0
                    scroll_offsets["yt_grid"] = 0
                    if not yt_trending_list:
                        start_yt_load("Nhạc trẻ", is_trending=True)
                    else:
                        yt_loading_state["active"] = False
                        _prefetch_yt_thumbs(yt_trending_list)
                        trigger_yt_adjacent_preload()
                    screen_stack.append("yt_grid")


                elif item_id == "nav_settings":
                    selected_indices["settings"] = 0
                    screen_stack.append("settings")
                elif item_id == "toggle_autoupdate":
                    state.auto_update = not state.auto_update
                    state.save_settings()
                elif item_id == "nav_splash":
                    splash_images_list = scan_splash_images()
                    selected_indices["splash_manager"] = 0
                    screen_stack.append("splash_manager")
                elif current_screen == "splash_preview":
                    ok, msg = apply_splash_update(SPLASH_TEMP_PREVIEW)
                    toast_msg = msg
                    toast_timer = time.time()
                    screen_stack.pop()
                elif current_screen == "splash_manager":
                    if item_id == "splash_restore":
                        ok, msg = restore_original_splash()
                        toast_msg = msg
                        toast_timer = time.time()
                    elif item_id == "splash_browse_sd":
                        fb_current_path = "/mnt/SDCARD"
                        selected_indices["file_browser"] = 0
                        screen_stack.append("file_browser")
                    elif item_id == "back":
                        screen_stack.pop()
                    elif "img_data" in cur_item:
                        src_p = cur_item["path"]
                        toast_msg = tr("splash_converting")
                        toast_timer = time.time()
                        ok = convert_and_fit_splash(src_p, SPLASH_TEMP_PREVIEW, width=state.SCREEN_W, height=state.SCREEN_H)
                        if ok:
                            get_texture_and_size(SPLASH_TEMP_PREVIEW, force_reload=True)
                            splash_preview_path = SPLASH_TEMP_PREVIEW
                            splash_preview_orig_name = cur_item["title"]
                            screen_stack.append("splash_preview")
                        else:
                            toast_msg = tr("splash_err")
                            toast_timer = time.time()
                elif current_screen == "file_browser":
                    if cur_item.get("id") == "fb_empty":
                        pass
                    elif cur_item.get("type") == "dir" or item_id == "fb_up":
                        fb_current_path = cur_item["path"]
                        selected_indices["file_browser"] = 0
                    elif cur_item.get("type") == "file":
                        src_p = cur_item["path"]
                        toast_msg = tr("splash_converting")
                        toast_timer = time.time()
                        ok = convert_and_fit_splash(src_p, SPLASH_TEMP_PREVIEW, width=state.SCREEN_W, height=state.SCREEN_H)
                        if ok:
                            get_texture_and_size(SPLASH_TEMP_PREVIEW, force_reload=True)
                            splash_preview_path = SPLASH_TEMP_PREVIEW
                            splash_preview_orig_name = cur_item["filename"]
                            screen_stack.append("splash_preview")
                        else:
                            toast_msg = tr("splash_err")
                            toast_timer = time.time()
                elif item_id == "nav_downloaded":
                    downloaded_games_list = scan_all_downloaded_games()
                    selected_indices["downloaded_games"] = 0
                    scroll_offsets["downloaded_games"] = 0
                    screen_stack.append("downloaded_games")
                elif item_id in ("nav_search", "nav_search_global", "nav_search_fts"):
                    selected_indices["search_input"] = 0
                    scroll_offsets["search_input"] = 0
                    screen_stack.append("search_input")
                elif item_id == "nav_online_categories":
                    selected_indices["rom_online_categories"] = 0
                    scroll_offsets["rom_online_categories"] = 0
                    screen_stack.append("rom_online_categories")
                elif item_id == "nav_dl_manager":
                    selected_indices["download_manager"] = 0
                    scroll_offsets["download_manager"] = 0
                    screen_stack.append("download_manager")
                elif current_screen == "download_manager":
                    if item_id == "dl_active_card":
                        dl_state["is_background"] = False
                    elif item_id == "dl_clear_queue":
                        n = clear_download_queue()
                        toast_msg = f"{tr('dl_queue_cleared')} ({n})"
                        toast_timer = time.time()
                    elif item_id == "back":
                        screen_stack.pop()
                elif item_id in ("src_viet", "src_hack", "src_hits", "src_archive", "src_retrostic", "src_all", "src_java", "src_fav"):
                    src_map = {
                        "src_viet": "VIET",
                        "src_hack": "HACK",
                        "src_hits": "HITS",
                        "src_java": "JAVA",
                        "src_retrostic": "RETROSTIC",
                        "src_archive": "ARCHIVE",
                        "src_all": "ALL",
                        "src_fav": "FAV"
                    }
                    current_source = src_map[item_id]
                    if current_source == "JAVA":
                        current_rom_system = "JAVA"
                        current_java_cat = "ALL"
                        java_cats_cache = []
                        selected_indices["rom_java_cats"] = 0
                        scroll_offsets["rom_java_cats"] = 0
                        screen_stack.append("rom_java_cats")
                    else:
                        selected_indices["rom_source_systems"] = 0
                        scroll_offsets["rom_source_systems"] = 0
                        screen_stack.append("rom_source_systems")
                elif item_id.startswith("javacat_"):
                    current_java_cat = cur_item.get("java_cat", "ALL")
                    selected_indices["rom_games"] = 0
                    scroll_offsets["rom_games"] = 0
                    screen_stack.append("rom_games")
                elif item_id.startswith("sys_"):
                    # Both the source-filtered and the legacy system screens build
                    # their tiles with a sys_ id; without this branch pressing A
                    # did nothing, even though the footer offered "Chon he may".
                    current_rom_system = cur_item.get("sys_code") or item_id[4:]
                    selected_indices["rom_games"] = 0
                    scroll_offsets["rom_games"] = 0
                    screen_stack.append("rom_games")
                elif item_id.startswith("game_") or item_id.startswith("res_"):
                    # The store list and the search results build the same tile
                    # shape but were never wired to the detail modal, so pressing
                    # A on a game did nothing on either screen.
                    if cur_item.get("downloaded"):
                        # Tile da deo bien [DA CO] roi ma bam vao van ra man hoi
                        # "co tai khong": doc thanh may khong biet game dang nam
                        # tren the. Game da co thi mo dung bang hanh dong nhu ben
                        # thu vien - choi, xoa, tai lai.
                        g_info = cur_item["game_info"]
                        cur_img = cur_item.get("img_path") or resolve_game_img_path(cur_item["sys_code"], g_info.get("filename"))
                        cur_item["img_path"] = cur_img
                        game_action_modal["active"] = True
                        game_action_modal["game_info"] = g_info
                        game_action_modal["rom_path"] = cur_item.get("rom_path", "")
                        game_action_modal["sys_code"] = cur_item["sys_code"]
                        game_action_modal["img_path"] = cur_img
                        # Dung luong that cua file tren the, dung cach thu vien
                        # do; con so trong catalogue chi la uoc luong cua nguon.
                        _rp = cur_item.get("rom_path", "")
                        _sz_str = (g_info.get("file_size_str") or g_info.get("size") or "").strip()
                        if _sz_str in ("TOPO SHOP", "TOPO"):
                            _sz_str = ""
                        try:
                            _b = os.path.getsize(_rp)
                            _sz_str = (f"{_b / (1024*1024):.1f} MB" if _b > 1024*1024
                                       else f"{_b // 1024} KB")
                        except OSError:
                            pass
                        game_action_modal["size_str"] = _sz_str
                        game_action_modal["selected_opt"] = 0
                        game_action_modal["from_downloaded_view"] = False
                    else:
                        cur_img = cur_item.get("img_path") or resolve_game_img_path(cur_item["sys_code"], cur_item["game_info"].get("filename"))
                        cur_item["img_path"] = cur_img
                        open_pre_download_modal(cur_item["sys_code"],
                                                cur_item["game_info"],
                                                cur_img)
                elif item_id == "toggle_lang":
                    state.current_lang = "EN" if state.current_lang == "VI" else "VI"
                    state.save_settings()
                    toast_msg = f"Đã chuyển sang: {tr('lang_badge')}"
                    toast_timer = time.time()
                elif item_id.startswith("dl_"):
                    dg = cur_item["game_data"]
                    game_action_modal["active"] = True
                    game_action_modal["game_info"] = {"title": dg["title"], "filename": dg["filename"]}
                    game_action_modal["rom_path"] = dg["rom_path"]
                    game_action_modal["sys_code"] = dg["sys_code"]
                    game_action_modal["img_path"] = dg.get("img_path")
                    game_action_modal["size_str"] = dg.get("size_str", "")
                    game_action_modal["selected_opt"] = 0
                    game_action_modal["from_downloaded_view"] = True
                elif item_id == "sftp_toggle":
                    msg = toggle_sftpgo()
                    service_states["sftp"] = is_sftpgo_running()
                    last_service_check_time = time.time()
                    toast_msg = msg
                    toast_timer = time.time()
                elif item_id == "sftp_guide":
                    modal_title = "HƯỚNG DẪN KẾT NỐI SFTPGO" if state.current_lang == "VI" else "SFTPGO CONNECTION GUIDE"
                    modal_style = "big"
                    modal_rows = get_sftp_guide_rows()
                elif item_id == "ssh_toggle":
                    msg = toggle_ssh()
                    service_states["ssh"] = is_ssh_running()
                    last_service_check_time = time.time()
                    toast_msg = msg
                    toast_timer = time.time()
                elif item_id == "ssh_guide":
                    modal_title = "HƯỚNG DẪN KẾT NỐI SSH" if state.current_lang == "VI" else "SSH CONNECTION GUIDE"
                    modal_style = "big"
                    modal_rows = get_ssh_guide_rows()
                elif item_id == "adb_toggle":
                    msg = toggle_adb()
                    service_states["adb"] = is_adb_running()
                    last_service_check_time = time.time()
                    toast_msg = msg
                    toast_timer = time.time()
                elif item_id == "mtp_toggle":
                    msg = toggle_mtp()
                    service_states["mtp"] = is_mtp_running()
                    last_service_check_time = time.time()
                    toast_msg = msg
                    toast_timer = time.time()
                elif item_id == "wifi_ps_toggle":
                    msg = toggle_wifi_awake()
                    service_states["wifi_awake"] = is_wifi_awake()
                    last_service_check_time = time.time()
                    toast_msg = msg
                    toast_timer = time.time()
                elif item_id == "stream_toggle":
                    msg = toggle_streamer()
                    service_states["streamer"] = is_streamer_running()
                    last_service_check_time = time.time()
                    toast_msg = msg
                    toast_timer = time.time()
                elif item_id == "stream_guide":
                    modal_title = "HƯỚNG DẪN STREAM 24 FPS" if state.current_lang == "VI" else "24 FPS STREAM GUIDE"
                    modal_style = "big"
                    modal_rows = get_stream_guide_rows()
                elif item_id == "app_version":
                    if not update_modal["checking"]:
                        update_modal["checking"] = True
                        toast_msg = tr("upd_checking")
                        toast_timer = time.time()
                        threading.Thread(target=manual_check_update, daemon=True).start()
                elif item_id == "nav_donate":
                    # mods is each code's module count. The images carry no quiet
                    # zone of their own, so the renderer adds the four modules the
                    # spec requires, and that needs the count.
                    qr_modal.update(active=True, page=0, pages=[
                        {"title": tr("donate_title"), "img": QR_DONATE_FILE, "mods": 41,
                         "rows": [(tr("donate_bank"), "Techcombank"),
                                  (tr("donate_holder"), "NGUYEN XUAN HOA"),
                                  (tr("donate_acct"), "1732 8888 88")]},
                        {"title": tr("bmc_title"), "img": QR_BMC_FILE, "mods": 29,
                         "rows": [(tr("bmc_site"), "buymeacoffee.com"),
                                  (tr("bmc_user"), "xuanhoa493"),
                                  (tr("bmc_pay"), tr("bmc_pay_val"))]},
                    ])
                elif item_id == "nav_chat":
                    qr_modal.update(active=True, page=0, pages=[
                        {"title": tr("chat_title"), "img": QR_TELEGRAM_FILE, "mods": 25,
                         "rows": [("Telegram", "@retrohubtool")]},
                    ])
                elif item_id == "nav_author":
                    modal_title = tr("author_title")
                    modal_style = "two_col"
                    modal_rows = [
                        (tr("author_name"), "Nguyễn Xuân Hòa"),
                        ("Email", "nguyenxuanhoa493@gmail.com"),
                        (tr("author_phone"), "0962 369 231"),
                        ("Telegram", "@xuanhoa493"),
                        (tr("author_web"), "xuanhoa493.com"),
                    ]
                elif item_id == "device_info":
                    modal_title = "THÔNG TIN THIẾT BỊ & MẠNG" if state.current_lang == "VI" else "DEVICE & NETWORK INFO"
                    modal_rows = get_device_info_rows()
                elif item_id == "storage_status":
                    modal_title = "TRẠNG THÁI DUNG LƯỢNG LƯU TRỮ" if state.current_lang == "VI" else "STORAGE & DISK STATUS"
                    modal_rows = get_storage_info_rows()
                elif item_id == "install_j2me_emu":
                    # Just open the panel. Installing on open was surprising, and it
                    # reported success unconditionally even when pieces were missing.
                    # Rescan here: the list is filled lazily when the library screen is
                    # visited, so coming straight from Utilities showed a stale count.
                    downloaded_games_list = scan_all_downloaded_games()
                    j2me_modal["busy"] = False
                    j2me_modal["pending"] = False
                    j2me_modal["active"] = True
                elif item_id == "back" and current_screen == "led_theme":
                    # Dung duong cua nut B: bo mau dang xem thu chua duoc chon,
                    # phai ghi lai led_cfg de tra den ve nguyen trang. Roi man
                    # hinh bang dong nay ma khong lam vay se bien ban xem thu
                    # thanh vinh vien tren dia trong khi led_cfg trong bo nho
                    # van giu bo mau cu - va dong "Bo mau" o man hinh truoc se
                    # ghi mot cai ten khac han voi cai dang sang.
                    if not ledconf.save(led_cfg):
                        toast_msg = tr("led_save_failed")
                        toast_timer = time.time()
                    led_preview = None
                    if len(screen_stack) > 1:
                        screen_stack.pop()
                elif item_id == "back":
                    if len(screen_stack) > 1:
                        screen_stack.pop()
                elif item_id == "exit":
                    running = False

            # Con tro chinh la nut xem thu: di toi bo mau nao thi den doi ngay
            # toi bo mau do. Ghi vao led.json - cung duong di voi luc chon that,
            # nen khong co nhanh code rieng cho preview, va daemon nhan trong
            # khoang mot phan muoi giay.
            #
            # Dat SAU toan bo chuoi if/elif dieu huong, khong phai chen vao
            # giua no: chen vao giua se cat chuoi lam hai, va tu do btn_a /
            # btn_b khong con loai tru lan nhau voi btn_up / btn_down - mot
            # khung hinh co ca hai co se vua cuon vua mo nham muc.
            if current_screen == "led_theme" and (btn_up or btn_down) and items:
                new_theme = items[selected_idx].get("theme_id")
                # So voi bo mau DA XEM THU lan truoc, khong phai voi
                # led_cfg["theme"]. led_cfg co y khong bi preview dung toi (no
                # la ban de tra ve khi bam B), nen so voi no se lam viec cuon
                # con tro QUAY LAI dong "DANG DUNG" khong ghi gi ca: den van
                # giu bo mau vua xem thu trong khi dong do noi no dang duoc
                # dung. Dung nghia la "con tro chinh la nut xem thu".
                if new_theme and new_theme != led_preview:
                    led_preview = new_theme
                    # Khong toast neu ghi hong: day la buoc xem thu, chay moi
                    # lan con tro di chuyen. Neu the hong that, toast se lap
                    # lai lien tuc trong luc luot qua 12 bo mau - ca A (chon
                    # that) va B (tra ve nguyen trang) van kiem tra ket qua
                    # ghi, nen loi that su van duoc bao, chi khong bao o day.
                    ledconf.save(ledconf.apply_theme(led_cfg, new_theme))

        # A finished update swapped the bytecode underneath this process. Hand
        # control back to launch.sh, which restarts the app with the new build.
        if update_modal.get("restart") and not update_modal["busy"]:
            running = False

        # The check runs off-thread and cannot touch toast_msg directly.
        if update_modal.get("notice"):
            toast_msg = update_modal["notice"]
            update_modal["notice"] = None
            toast_timer = time.time()

        # Same for the startup repair thread, which may have upgraded the J2ME
        # emulator while the user was still looking at the home screen.
        if startup_notice.get("msg"):
            toast_msg = startup_notice["msg"]
            startup_notice["msg"] = None
            toast_timer = time.time()

        # ----------------------------------------------------------------------
        # DRAWING UI (Re-sync active screen & cursor index after event handling)
        # ----------------------------------------------------------------------
        current_screen = screen_stack[-1]
        selected_idx = selected_indices.get(current_screen, 0)
        panel_margin = 40
        foot_h = 56
        foot_y = state.SCREEN_H - foot_h

        fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 13, 17, 28, 255)

        # 1. Header Bar
        header_h = HEADER_H
        fill_rect(0, 0, state.SCREEN_W, header_h, 20, 28, 46, 255)
        fill_rect(0, header_h - 2, state.SCREEN_W, 2, 0, 246, 246, 255)

        _head_txt = tr("yt_search_title") if current_screen == "yt_search_input" else (tr("search_title") if current_screen == "search_input" else header_title)
        draw_text(_head_txt, font_title, 40, header_h // 2, 255, 255, 255, center_y=True)
        # Version sits beside the app name on the home screen only. Measured
        # rather than placed at a guessed offset, because the title is translated
        # and the two languages are not the same width.
        if current_screen == "home":
            draw_text("v" + APP_VERSION, font_sub,
                      40 + measure_text(_head_txt, font_title) + 14,
                      header_h // 2 + 4, 120, 145, 180, center_y=True)
        # Battery readout removed from the header: it carried emoji the bundled font
        # has no glyphs for, and its second line sat below the shortened bar.
        # Battery still shows in Device Info.

        # ----------------------------------------------------------------------
        # SCREEN: YOUTUBE SEARCH INPUT & VIRTUAL KEYBOARD
        # ----------------------------------------------------------------------
        if current_screen == "yt_search_input":
            box_x = 40
            box_y = 108
            box_w = state.SCREEN_W - 80
            box_h = 58
            fill_rect(box_x, box_y, box_w, box_h, 20, 28, 48, 255)
            draw_rect(box_x, box_y, box_w, box_h, 0, 230, 255, 255, thickness=2)

            cursor_str = "_" if int(time.time() * 2) % 2 == 0 else ""
            disp_query = yt_input_text + cursor_str if yt_input_text else tr("search_prompt") + cursor_str
            q_col = (255, 255, 255) if yt_input_text else (120, 140, 170)
            draw_text(disp_query, font_item, box_x + 20, box_y + box_h // 2, q_col[0], q_col[1], q_col[2], center_y=True)

            kb_start_y = box_y + box_h + 16
            k_row_gap = 12
            k_col_gap = 10
            k_h = 56

            for r_idx, row in enumerate(kb_rows):
                num_k = len(row)
                total_w = state.SCREEN_W - 80
                k_w = (total_w - (num_k - 1) * k_col_gap) // num_k
                ky = kb_start_y + r_idx * (k_h + k_row_gap)

                for c_idx, key_str in enumerate(row):
                    kx = 40 + c_idx * (k_w + k_col_gap)
                    is_k_sel = (kb_cursor[0] == r_idx and kb_cursor[1] == c_idx)

                    if is_k_sel:
                        fill_rect(kx, ky, k_w, k_h, 0, 230, 255, 255)
                        draw_rect(kx, ky, k_w, k_h, 255, 255, 255, 255, thickness=2)
                        draw_text(key_str, font_kb, kx + k_w // 2, ky + k_h // 2, 0, 20, 40, center_x=True, center_y=True)
                    else:
                        fill_rect(kx, ky, k_w, k_h, 24, 34, 56, 255)
                        draw_rect(kx, ky, k_w, k_h, 45, 65, 100, 255, thickness=1)
                        draw_text(key_str, font_kb, kx + k_w // 2, ky + k_h // 2, 220, 230, 245, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # SCREEN: YOUTUBE 3x2 GRID VIEW
        # ----------------------------------------------------------------------
        elif current_screen == "yt_grid":
            cur_videos = yt_trending_list if yt_mode == "trending" else yt_search_results_list
            total_v = len(cur_videos)
            scroll_row = scroll_offsets.get("yt_grid", 0)

            # Draw counter badge in top right of header
            if total_v > 0:
                cnt_str = f"{selected_idx + 1} / {total_v}"
                cw = measure_text(cnt_str, font_sub)
                draw_text(cnt_str, font_sub, state.SCREEN_W - 40 - cw, header_h // 2, 0, 246, 246, center_y=True)

            # ------------------------------------------------------------------
            # TOP BAR: RECENT SEARCH KEYWORDS (L1 / R1 TO SWITCH)
            # ------------------------------------------------------------------
            bar_y = 66
            bar_h = 38
            fill_rect(0, bar_y, state.SCREEN_W, bar_h, 17, 24, 40, 245)
            fill_rect(0, bar_y + bar_h - 1, state.SCREEN_W, 1, 35, 48, 72, 255)

            # Navigation hints (safe ASCII to avoid font missing glyph issues)
            draw_text("< L1", font_footer, 20, bar_y + bar_h // 2, 0, 220, 245, center_y=True)
            r1_txt = "R1 >"
            r1_w = measure_text(r1_txt, font_footer)
            draw_text(r1_txt, font_footer, state.SCREEN_W - 20 - r1_w, bar_y + bar_h // 2, 0, 220, 245, center_y=True)

            # Calculate pills dimensions
            pill_area_x = 90
            pill_area_w = state.SCREEN_W - 180
            pill_gap = 10
            pill_h = 26
            pill_y = bar_y + (bar_h - pill_h) // 2

            pills_w = []
            for q_item in yt_recent_queries:
                pw = measure_text(q_item, font_badge) + 24
                pills_w.append(pw)

            total_pills_w = sum(pills_w) + (len(pills_w) - 1) * pill_gap if pills_w else 0

            # Determine scroll offset for pills
            pill_x_pos = []
            cur_px = 0
            for pw in pills_w:
                pill_x_pos.append(cur_px)
                cur_px += pw + pill_gap

            safe_q_idx = max(0, min(len(pills_w) - 1, yt_query_idx)) if pills_w else 0

            if not pills_w or total_pills_w <= pill_area_w:
                base_x = pill_area_x + max(0, (pill_area_w - total_pills_w) // 2)
            else:
                # Center active pill in pill_area safely
                active_center = pill_x_pos[safe_q_idx] + pills_w[safe_q_idx] // 2
                desired_offset = (pill_area_w // 2) - active_center
                max_scroll = 0
                min_scroll = pill_area_w - total_pills_w
                scroll_offset_x = max(min_scroll, min(max_scroll, desired_offset))
                base_x = pill_area_x + scroll_offset_x

            # Draw keyword pills safely
            num_pills = min(len(yt_recent_queries), len(pills_w), len(pill_x_pos))
            for q_i in range(num_pills):
                q_txt = yt_recent_queries[q_i]
                px = base_x + pill_x_pos[q_i]
                pw = pills_w[q_i]
                if px + pw < pill_area_x - 10 or px > pill_area_x + pill_area_w + 10:
                    continue # outside view

                is_active_q = (q_i == safe_q_idx)
                if is_active_q:
                    fill_rect(px, pill_y, pw, pill_h, 0, 185, 235, 255)
                    draw_rect(px, pill_y, pw, pill_h, 255, 255, 255, 255, thickness=2)
                    draw_text(q_txt, font_badge, px + pw // 2, pill_y + pill_h // 2, 10, 24, 45, center_x=True, center_y=True)
                else:
                    fill_rect(px, pill_y, pw, pill_h, 25, 35, 54, 230)
                    draw_rect(px, pill_y, pw, pill_h, 48, 66, 94, 255, thickness=1)
                    draw_text(q_txt, font_badge, px + pw // 2, pill_y + pill_h // 2, 180, 205, 235, center_x=True, center_y=True)

            if total_v == 0:
                if yt_loading_state.get("active"):
                    q_disp = yt_loading_state.get("query", "")
                    num_dots = int(now * 3.5) % 4
                    dots = "." * num_dots
                    msg_main = f"Đang tải video \"{q_disp}\"{dots}" if state.current_lang == "VI" else f"Loading \"{q_disp}\"{dots}"
                    draw_text(msg_main, font_item, state.SCREEN_W // 2, state.SCREEN_H // 2 - 12, 0, 246, 246, center_x=True, center_y=True)
                    sub_hint = "Đang kết nối YouTube InnerTube API..." if state.current_lang == "VI" else "Connecting to YouTube InnerTube API..."
                    draw_text(sub_hint, font_sub, state.SCREEN_W // 2, state.SCREEN_H // 2 + 26, 140, 175, 210, center_x=True, center_y=True)
                else:
                    draw_text(tr("yt_no_results"), font_item, state.SCREEN_W // 2, state.SCREEN_H // 2 + 20, 160, 180, 210, center_x=True, center_y=True)
            else:
                cols = 3
                rows = 2
                gap_x = 26
                gap_y = 14
                card_w = 348
                card_h = 250
                start_x = (state.SCREEN_W - (cols * card_w + (cols - 1) * gap_x)) // 2
                start_y = 112

                for r_off in range(rows):
                    cur_r = scroll_row + r_off
                    for c_off in range(cols):
                        idx = cur_r * cols + c_off
                        if idx >= total_v:
                            continue

                        cx = start_x + c_off * (card_w + gap_x)
                        cy = start_y + r_off * (card_h + gap_y)
                        is_sel = (idx == selected_idx)
                        v_data = cur_videos[idx]

                        # Card Background & Border
                        if is_sel:
                            fill_rect(cx, cy, card_w, card_h, 24, 38, 64, 255)
                            draw_rect(cx, cy, card_w, card_h, 0, 230, 255, 255, thickness=3)
                        else:
                            fill_rect(cx, cy, card_w, card_h, 18, 24, 40, 240)
                            draw_rect(cx, cy, card_w, card_h, 36, 48, 76, 255, thickness=1)

                        # Thumbnail Area (Standard 16:9 YouTube ratio: 320x180)
                        tw = 320
                        th = 180
                        tx = cx + (card_w - tw) // 2
                        ty = cy + 8

                        v_id = v_data.get("id", "")
                        t_path = os.path.join(YT_CACHE_DIR, f"{v_id}.jpg") if v_id else ""
                        tex, orig_w, orig_h = (None, 0, 0)
                        if os.path.exists(t_path):
                            missing_img_cache.discard(t_path)
                            tex, orig_w, orig_h = get_texture_and_size(t_path)

                        if tex:
                            # Proportional fit preserving standard 16:9 aspect ratio
                            if orig_w > 0 and orig_h > 0:
                                scale = min(tw / float(orig_w), th / float(orig_h))
                                dw = int(orig_w * scale)
                                dh = int(orig_h * scale)
                                dx = tx + (tw - dw) // 2
                                dy = ty + (th - dh) // 2
                                dest_r = sdl2.SDL_Rect(dx, dy, dw, dh)
                            else:
                                dest_r = sdl2.SDL_Rect(tx, ty, tw, th)
                            sdl2.SDL_RenderCopy(renderer, tex, None, dest_r)
                        else:
                            fill_rect(tx, ty, tw, th, 12, 16, 26, 255)
                            draw_rect(tx, ty, tw, th, 30, 42, 65, 255, thickness=1)
                            pw, ph = 50, 34
                            px = tx + (tw - pw) // 2
                            py = ty + (th - ph) // 2
                            fill_rect(px, py, pw, ph, 230, 33, 23, 255)
                            draw_text("▶", font_badge, px + pw // 2, py + ph // 2, 255, 255, 255, center_x=True, center_y=True)

                        # Duration badge in bottom-right of thumbnail
                        dur_str = v_data.get("duration", "")
                        if dur_str:
                            dw = measure_text(dur_str, font_badge) + 12
                            dh = 22
                            dx = tx + tw - dw - 6
                            dy = ty + th - dh - 6
                            fill_rect(dx, dy, dw, dh, 0, 0, 0, 220)
                            draw_rect(dx, dy, dw, dh, 50, 50, 50, 255, thickness=1)
                            draw_text(dur_str, font_badge, dx + dw // 2, dy + dh // 2, 255, 255, 255, center_x=True, center_y=True)

                        # Title below thumbnail
                        text_y = ty + th + 6
                        disp_title = v_data.get("title", "Video")
                        if len(disp_title) > 30:
                            disp_title = disp_title[:28] + "..."
                        title_col = (255, 255, 255) if is_sel else (205, 215, 230)
                        draw_text(disp_title, font_sub, cx + 14, text_y, title_col[0], title_col[1], title_col[2])

                        # Channel name
                        chan_name = v_data.get("channel", "")
                        if len(chan_name) > 32:
                            chan_name = chan_name[:30] + "..."
                        chan_col = (0, 220, 240) if is_sel else (120, 145, 175)
                        draw_text(chan_name, font_badge, cx + 14, text_y + 24, chan_col[0], chan_col[1], chan_col[2])

        # ----------------------------------------------------------------------
        # SCREEN: SEARCH INPUT & VIRTUAL KEYBOARD WITH SYSTEM FILTER BAR
        # ----------------------------------------------------------------------
        elif current_screen == "search_input":
            cur_filter_sys = sys_keys_list[search_sys_idx]
            sys_disp_name = (tr("search_scope_all") if cur_filter_sys == "ALL"
                             else get_system_display_name(cur_filter_sys))
            src_disp_name = tr(f"src_{search_source.lower()}")

            # Two pickers side by side. Each opens a list rather than stepping
            # through values, which for 30 systems was a lot of presses.
            fb_y = 108
            fb_h = 54
            fb_gap = 16
            fb_w = (state.SCREEN_W - 80 - fb_gap) // 2
            for i, (btn, lbl, val) in enumerate((
                    ("L1", tr("search_scope_lbl"), sys_disp_name),
                    ("R1", tr("search_src_lbl"), src_disp_name))):
                bx = 40 + i * (fb_w + fb_gap)
                fill_rect(bx, fb_y, fb_w, fb_h, 24, 34, 58, 255)
                draw_rect(bx, fb_y, fb_w, fb_h, 0, 230, 255, 255, thickness=2)
                draw_text(f"[{btn}] {lbl}", font_footer, bx + 16, fb_y + 15,
                          0, 230, 255, center_y=True)
                if len(val) > 24:
                    val = val[:22] + "..."
                draw_text(val, font_badge, bx + 16, fb_y + 38, 255, 255, 255, center_y=True)

            box_x = 40
            box_y = fb_y + fb_h + 12
            box_w = state.SCREEN_W - 80
            box_h = 58
            fill_rect(box_x, box_y, box_w, box_h, 20, 28, 48, 255)
            draw_rect(box_x, box_y, box_w, box_h, 60, 85, 130, 255, thickness=1)

            cursor_str = "_" if int(time.time() * 2) % 2 == 0 else ""
            disp_query = search_query + cursor_str if search_query else tr("search_prompt") + cursor_str
            q_col = (255, 255, 255) if search_query else (120, 140, 170)
            draw_text(disp_query, font_item, box_x + 20, box_y + box_h // 2, q_col[0], q_col[1], q_col[2], center_y=True)

            # Anchored to the query box instead of a fixed offset: the fixed value
            # put the first key row 20px inside the box.
            kb_start_y = box_y + box_h + 16
            k_row_gap = 12
            k_col_gap = 10
            k_h = 56

            for r_idx, row in enumerate(kb_rows):
                num_k = len(row)
                total_w = state.SCREEN_W - 80
                k_w = (total_w - (num_k - 1) * k_col_gap) // num_k
                ky = kb_start_y + r_idx * (k_h + k_row_gap)

                for c_idx, key_str in enumerate(row):
                    kx = 40 + c_idx * (k_w + k_col_gap)
                    is_k_sel = (kb_cursor[0] == r_idx and kb_cursor[1] == c_idx)

                    if is_k_sel:
                        fill_rect(kx, ky, k_w, k_h, 0, 230, 255, 255)
                        draw_rect(kx, ky, k_w, k_h, 255, 255, 255, 255, thickness=2)
                        draw_text(key_str, font_kb, kx + k_w // 2, ky + k_h // 2, 0, 20, 40, center_x=True, center_y=True)
                    else:
                        fill_rect(kx, ky, k_w, k_h, 24, 34, 56, 255)
                        draw_rect(kx, ky, k_w, k_h, 45, 65, 100, 255, thickness=1)
                        draw_text(key_str, font_kb, kx + k_w // 2, ky + k_h // 2, 220, 230, 245, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # SCREEN: DOWNLOADED GAMES - GRID MODE (2-LINE TITLE WRAP & NO EXTRA META)
        # ----------------------------------------------------------------------
        elif current_screen == "downloaded_games" and state.downloaded_view_mode == "grid" and len(lib_games_list) > 0:
            cols = 3
            rows = 2
            per_page = cols * rows
            cur_page = selected_idx // per_page
            page_start = cur_page * per_page
            visible_games = lib_games_list[page_start : page_start + per_page]

            grid_margin_x = 40
            grid_margin_y = CONTENT_TOP
            card_gap_x = 20
            card_gap_y = 16
            card_w = (state.SCREEN_W - (grid_margin_x * 2) - (card_gap_x * (cols - 1))) // cols
            card_h = (state.SCREEN_H - grid_margin_y - 80 - card_gap_y) // rows

            for i, dg in enumerate(visible_games):
                actual_idx = page_start + i
                c_row = i // cols
                c_col = i % cols
                cx = grid_margin_x + c_col * (card_w + card_gap_x)
                cy = grid_margin_y + c_row * (card_h + card_gap_y)
                is_sel = (actual_idx == selected_idx)

                if is_sel:
                    fill_rect(cx, cy, card_w, card_h, 28, 44, 75, 255)
                    draw_rect(cx, cy, card_w, card_h, 0, 246, 246, 255, thickness=3)
                else:
                    fill_rect(cx, cy, card_w, card_h, 19, 26, 42, 255)
                    draw_rect(cx, cy, card_w, card_h, 40, 54, 85, 255, thickness=1)

                img_area_x = cx + 8
                img_area_y = cy + 8
                img_area_w = card_w - 16
                img_area_h = card_h - 76

                fill_rect(img_area_x, img_area_y, img_area_w, img_area_h, 12, 16, 26, 255)

                drawn = False
                if dg.get("img_path"):
                    drawn = draw_proportional_boxart(dg["img_path"], img_area_x, img_area_y, img_area_w, img_area_h)
                if not drawn:
                    draw_default_boxart_avatar(img_area_x, img_area_y, img_area_w, img_area_h, dg.get("sys_code", "ROM"), dg.get("title", "Game"))

                title_lines = wrap_title_2lines(dg["title"], max_chars_per_line=17)
                t_color = (255, 255, 255) if is_sel else (210, 220, 235)

                if len(title_lines) == 1:
                    draw_text(title_lines[0], font_grid_title, cx + card_w // 2, cy + card_h - 32, t_color[0], t_color[1], t_color[2], center_x=True, center_y=True)
                else:
                    draw_text(title_lines[0], font_grid_title, cx + card_w // 2, cy + card_h - 45, t_color[0], t_color[1], t_color[2], center_x=True, center_y=True)
                    draw_text(title_lines[1], font_grid_title, cx + card_w // 2, cy + card_h - 19, t_color[0], t_color[1], t_color[2], center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # SCREEN: SPLASH PREVIEW (FULLSCREEN IMAGE + BOTTOM HUD)
        # ----------------------------------------------------------------------
        elif current_screen == "splash_preview":
            draw_proportional_boxart(splash_preview_path, 0, 0, state.SCREEN_W, state.SCREEN_H)
            
            hud_x = 30
            hud_w = state.SCREEN_W - 60
            hud_h = 106
            hud_y = state.SCREEN_H - hud_h - 25

            fill_rect(hud_x, hud_y, hud_w, hud_h, 15, 22, 38, 240)
            draw_rect(hud_x, hud_y, hud_w, hud_h, 0, 230, 255, 255, thickness=2)
            fill_rect(hud_x + 3, hud_y + 4, 8, hud_h - 8, 0, 246, 246, 255)

            draw_text(tr("splash_preview_title"), font_item, hud_x + 25, hud_y + 30, 0, 246, 246, center_y=True)
            disp_fname = splash_preview_orig_name
            if len(disp_fname) > 34:
                disp_fname = disp_fname[:31] + "..."
            draw_text(f"File: {disp_fname}  |  Chuẩn: {state.SCREEN_W}x{state.SCREEN_H} PNG", font_sub, hud_x + 25, hud_y + 70, 220, 230, 245, center_y=True)

            btn1_w = 260
            btn1_h = 44
            btn1_x = hud_x + hud_w - btn1_w - 20
            btn1_y = hud_y + 14
            fill_rect(btn1_x, btn1_y, btn1_w, btn1_h, 0, 180, 90, 255)
            draw_rect(btn1_x, btn1_y, btn1_w, btn1_h, 0, 255, 160, 255, thickness=2)
            draw_text(f"[A] {tr('splash_btn_apply')}", font_badge, btn1_x + btn1_w // 2, btn1_y + btn1_h // 2, 0, 0, 0, center_x=True, center_y=True)

            btn2_w = 260
            btn2_h = 36
            btn2_x = hud_x + hud_w - btn2_w - 20
            btn2_y = hud_y + 60
            fill_rect(btn2_x, btn2_y, btn2_w, btn2_h, 35, 45, 65, 255)
            draw_rect(btn2_x, btn2_y, btn2_w, btn2_h, 80, 95, 130, 255, thickness=1)
            draw_text(f"[B] {tr('splash_btn_cancel')}", font_sub, btn2_x + btn2_w // 2, btn2_y + btn2_h // 2, 200, 210, 230, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # SCREEN: SPLASH MANAGER & FILE BROWSER (SPLIT LIST + PREVIEW THUMBNAIL)
        # ----------------------------------------------------------------------
        elif current_screen in ("splash_manager", "file_browser"):
            left_w = int(state.SCREEN_W * 0.56)
            right_w = state.SCREEN_W - left_w - 60
            panel_x = 30
            card_h = 76
            gap = 10
            start_y = CONTENT_TOP
            max_visible = 6
            cur_scroll = scroll_offsets.get(current_screen, 0)
            if selected_idx < cur_scroll:
                cur_scroll = selected_idx
            elif selected_idx >= cur_scroll + max_visible:
                cur_scroll = selected_idx - max_visible + 1
            cur_scroll = max(0, min(max(0, len(items) - max_visible), cur_scroll))
            scroll_offsets[current_screen] = cur_scroll
            scroll_offset = cur_scroll

            if len(items) > max_visible:
                visible_items = items[scroll_offset : scroll_offset + max_visible]
            else:
                visible_items = items

            for i, item in enumerate(visible_items):
                actual_idx = i + scroll_offset
                cy = start_y + i * (card_h + gap)
                is_sel = (actual_idx == selected_idx)

                if is_sel:
                    fill_rect(panel_x, cy, left_w, card_h, 28, 44, 75, 255)
                    draw_rect(panel_x, cy, left_w, card_h, 0, 246, 246, 255, thickness=3)
                    fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                    text_r, text_g, text_b = 255, 255, 255
                else:
                    fill_rect(panel_x, cy, left_w, card_h, 19, 26, 42, 255)
                    draw_rect(panel_x, cy, left_w, card_h, 40, 54, 85, 255, thickness=1)
                    text_r, text_g, text_b = 200, 210, 225

                disp_title = item["title"]
                if len(disp_title) > 28:
                    disp_title = disp_title[:25] + "..."

                if item.get("is_restore"):
                    draw_text(disp_title, font_item, panel_x + 22, cy + (card_h // 2), 255, 215, 0, center_y=True)
                elif item.get("is_browse"):
                    draw_text(disp_title, font_item, panel_x + 22, cy + (card_h // 2), 0, 230, 255, center_y=True)
                elif item.get("type") == "dir" or item.get("id") == "fb_up":
                    draw_text(disp_title, font_item, panel_x + 22, cy + (card_h // 2), 0, 230, 255, center_y=True)
                else:
                    draw_text(disp_title, font_item, panel_x + 22, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

            rx = panel_x + left_w + 20
            ry = start_y
            rw = right_w
            rh = state.SCREEN_H - start_y - 75

            fill_rect(rx, ry, rw, rh, 18, 25, 42, 255)
            draw_rect(rx, ry, rw, rh, 0, 230, 255, 255, thickness=2)

            cur_item = items[selected_idx] if selected_idx < len(items) else None
            if cur_item:
                box_x = rx + 25
                box_y = ry + 60
                box_w_target = rw - 50
                box_h_target = rh - 170

                fill_rect(box_x, box_y, box_w_target, box_h_target, 12, 16, 26, 255)
                draw_rect(box_x, box_y, box_w_target, box_h_target, 45, 65, 100, 255, thickness=1)

                if cur_item.get("is_restore"):
                    fill_rect(rx + 10, ry + 12, rw - 20, 38, 50, 40, 20, 255)
                    draw_text("ẢNH KHỞI ĐỘNG MẶC ĐỊNH (GỐC)", font_badge, rx + rw // 2, ry + 31, 255, 215, 0, center_x=True, center_y=True)
                    restore_prev_p = SPLASH_BACKUP_FILE if os.path.exists(SPLASH_BACKUP_FILE) else "/rom/etc/splash.png"
                    drawn = draw_proportional_boxart(restore_prev_p, box_x + 4, box_y + 4, box_w_target - 8, box_h_target - 8)
                    if not drawn:
                        draw_text(tr("splash_orig_preview"), font_sub, box_x + box_w_target // 2, box_y + box_h_target // 2, 120, 140, 170, center_x=True, center_y=True)

                    ab_w = rw - 40
                    ab_h = 48
                    ab_x = rx + 20
                    ab_y = ry + rh - ab_h - 15
                    fill_rect(ab_x, ab_y, ab_w, ab_h, 180, 140, 20, 255)
                    draw_rect(ab_x, ab_y, ab_w, ab_h, 255, 215, 0, 255, thickness=2)
                    draw_text("[A] KHÔI PHỤC ẢNH GỐC", font_badge, ab_x + ab_w // 2, ab_y + ab_h // 2, 0, 0, 0, center_x=True, center_y=True)

                elif cur_item.get("is_browse"):
                    fill_rect(rx + 10, ry + 12, rw - 20, 38, 20, 45, 65, 255)
                    draw_text("TRÌNH DUYỆT THẺ NHỚ", font_badge, rx + rw // 2, ry + 31, 0, 230, 255, center_x=True, center_y=True)
                    draw_text("DUYỆT FILE SD CARD", font_item, box_x + box_w_target // 2, box_y + box_h_target // 2 - 15, 0, 246, 246, center_x=True, center_y=True)
                    draw_text("Hỗ trợ .png, .jpg, .bmp", font_sub, box_x + box_w_target // 2, box_y + box_h_target // 2 + 25, 170, 185, 210, center_x=True, center_y=True)

                    ab_w = rw - 40
                    ab_h = 48
                    ab_x = rx + 20
                    ab_y = ry + rh - ab_h - 15
                    fill_rect(ab_x, ab_y, ab_w, ab_h, 0, 140, 200, 255)
                    draw_rect(ab_x, ab_y, ab_w, ab_h, 0, 230, 255, 255, thickness=2)
                    draw_text("[A] MỞ TRÌNH DUYỆT TỆP", font_badge, ab_x + ab_w // 2, ab_y + ab_h // 2, 255, 255, 255, center_x=True, center_y=True)

                elif cur_item.get("type") == "dir" or cur_item.get("id") == "fb_up":
                    fill_rect(rx + 10, ry + 12, rw - 20, 38, 20, 45, 65, 255)
                    draw_text("THƯ MỤC", font_badge, rx + rw // 2, ry + 31, 0, 230, 255, center_x=True, center_y=True)
                    draw_text(f"{cur_item['title']}", font_item, box_x + box_w_target // 2, box_y + box_h_target // 2 - 15, 0, 246, 246, center_x=True, center_y=True)
                    draw_text("Bấm [A] để mở thư mục này", font_sub, box_x + box_w_target // 2, box_y + box_h_target // 2 + 25, 170, 185, 210, center_x=True, center_y=True)

                    ab_w = rw - 40
                    ab_h = 48
                    ab_x = rx + 20
                    ab_y = ry + rh - ab_h - 15
                    fill_rect(ab_x, ab_y, ab_w, ab_h, 0, 140, 200, 255)
                    draw_rect(ab_x, ab_y, ab_w, ab_h, 0, 230, 255, 255, thickness=2)
                    draw_text("[A] MỞ THƯ MỤC", font_badge, ab_x + ab_w // 2, ab_y + ab_h // 2, 255, 255, 255, center_x=True, center_y=True)

                elif "img_data" in cur_item or cur_item.get("type") == "file":
                    p = cur_item["path"]
                    sz_s = cur_item.get("size_str", "")
                    d_s = cur_item.get("dir", "File")
                    fill_rect(rx + 10, ry + 12, rw - 20, 38, 28, 40, 68, 255)
                    draw_text(f"[{d_s}] {sz_s}", font_badge, rx + rw // 2, ry + 31, 0, 246, 246, center_x=True, center_y=True)

                    drawn = draw_proportional_boxart(p, box_x + 4, box_y + 4, box_w_target - 8, box_h_target - 8)
                    if not drawn:
                        draw_text("PREVIEW", font_sub, box_x + box_w_target // 2, box_y + box_h_target // 2, 120, 140, 170, center_x=True, center_y=True)

                    ab_w = rw - 40
                    ab_h = 48
                    ab_x = rx + 20
                    ab_y = ry + rh - ab_h - 15
                    fill_rect(ab_x, ab_y, ab_w, ab_h, 0, 180, 90, 255)
                    draw_rect(ab_x, ab_y, ab_w, ab_h, 0, 255, 160, 255, thickness=2)
                    draw_text("[A] XEM TRƯỚC & ÁP DỤNG", font_badge, ab_x + ab_w // 2, ab_y + ab_h // 2, 0, 0, 0, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # SCREEN: DOWNLOADED GAMES - LIST MODE (SPLIT VIEW)
        # ----------------------------------------------------------------------
        elif current_screen == "downloaded_games" and state.downloaded_view_mode == "list" and len(lib_games_list) > 0:
            left_w = int(state.SCREEN_W * 0.60)
            right_w = state.SCREEN_W - left_w - 60
            panel_x = 30
            card_h = 76
            gap = 10
            start_y = CONTENT_TOP
            max_visible = 6
            cur_scroll = scroll_offsets.get(current_screen, 0)
            if selected_idx < cur_scroll:
                cur_scroll = selected_idx
            elif selected_idx >= cur_scroll + max_visible:
                cur_scroll = selected_idx - max_visible + 1
            cur_scroll = max(0, min(max(0, len(items) - max_visible), cur_scroll))
            scroll_offsets[current_screen] = cur_scroll
            scroll_offset = cur_scroll

            if len(items) > max_visible:
                visible_items = items[scroll_offset : scroll_offset + max_visible]
            else:
                visible_items = items

            for i, item in enumerate(visible_items):
                actual_idx = i + scroll_offset
                cy = start_y + i * (card_h + gap)
                is_sel = (actual_idx == selected_idx)

                if is_sel:
                    fill_rect(panel_x, cy, left_w, card_h, 28, 44, 75, 255)
                    draw_rect(panel_x, cy, left_w, card_h, 0, 246, 246, 255, thickness=3)
                    fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                    text_r, text_g, text_b = 255, 255, 255
                else:
                    fill_rect(panel_x, cy, left_w, card_h, 19, 26, 42, 255)
                    draw_rect(panel_x, cy, left_w, card_h, 40, 54, 85, 255, thickness=1)
                    text_r, text_g, text_b = 200, 210, 225

                disp_title = item["title"]
                if len(disp_title) > 30:
                    disp_title = disp_title[:27] + "..."
                draw_text(disp_title, font_item, panel_x + 22, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

            rx = panel_x + left_w + 20
            ry = start_y
            rw = right_w
            rh = state.SCREEN_H - start_y - 75

            fill_rect(rx, ry, rw, rh, 18, 25, 42, 255)
            draw_rect(rx, ry, rw, rh, 0, 230, 255, 255, thickness=2)

            cur_item = items[selected_idx] if selected_idx < len(items) else None
            if cur_item and "game_data" in cur_item:
                dg = cur_item["game_data"]
                fill_rect(rx + 10, ry + 12, rw - 20, 42, 28, 40, 68, 255)
                draw_text(f"{dg['sys_name']}", font_badge, rx + rw // 2, ry + 33, 0, 246, 246, center_x=True, center_y=True)

                box_x = rx + 25
                box_y = ry + 66
                box_w_target = rw - 50
                box_h_target = rh - 180

                fill_rect(box_x, box_y, box_w_target, box_h_target, 12, 16, 26, 255)
                draw_rect(box_x, box_y, box_w_target, box_h_target, 45, 65, 100, 255, thickness=1)

                drawn = False
                if dg.get("img_path"):
                    drawn = draw_proportional_boxart(dg["img_path"], box_x + 6, box_y + 6, box_w_target - 12, box_h_target - 12)
                if not drawn:
                    draw_default_boxart_avatar(box_x + 6, box_y + 6, box_w_target - 12, box_h_target - 12, dg.get("sys_code", "ROM"), dg.get("title", "Game"))

                ab_w = rw - 40
                ab_h = 50
                ab_x = rx + 20
                ab_y = ry + rh - ab_h - 15
                fill_rect(ab_x, ab_y, ab_w, ab_h, 0, 190, 100, 255)
                draw_rect(ab_x, ab_y, ab_w, ab_h, 0, 255, 160, 255, thickness=2)
                draw_text(tr("btn_play_now"), font_badge, ab_x + ab_w // 2, ab_y + ab_h // 2, 0, 0, 0, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # STANDARD FULL-WIDTH LIST VIEW
        # ----------------------------------------------------------------------
        else:
            num_items = len(items)
            panel_margin = 40
            panel_x = panel_margin
            panel_w = state.SCREEN_W - (panel_margin * 2)

            if num_items <= 5:
                card_h = 86
                gap = 14
                start_y = CONTENT_TOP + 8
            else:
                card_h = 76
                gap = 10
                start_y = CONTENT_TOP

            max_visible = 6
            cur_scroll = scroll_offsets.get(current_screen, 0)
            if selected_idx < cur_scroll:
                cur_scroll = selected_idx
            elif selected_idx >= cur_scroll + max_visible:
                cur_scroll = selected_idx - max_visible + 1
            cur_scroll = max(0, min(max(0, num_items - max_visible), cur_scroll))
            scroll_offsets[current_screen] = cur_scroll
            scroll_offset = cur_scroll

            if num_items > max_visible:
                visible_items = items[scroll_offset : scroll_offset + max_visible]
            else:
                visible_items = items

            for i, item in enumerate(visible_items):
                actual_idx = i + scroll_offset
                cy = start_y + i * (card_h + gap)
                is_sel = (actual_idx == selected_idx)
                is_sub = item.get("sub", False)
                is_lang = item.get("is_lang", False)
                if not item.get("downloaded") and item.get("game_info"):
                    _dst = download_state_for(item["game_info"])
                    if _dst == "downloading":
                        item["label"] = tr("dling_badge")
                    elif _dst == "queued":
                        item["label"] = tr("dl_queue_badge")
                    else:
                        item["label"] = tr("download_badge")
                has_label = bool(item.get("label"))

                if is_sel:
                    fill_rect(panel_x, cy, panel_w, card_h, 28, 44, 75, 255)
                    draw_rect(panel_x, cy, panel_w, card_h, 0, 246, 246, 255, thickness=3)
                    fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                    text_r, text_g, text_b = 255, 255, 255
                else:
                    if is_sub:
                        fill_rect(panel_x, cy, panel_w, card_h, 15, 22, 36, 255)
                        draw_rect(panel_x, cy, panel_w, card_h, 0, 180, 220, 160, thickness=1)
                        text_r, text_g, text_b = 0, 225, 245
                    else:
                        fill_rect(panel_x, cy, panel_w, card_h, 19, 26, 42, 255)
                        draw_rect(panel_x, cy, panel_w, card_h, 40, 54, 85, 255, thickness=1)
                        text_r, text_g, text_b = 200, 210, 225

                if item.get("sub_title"):
                    disp_title = item["title"]
                    max_chars = 42 if has_label else 54
                    if len(disp_title) > max_chars:
                        disp_title = disp_title[:max_chars - 3] + "..."
                    draw_text(disp_title, font_item, panel_x + 28, cy + 22, text_r, text_g, text_b, center_y=True)
                    st_col = (0, 220, 240) if is_sel else (140, 160, 190)
                    draw_text(item["sub_title"], font_sub, panel_x + 28, cy + card_h - 22, st_col[0], st_col[1], st_col[2], center_y=True)
                else:
                    disp_title = item["title"]
                    max_chars = 46 if (has_label or item.get("type") == "toggle") else 58
                    if len(disp_title) > max_chars:
                        disp_title = disp_title[:max_chars - 3] + "..."
                    draw_text(disp_title, font_item, panel_x + 28, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

                if item.get("type") == "toggle":
                    sw_x = panel_x + panel_w - 110 - 24
                    sw_y = cy + (card_h - 48) // 2
                    draw_toggle(sw_x, sw_y, item["state"])
                elif item.get("is_active_dl"):
                    badge_w = 200
                    badge_h = 46
                    badge_x = panel_x + panel_w - badge_w - 24
                    badge_y = cy + (card_h - badge_h) // 2
                    fill_rect(badge_x, badge_y, badge_w, badge_h, 16, 48, 36, 255)
                    draw_rect(badge_x, badge_y, badge_w, badge_h, 0, 230, 140, 255, thickness=1)
                    draw_text(f"{dl_state['progress_pct']}%", font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 255, 160, center_x=True, center_y=True)
                elif is_lang:
                    badge_w = 92
                    badge_h = 52
                    badge_x = panel_x + panel_w - badge_w - 24
                    badge_y = cy + (card_h - badge_h) // 2

                    fill_rect(badge_x, badge_y, badge_w, badge_h, 24, 38, 64, 255)
                    draw_rect(badge_x, badge_y, badge_w, badge_h, 0, 246, 246, 255, thickness=2)
                    # A flag reads faster than a two-letter code. Fall back to the text
                    # badge if the image is missing, so the row never renders empty.
                    flag_p = FLAG_FILES.get(state.current_lang)
                    drawn_flag = False
                    if flag_p and os.path.exists(flag_p):
                        drawn_flag = draw_proportional_boxart(
                            flag_p, badge_x + 5, badge_y + 5, badge_w - 10, badge_h - 10)
                    if not drawn_flag:
                        draw_text(item["label"], font_badge, badge_x + badge_w // 2,
                                  badge_y + badge_h // 2, 0, 246, 246,
                                  center_x=True, center_y=True)
                elif has_label:
                    badge_w = 130
                    badge_h = 46
                    badge_x = panel_x + panel_w - badge_w - 24
                    badge_y = cy + (card_h - badge_h) // 2

                    if item.get("downloaded", False):
                        fill_rect(badge_x, badge_y, badge_w, badge_h, 16, 48, 36, 255)
                        draw_rect(badge_x, badge_y, badge_w, badge_h, 0, 230, 140, 255, thickness=1)
                        draw_text(item["label"], font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 255, 160, center_x=True, center_y=True)
                    elif is_sub:
                        fill_rect(badge_x, badge_y, badge_w, badge_h, 15, 45, 70, 255)
                        draw_rect(badge_x, badge_y, badge_w, badge_h, 0, 246, 246, 255, thickness=1)
                        draw_text(item["label"], font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 246, 246, center_x=True, center_y=True)
                    else:
                        fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                        draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                        draw_text(item["label"], font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 230, 255, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 3. FOOTER NAVIGATION BAR (CLEAN, MODULAR, NO OVERLAPPING)
        # ----------------------------------------------------------------------
        # FOOTER ACTION BAR
        # ----------------------------------------------------------------------
        if current_screen != "splash_preview":
            foot_h = 56
            foot_y = state.SCREEN_H - foot_h
            fill_rect(0, foot_y, state.SCREEN_W, foot_h, 10, 14, 24, 255)
            fill_rect(0, foot_y, state.SCREEN_W, 2, 35, 45, 75, 255)

            def draw_footer_btn(x, key_char, label_str, btn_color=(0, 230, 150), text_color=(220, 225, 235), is_dark_btn=True):
                b_size = 32
                b_y = foot_y + (foot_h - b_size) // 2
                fill_rect(x, b_y, b_size, b_size, btn_color[0], btn_color[1], btn_color[2], 255)
                font_btn_col = (0, 0, 0) if is_dark_btn else (255, 255, 255)
                draw_text(key_char, font_btn_badge, x + b_size // 2, b_y + b_size // 2, font_btn_col[0], font_btn_col[1], font_btn_col[2], center_x=True, center_y=True)
                w, h = draw_text(label_str, font_footer, x + b_size + 8, foot_y + foot_h // 2, text_color[0], text_color[1], text_color[2], center_y=True)
                return x + b_size + 8 + w + 20

            fx = 30
            # Common: [A] & [B]
            if current_screen == "file_browser":
                a_label = "Mở / Xem"
                b_label = "Thư mục cha / Lùi"
            elif current_screen == "splash_manager":
                a_label = "Xem & Cài đặt"
                b_label = "Quay lại"
            elif current_screen == "download_manager":
                a_label = "Chi tiết / Mở"
                b_label = "Quay lại"
            elif current_screen in ("core_sys", "core_pick"):
                a_label = "Chọn"
                b_label = "Quay lại"
            elif current_screen in ("network", "utilities"):
                a_label = "Bật / Tắt"
                b_label = "Quay lại" if len(screen_stack) > 1 else "Thoát"
            elif current_screen == "rom_java_cats":
                a_label = "Chọn nhóm"
                b_label = "Quay lại"
            elif current_screen == "rom_source_systems":
                a_label = "Chọn hệ máy"
                b_label = "Quay lại"
            elif current_screen == "rom_games":
                a_label = "Xem chi tiết"
                b_label = "Quay lại"
            else:
                a_label = "Chọn / Mở"
                b_label = "Quay lại" if len(screen_stack) > 1 else "Thoát"

            fx = draw_footer_btn(fx, "A", a_label, (0, 230, 150))
            fx = draw_footer_btn(fx, "B", b_label, (255, 70, 70), is_dark_btn=False)

            if current_screen == "download_manager":
                if dl_state.get("active") or dl_state.get("status") in ("downloading", "extracting"):
                    fx = draw_footer_btn(fx, "X", "Hủy tải", (255, 80, 80), is_dark_btn=False)
                draw_footer_btn(state.SCREEN_W - 190, "LR", "Lướt 10", (70, 95, 140), is_dark_btn=False)

            elif current_screen == "downloaded_games":
                # Physical X = Toggle view, Physical Y = Random, SELECT = filter
                fx = draw_footer_btn(fx, "X", "Đổi xem", (0, 190, 255))
                fx = draw_footer_btn(fx, "Y", "Random", (255, 200, 0))
                _f_lbl = "Lọc hệ" if current_lib_sys == "ALL" else f"Lọc: {current_lib_sys}"
                fx = draw_footer_btn(fx, "SL", _f_lbl, (140, 200, 90))
                draw_footer_btn(state.SCREEN_W - 190, "LR", "Lướt 10", (70, 95, 140), is_dark_btn=False)

            elif current_screen == "rom_games":
                if current_source != "HITS":
                    sort_btn_text = "Xếp A-Z" if state.rom_sort_mode == "downloads" else "Xếp Lượt tải"
                    fx = draw_footer_btn(fx, "X", sort_btn_text, (0, 190, 255))
                    fx = draw_footer_btn(fx, "Y", "Chữ cái", (255, 200, 0))
                draw_footer_btn(state.SCREEN_W - 190, "LR", "Lướt 10", (70, 95, 140), is_dark_btn=False)

            elif current_screen == "search_results":
                draw_footer_btn(state.SCREEN_W - 190, "LR", "Lướt 10", (70, 95, 140), is_dark_btn=False)

            elif current_screen == "yt_grid":
                fx = draw_footer_btn(fx, "A", "Xem", (0, 230, 140))
                fx = draw_footer_btn(fx, "X", "Tìm kiếm", (0, 190, 255))
                if yt_mode == "search" or yt_query_idx != 0:
                    fx = draw_footer_btn(fx, "Y", "Mặc định", (255, 180, 0))
                draw_footer_btn(state.SCREEN_W - 220, "L1/R1", "Từ khóa", (70, 95, 140), is_dark_btn=False)

            elif current_screen == "yt_search_input":
                fx = draw_footer_btn(fx, "X", "Cách", (0, 190, 255))
                fx = draw_footer_btn(fx, "Y", "Xóa", (255, 200, 0))
                fx = draw_footer_btn(fx, "ST", "Tìm", (255, 140, 0))

            elif current_screen == "search_input":
                fx = draw_footer_btn(fx, "X", "Cách", (0, 190, 255))
                fx = draw_footer_btn(fx, "Y", "Xóa", (255, 200, 0))
                fx = draw_footer_btn(fx, "ST", "Tìm", (255, 140, 0))
                draw_footer_btn(state.SCREEN_W - 190, "LR", "Hệ / Nguồn", (70, 95, 140), is_dark_btn=False)

            else:
                draw_footer_btn(state.SCREEN_W - 190, "LR", "Lướt 10", (70, 95, 140), is_dark_btn=False)

        # 4. Toast Notification
        if toast_msg and (now - toast_timer < 2.5) and not (current_screen == "yt_grid" and yt_loading_state.get("active")):
            toast_margin = 40
            tw = state.SCREEN_W - (toast_margin * 2)
            th = 44
            tx = toast_margin
            ty = (state.SCREEN_H - 56) - 52
            fill_rect(tx, ty, tw, th, 16, 32, 56, 245)
            draw_rect(tx, ty, tw, th, 0, 246, 246, 255, thickness=1)
            draw_text(toast_msg, font_toast, tx + tw // 2, ty + th // 2, 0, 246, 246, center_x=True, center_y=True)

        # 4.5. Mini Floating Download HUD (when running in background)
        if dl_state["active"] and dl_state.get("is_background", False) and current_screen != "splash_preview":
            hud_w = state.SCREEN_W - 60
            hud_h = 44
            hud_x = 30
            hud_y = foot_y - hud_h - 10

            fill_rect(hud_x, hud_y, hud_w, hud_h, 15, 24, 40, 245)
            draw_rect(hud_x, hud_y, hud_w, hud_h, 0, 230, 255, 255, thickness=2)

            if dl_state["status"] == "downloading":
                pct = dl_state["progress_pct"]
                pb_w = int(hud_w * (pct / 100.0))
                if pb_w > 0:
                    fill_rect(hud_x + 2, hud_y + hud_h - 4, pb_w - 4, 3, 0, 230, 150)

            g_title = dl_state["title"]
            if len(g_title) > 45:
                g_title = g_title[:42] + "..."
            hud_txt = f"[{dl_state['sys_code']}] {g_title} • {dl_state['progress_pct']}% ({dl_state['downloaded_str']})"
            draw_text(hud_txt, font_sub, hud_x + 18, hud_y + hud_h // 2 - 1, 0, 246, 246, center_y=True)

        # 4.6. Mini Floating YouTube Loading HUD (when fetching in background)
        if current_screen == "yt_grid" and yt_loading_state.get("active"):
            hud_w = state.SCREEN_W - 60
            hud_h = 44
            hud_x = 30
            hud_y = foot_y - hud_h - 10
            if dl_state.get("active") and dl_state.get("is_background", False):
                hud_y -= (hud_h + 8)

            fill_rect(hud_x, hud_y, hud_w, hud_h, 15, 24, 40, 248)
            draw_rect(hud_x, hud_y, hud_w, hud_h, 0, 220, 255, 255, thickness=2)

            # Animated glowing pulse scanning bar along bottom of HUD
            anim_offset = int((now * 420) % hud_w)
            pulse_w = 220
            p1 = min(pulse_w, hud_w - anim_offset)
            fill_rect(hud_x + anim_offset, hud_y + hud_h - 4, p1, 3, 0, 246, 246, 255)
            if anim_offset + pulse_w > hud_w:
                p2 = (anim_offset + pulse_w) - hud_w
                fill_rect(hud_x, hud_y + hud_h - 4, p2, 3, 0, 246, 246, 255)

            # Loading label
            q_name = yt_loading_state.get("query", "")
            eff_hint = yt.get_effective_query(q_name)
            num_dots = int(now * 3.5) % 4
            dots = "." * num_dots
            hud_txt = f"⏳ ĐANG TẢI DỮ LIỆU: \"{q_name}\"{dots}  ({eff_hint})" if state.current_lang == "VI" else f"⏳ LOADING: \"{q_name}\"{dots}  ({eff_hint})"
            draw_text(hud_txt, font_badge, hud_x + 20, hud_y + hud_h // 2 - 1, 0, 246, 246, center_y=True)

            wait_txt = "Đang kết nối..." if state.current_lang == "VI" else "Connecting..."
            ww = measure_text(wait_txt, font_badge)
            draw_text(wait_txt, font_badge, hud_x + hud_w - 20 - ww, hud_y + hud_h // 2 - 1, 255, 215, 0, center_y=True)


        # 5. Live Progress Bar Download Modal
        if dl_state["active"] and not dl_state.get("is_background", False):
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 210)

            mw = min(920, state.SCREEN_W - 60)
            mh = 430
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            fill_rect(mx + 3, my + 3, mw - 6, 72, 24, 34, 58, 255)
            head_txt = dl_state['title']
            # Two lines of the smaller font fit the existing 72px band, so a long
            # title wraps without pushing the rest of the modal out of place.
            head_lines = wrap_text_to_width(head_txt, font_item, mw - 90, max_lines=1)
            if measure_text(head_txt, font_item) > mw - 90:
                head_lines = wrap_text_to_width(head_txt, font_sub, mw - 70, max_lines=2)
                head_font, head_ys = font_sub, (my + 26, my + 54)
            else:
                head_font, head_ys = font_item, (my + 38,)
            for li, line in enumerate(head_lines[:len(head_ys)]):
                draw_text(line, head_font, mx + mw // 2, head_ys[li], 0, 246, 246,
                          center_x=True, center_y=True)

            # Metadata line: System, Size, Source
            src_str = dl_state.get("source_name", "Internet Archive")
            draw_text(f"[{dl_state['sys_code']}]  {tr('game_size')}{dl_state['size']}   |   {tr('dl_source_lbl')}{src_str}", font_sub, mx + 45, my + 105, 255, 215, 0)
            
            if dl_state["status"] in ("downloading", "extracting"):
                pb_x = mx + 45
                pb_y = my + 155
                pb_w = mw - 90
                pb_h = 34
                fill_rect(pb_x, pb_y, pb_w, pb_h, 24, 34, 56, 255)
                draw_rect(pb_x, pb_y, pb_w, pb_h, 60, 85, 130, 255, thickness=1)
                fill_w = int(pb_w * (dl_state["progress_pct"] / 100.0))
                if fill_w > 0:
                    fill_rect(pb_x + 2, pb_y + 2, fill_w - 4, pb_h - 4, 0, 230, 150, 255)

                # Modal ve nguyen van tung dong: ten file cua ban scene, hay
                # duong dan thu muc J2ME, dai hon be ngang khung thi chu chay
                # thang ra ngoai - dung nhu dong Errno tung bi cat cut o mep.
                lines = []
                for _raw in dl_state["msg"].split("\n"):
                    lines.extend(wrap_text_to_width(_raw, font_sub, mw - 90, max_lines=2))
                line_y = my + 215
                for l in lines:
                    draw_text(l, font_sub, mx + 45, line_y, 220, 230, 245)
                    line_y += 32

                btn_w = 220
                btn_h = 52
                gap_b = 30
                bx1 = mx + (mw - (btn_w * 2 + gap_b)) // 2
                bx2 = bx1 + btn_w + gap_b
                by = my + mh - 75

                fill_rect(bx1, by, btn_w, btn_h, 30, 60, 100, 255)
                draw_rect(bx1, by, btn_w, btn_h, 0, 230, 255, 255, thickness=1)
                draw_text(tr("dl_btn_minimize"), font_badge, bx1 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)

                fill_rect(bx2, by, btn_w, btn_h, 160, 45, 45, 255)
                draw_rect(bx2, by, btn_w, btn_h, 255, 80, 80, 255, thickness=1)
                draw_text(tr("dl_btn_cancel"), font_badge, bx2 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)

            elif dl_state["status"] == "success":
                # Modal ve nguyen van tung dong: ten file cua ban scene, hay
                # duong dan thu muc J2ME, dai hon be ngang khung thi chu chay
                # thang ra ngoai - dung nhu dong Errno tung bi cat cut o mep.
                lines = []
                for _raw in dl_state["msg"].split("\n"):
                    lines.extend(wrap_text_to_width(_raw, font_sub, mw - 90, max_lines=2))
                line_y = my + 155
                for l in lines:
                    draw_text(l, font_sub, mx + 45, line_y, 0, 246, 246)
                    line_y += 34

                btn_w = 220
                btn_h = 56
                gap_b = 30
                bx1 = mx + (mw - (btn_w * 2 + gap_b)) // 2
                bx2 = bx1 + btn_w + gap_b
                by = my + mh - 75

                is_opt0 = (dl_state["selected_opt"] == 0)
                is_opt1 = (dl_state["selected_opt"] == 1)

                fill_rect(bx1, by, btn_w, btn_h, 0, 200, 120, 255)
                if is_opt0:
                    draw_rect(bx1, by, btn_w, btn_h, 255, 255, 255, 255, thickness=3)
                else:
                    draw_rect(bx1, by, btn_w, btn_h, 0, 255, 160, 255, thickness=1)
                draw_text(tr("dl_btn_play_now"), font_badge, bx1 + btn_w // 2, by + btn_h // 2, 0, 0, 0, center_x=True, center_y=True)

                fill_rect(bx2, by, btn_w, btn_h, 45, 60, 90, 255)
                if is_opt1:
                    draw_rect(bx2, by, btn_w, btn_h, 255, 255, 255, 255, thickness=3)
                else:
                    draw_rect(bx2, by, btn_w, btn_h, 90, 120, 170, 255, thickness=1)
                draw_text(f"[B] {tr('act_close_title').capitalize()}", font_badge, bx2 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)

            elif dl_state["status"] in ("error", "cancelled"):
                # Modal ve nguyen van tung dong: ten file cua ban scene, hay
                # duong dan thu muc J2ME, dai hon be ngang khung thi chu chay
                # thang ra ngoai - dung nhu dong Errno tung bi cat cut o mep.
                lines = []
                for _raw in dl_state["msg"].split("\n"):
                    lines.extend(wrap_text_to_width(_raw, font_sub, mw - 90, max_lines=2))
                line_y = my + 155
                for l in lines:
                    draw_text(l, font_sub, mx + 45, line_y, 255, 100, 100)
                    line_y += 34

                btn_w = 200
                btn_h = 50
                bx = mx + (mw - btn_w) // 2
                by = my + mh - 70
                fill_rect(bx, by, btn_w, btn_h, 220, 70, 70, 255)
                draw_rect(bx, by, btn_w, btn_h, 255, 255, 255, 255, thickness=2)
                draw_text(f"[B] {tr('act_close_title').capitalize()}", font_badge, bx + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 5.2. QR MODAL (donation transfer details, chat group invite)
        # ----------------------------------------------------------------------
        elif qr_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 225)

            mw = min(940, state.SCREEN_W - 50)
            mh = min(620, state.SCREEN_H - 70)
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2
            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            fill_rect(mx + 3, my + 3, mw - 6, 66, 24, 34, 58, 255)
            fill_rect(mx + 3, my + 67, mw - 6, 2, 0, 246, 246, 255)
            _pg = qr_modal["pages"][qr_modal["page"] % len(qr_modal["pages"])]
            _npages = len(qr_modal["pages"])
            draw_text(_pg["title"], font_title, mx + mw // 2, my + 35,
                      0, 246, 246, center_x=True, center_y=True)

            body_y = my + 88
            body_h = mh - 88 - 62
            TEXT_COL_W = 350

            # The images hold the bare pattern, so the four modules of quiet zone
            # the spec demands are drawn here. Sizing the padding from the module
            # count keeps it exact: too little and the code stops scanning, too
            # much and it just wastes space.
            mods = max(21, _pg.get("mods", 25))
            quiet = 4.0 / mods
            avail_w = mw - 68 - TEXT_COL_W - 24
            qr_side = int(min(avail_w, body_h) / (1.0 + 2 * quiet))
            pad = max(8, int(qr_side * quiet))

            qr_x = mx + 34 + pad
            qr_y = body_y + (body_h - qr_side) // 2
            fill_rect(qr_x - pad, qr_y - pad, qr_side + pad * 2, qr_side + pad * 2,
                      255, 255, 255, 255)
            if not draw_proportional_boxart(_pg["img"], qr_x, qr_y, qr_side, qr_side):
                draw_text("QR", font_title, qr_x + qr_side // 2, qr_y + qr_side // 2,
                          40, 40, 40, center_x=True, center_y=True)

            tx = qr_x + qr_side + pad + 34
            tw = mx + mw - tx - 30
            rows = _pg["rows"]
            row_pitch = 96
            ty = body_y + max(0, (body_h - len(rows) * row_pitch) // 2)
            for lbl, val in rows:
                draw_text(lbl, font_badge, tx, ty, 150, 175, 210, center_y=True)
                draw_text(val, font_title, tx, ty + 42, 255, 255, 255, center_y=True)
                fill_rect(tx, ty + 76, tw, 1, 45, 62, 95, 255)
                ty += row_pitch

            if _npages > 1:
                # Dots rather than "1/2": the count is small and a filled dot
                # reads at a glance without being counted.
                dot_r = 7
                gap = 16
                total_w = _npages * dot_r * 2 + (_npages - 1) * gap
                dx = mx + mw // 2 - total_w // 2
                dy = my + mh - 52
                for i in range(_npages):
                    cx = dx + i * (dot_r * 2 + gap)
                    if i == qr_modal["page"]:
                        fill_rect(cx, dy, dot_r * 2, dot_r * 2, 0, 246, 246, 255)
                    else:
                        draw_rect(cx, dy, dot_r * 2, dot_r * 2, 90, 110, 145, 255, thickness=2)
                draw_text(f"[L1/R1] {tr('qr_switch')}   [A/B] {tr('lib_filter_close')}",
                          font_sub, mx + mw // 2, my + mh - 22, 160, 180, 210,
                          center_x=True, center_y=True)
            else:
                draw_text(f"[A/B] {tr('lib_filter_close')}", font_sub,
                          mx + mw // 2, my + mh - 30, 160, 180, 210,
                          center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 5.3. LIBRARY SYSTEM FILTER MODAL
        # ----------------------------------------------------------------------
        elif pick_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)
            rows = pick_modal["rows"]
            sel = pick_modal["selected_idx"]
            row_h = 54
            shown = min(len(rows), 8)
            # Scroll so the cursor stays inside the window when the card holds
            # more systems than fit.
            top = max(0, min(sel - shown // 2, len(rows) - shown))

            # Width from the widest row actually in this list, measured with the
            # real font rather than guessed from character counts: "Sega Genesis
            # (MD / Mega Drive)" is 30 characters and ran past the fixed 520px.
            name_w = max([measure_text(n, font_item) for _, n, _ in rows] or [0])
            right_w = max([measure_text(r, font_sub) for _, _, r in rows if r] or [0])
            title_w = measure_text(pick_modal["title"], font_item)
            mw = max(520, min(state.SCREEN_W - 80,
                              max(60 + name_w + 30 + right_w + 40, title_w + 80)))
            mh = 110 + shown * row_h
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2
            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)
            fill_rect(mx + 3, my + 3, mw - 6, 62, 24, 34, 58, 255)
            fill_rect(mx + 3, my + 63, mw - 6, 2, 0, 246, 246, 255)
            draw_text(pick_modal["title"], font_item, mx + mw // 2, my + 32,
                      0, 246, 246, center_x=True, center_y=True)

            for i in range(shown):
                code, name, right = rows[top + i]
                ry = my + 78 + i * row_h
                is_sel = (top + i == sel)
                if is_sel:
                    fill_rect(mx + 14, ry, mw - 28, row_h - 6, 28, 44, 75, 255)
                    draw_rect(mx + 14, ry, mw - 28, row_h - 6, 0, 246, 246, 255, thickness=2)
                # Filled dot marks the filter in force; the font has no glyph for
                # a checkmark, so it is drawn.
                if code == pick_modal["current"]:
                    fill_rect(mx + 30, ry + row_h // 2 - 9, 12, 12, 0, 246, 246, 255)
                else:
                    draw_rect(mx + 30, ry + row_h // 2 - 9, 12, 12, 90, 110, 145, 255, thickness=2)
                draw_text(name, font_item, mx + 60, ry + row_h // 2 - 3,
                          255, 255, 255, center_y=True)
                if right:
                    # Right-aligned. Drawn from a fixed x it grew rightwards, so a
                    # five-digit count spilled past the modal edge.
                    draw_text(right, font_sub,
                              mx + mw - 40 - measure_text(right, font_sub),
                              ry + row_h // 2 - 3, 150, 170, 200, center_y=True)

            draw_text(f"[A] {tr('lib_filter_pick')}   [B] {tr('lib_filter_close')}",
                      font_sub, mx + mw // 2, my + mh - 24, 160, 180, 210,
                      center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 5.4. UPDATE AVAILABLE MODAL
        # ----------------------------------------------------------------------
        elif update_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)
            mw = min(760, state.SCREEN_W - 60)
            mh = 380
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)
            fill_rect(mx + 3, my + 3, mw - 6, 70, 24, 34, 58, 255)
            fill_rect(mx + 3, my + 71, mw - 6, 2, 0, 246, 246, 255)
            draw_text(tr("upd_title"), font_title, mx + mw // 2, my + 36,
                      0, 246, 246, center_x=True, center_y=True)

            um = update_modal["manifest"] or {}
            rows_y = my + 100
            draw_text(f"{tr('upd_current')} {APP_VERSION}", font_item, mx + 45, rows_y, 200, 215, 235)
            if update_modal["cat_only"]:
                # Phien ban khong doi: "Ban moi: 1.39" trung voi dong tren se
                # doc nhu mot loi hien thi. Noi dung dang thay la kho game,
                # va so tep = 0 (catalog di lech duong "files") vo nghia hon
                # la dung luong phai tai.
                cat = catalog_entry(um) or {}
                size_txt = human_bytes(cat["size"]) if cat else ""
                draw_text(tr("upd_cat_new"), font_item, mx + 45, rows_y + 40, 0, 246, 200)
                draw_text(f"{tr('game_size')}{size_txt}", font_sub, mx + 45, rows_y + 82, 150, 170, 200)
            else:
                draw_text(f"{tr('upd_new')} {um.get('version', '?')}", font_item, mx + 45, rows_y + 40, 0, 246, 200)
                draw_text(f"{tr('upd_files')} {len(update_modal['files'])}", font_sub, mx + 45, rows_y + 82, 150, 170, 200)

            # "Co ban moi, 5 tep" khong tra loi duoc cau hoi duy nhat nguoi dung
            # dang hoi: cai bay gio hay de sau. Mot dong noi ban nay sua gi thi
            # tra loi duoc. Ban phat hanh cu khong co ghi chu, va luc do bo cuc
            # tro lai y nhu truoc.
            note_y = rows_y + 116
            rel_note = release_note(um, state.current_lang)
            if rel_note:
                note_txt = f"• {rel_note}"
                # Modal ve nguyen van tung dong: cat cho vua be ngang, neu khong
                # chu chay thang ra ngoai khung.
                limit = mw - 90
                if measure_text(note_txt, font_sub) > limit:
                    while note_txt and measure_text(note_txt + "...", font_sub) > limit:
                        note_txt = note_txt[:-1]
                    note_txt = note_txt.rstrip() + "..."
                draw_text(note_txt, font_sub, mx + 45, note_y, 0, 230, 180)
                note_y += 34
            draw_text(tr("upd_note"), font_sub, mx + 45, note_y, 150, 170, 200)

            if update_modal["busy"] or update_modal["failed"]:
                colour = (255, 120, 120) if update_modal["failed"] else (0, 230, 255)
                draw_text(update_modal["status"], font_item, mx + mw // 2, my + mh - 62,
                          *colour, center_x=True, center_y=True)
                if update_modal["failed"]:
                    draw_text("[A/B] OK", font_sub, mx + mw // 2, my + mh - 26,
                              200, 215, 235, center_x=True, center_y=True)
            else:
                labels = update_modal_labels()
                bw = (mw - 100) // len(labels)
                bh = 52
                by = my + mh - 78
                for i, lbl in enumerate(labels):
                    bx = mx + 40 + i * (bw + 10)
                    sel = (i == update_modal["selected_opt"])
                    if sel:
                        fill_rect(bx, by, bw, bh, 0, 120, 130, 255)
                        draw_rect(bx, by, bw, bh, 0, 246, 246, 255, thickness=3)
                    else:
                        fill_rect(bx, by, bw, bh, 30, 42, 66, 255)
                        draw_rect(bx, by, bw, bh, 70, 90, 125, 255, thickness=1)
                    draw_text(lbl, font_badge, bx + bw // 2, by + bh // 2,
                              255, 255, 255, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 5.5. PRE-DOWNLOAD GAME DETAILS & PREVIEW MODAL (Requirement 5)
        # ----------------------------------------------------------------------
        elif pre_download_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

            mw = min(960, state.SCREEN_W - 40)
            mh = 480
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            g_info = pre_download_modal["game_info"]
            g_title = g_info.get("title", "Game") if g_info else "Game"
            sys_c = pre_download_modal["sys_code"]
            sz_str = (pre_download_modal.get("dynamic_size_str") or g_info.get("file_size_str") or g_info.get("size") or "").strip() if g_info else ""
            if sz_str in ("TOPO SHOP", "TOPO"):
                sz_str = ""
            fn_str = g_info.get("filename", "") if g_info else ""
            img_p = pre_download_modal.get("img_path") or pre_download_modal.get("preview_cached_path")
            sel_opt = pre_download_modal["selected_opt"]

            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            # Header
            fill_rect(mx + 3, my + 3, mw - 6, 74, 24, 34, 58, 255)
            fill_rect(mx + 3, my + 75, mw - 6, 2, 0, 246, 246, 255)
            draw_text(tr("pre_dl_modal_title"), font_title, mx + mw // 2, my + 38, 0, 246, 246, center_x=True, center_y=True)

            mid_y = my + 92
            box_w = 230
            box_h = 240
            box_x = mx + 40
            fill_rect(box_x, mid_y, box_w, box_h, 12, 16, 26, 255)
            draw_rect(box_x, mid_y, box_w, box_h, 45, 65, 100, 255, thickness=1)

            drawn = False
            if img_p and os.path.exists(img_p):
                drawn = draw_proportional_boxart(img_p, box_x + 6, mid_y + 6, box_w - 12, box_h - 12)
            if not drawn:
                if pre_download_modal.get("preview_status") == "loading":
                    draw_text("Đang tải ảnh...", font_sub, box_x + box_w // 2, mid_y + box_h // 2 - 15, 0, 230, 255, center_x=True, center_y=True)
                    draw_text(f"[{sys_c}]", font_item, box_x + box_w // 2, mid_y + box_h // 2 + 15, 180, 200, 220, center_x=True, center_y=True)
                else:
                    draw_default_boxart_avatar(box_x + 6, mid_y + 6, box_w - 12, box_h - 12, sys_c, g_title)

            dt_x = box_x + box_w + 35

            # Game Title
            dt_title = f"[{sys_c}] {g_title}"
            if len(dt_title) > 38:
                dt_title = dt_title[:35] + "..."
            draw_text(f"{tr('pre_dl_lbl_name')}{dt_title}", font_item, dt_x, mid_y + 20, 255, 255, 255)

            # System
            s_full = get_system_display_name(sys_c)
            draw_text(f"{tr('pre_dl_lbl_sys')}{s_full}", font_modal_lbl, dt_x, mid_y + 65, 0, 230, 255)

            # Size
            size_display = sz_str if sz_str else ("Đang kiểm tra..." if (g_info and g_info.get("rom_url")) else ("Chuẩn ROM gốc" if state.current_lang == "VI" else "Standard ROM"))
            draw_text(f"{tr('pre_dl_lbl_size')}{size_display}", font_modal_lbl, dt_x, mid_y + 110, 255, 215, 0)

            # Filename
            dt_fn = fn_str
            if len(dt_fn) > 36:
                dt_fn = dt_fn[:33] + "..."
            draw_text(f"{tr('pre_dl_lbl_file')}{dt_fn}", font_modal_lbl, dt_x, mid_y + 155, 180, 205, 235)

            # Source Server
            cand_url = (g_info.get("topo_url") or g_info.get("rom_url") or g_info.get("mirror_url") or "") if g_info else ""
            src_lbl = "TOPO SHOP CDN" if ("toposhop.vn" in cand_url or (g_info and g_info.get("topo_url"))) else ("Internet Archive CDN" if "archive.org" in cand_url else "Online Fast CDN")
            draw_text(f"{tr('pre_dl_lbl_source')}{src_lbl}", font_modal_lbl, dt_x, mid_y + 200, 140, 230, 180)

            # Destination directory. J2ME games are filed by handset resolution,
            # so name the subfolder the jar will actually land in.
            _dest = (rom_dir_for(fn_str) if sys_c in ("JAVA", "J2ME")
                     else f"/mnt/SDCARD/Roms/{sys_c}")
            draw_text(f"{tr('pre_dl_lbl_dest')}{_dest}/", font_sub, dt_x, mid_y + 242, 140, 160, 190)

            # Bottom Action Buttons
            btn_w = 260
            btn_h = 60
            gap_b = 35
            bx1 = mx + (mw - (btn_w * 2 + gap_b)) // 2
            bx2 = bx1 + btn_w + gap_b
            by = my + mh - btn_h - 22

            is_opt0 = (sel_opt == 0)
            is_opt1 = (sel_opt == 1)

            # Button 1: Start Download (Green)
            if is_opt0:
                fill_rect(bx1, by, btn_w, btn_h, 0, 200, 120, 255)
                draw_rect(bx1, by, btn_w, btn_h, 255, 255, 255, 255, thickness=3)
                draw_text(tr("pre_dl_btn_download"), font_badge, bx1 + btn_w // 2, by + btn_h // 2, 0, 0, 0, center_x=True, center_y=True)
            else:
                fill_rect(bx1, by, btn_w, btn_h, 16, 48, 36, 255)
                draw_rect(bx1, by, btn_w, btn_h, 0, 200, 120, 255, thickness=1)
                draw_text(tr("pre_dl_btn_download"), font_badge, bx1 + btn_w // 2, by + btn_h // 2, 0, 230, 140, center_x=True, center_y=True)

            # Button 2: Cancel / Back (Red/Dark)
            if is_opt1:
                fill_rect(bx2, by, btn_w, btn_h, 200, 50, 50, 255)
                draw_rect(bx2, by, btn_w, btn_h, 255, 255, 255, 255, thickness=3)
                draw_text(tr("pre_dl_btn_cancel"), font_badge, bx2 + btn_w // 2, by + btn_h // 2, 255, 255, 255, center_x=True, center_y=True)
            else:
                fill_rect(bx2, by, btn_w, btn_h, 45, 60, 90, 255)
                draw_rect(bx2, by, btn_w, btn_h, 80, 110, 160, 255, thickness=1)
                draw_text(tr("pre_dl_btn_cancel"), font_badge, bx2 + btn_w // 2, by + btn_h // 2, 200, 215, 235, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 6. DOWNLOADED GAME HORIZONTAL ACTION MODAL
        # ----------------------------------------------------------------------
        elif game_action_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

            mw = min(960, state.SCREEN_W - 40)
            mh = 480
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            g_title = game_action_modal["game_info"].get("title", "Game")
            sys_c = game_action_modal.get("sys_code", current_rom_system)
            sz_str = game_action_modal.get("size_str", "")
            img_p = game_action_modal.get("img_path")
            sel_opt = game_action_modal["selected_opt"]

            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            fill_rect(mx + 3, my + 3, mw - 6, 76, 24, 34, 58, 255)
            fill_rect(mx + 3, my + 77, mw - 6, 2, 0, 246, 246, 255)
            
            disp_g_title = f"[{sys_c}] {g_title}"
            if len(disp_g_title) > 38:
                disp_g_title = disp_g_title[:35] + "..."
            draw_text(disp_g_title, font_title, mx + mw // 2, my + 40, 255, 255, 255, center_x=True, center_y=True)

            mid_y = my + 95
            box_w = 200
            box_h = 175
            box_x = mx + 45
            fill_rect(box_x, mid_y, box_w, box_h, 12, 16, 26, 255)
            draw_rect(box_x, mid_y, box_w, box_h, 45, 65, 100, 255, thickness=1)

            drawn = False
            if img_p and os.path.exists(img_p):
                drawn = draw_proportional_boxart(img_p, box_x + 6, mid_y + 6, box_w - 12, box_h - 12)
            if not drawn:
                draw_default_boxart_avatar(box_x + 6, mid_y + 6, box_w - 12, box_h - 12, sys_c, g_title)

            dt_x = box_x + box_w + 35
            draw_text(f"• Hệ máy: {sys_c}", font_modal_lbl, dt_x, mid_y + 30, 0, 230, 255)
            if sz_str:
                draw_text(f"• Dung lượng: {sz_str}", font_modal_lbl, dt_x, mid_y + 75, 255, 215, 0)
            if sys_c in ("JAVA", "J2ME"):
                _r = pretty_resolution(resolution_of_path(game_action_modal.get("rom_path", "")))
                draw_text(f"• Màn hình: {_r}", font_modal_lbl, dt_x, mid_y + 120, 0, 246, 200)
            else:
                draw_text(f"• Vị trí lưu: Roms/{sys_c}/", font_modal_lbl, dt_x, mid_y + 120, 200, 215, 235)

            # Compact icon tiles: one short label each, no description line - five of
            # them have to fit the same strip that used to hold four fat ones.
            _act_look = {
                "PLAY":  (tr("act_play_title"), (0, 230, 150)),
                "DEL":   (tr("act_del_title"), (255, 80, 80)),
                "RES":   (pretty_resolution(resolution_of_path(
                             game_action_modal.get("rom_path", ""))), (255, 200, 0)),
                "REGET": (tr("act_reget_title"), (255, 200, 0)),
                "CLOSE": (tr("act_close_title"), (180, 200, 230)),
            }
            actions = [(i,) + _act_look[i] for i in _act_ids(sys_c)]

            num_tiles = len(actions)
            tile_gap = 18
            total_tiles_w = mw - 70
            tile_w = (total_tiles_w - (num_tiles - 1) * tile_gap) // num_tiles
            tile_h = 76
            tile_y = my + mh - tile_h - 25

            for t_idx, (t_icon, t_title, t_col) in enumerate(actions):
                tx = mx + 35 + t_idx * (tile_w + tile_gap)
                is_t_sel = (t_idx == sel_opt)

                if is_t_sel:
                    fill_rect(tx, tile_y, tile_w, tile_h, 32, 50, 85, 255)
                    draw_rect(tx, tile_y, tile_w, tile_h, 0, 246, 246, 255, thickness=3)
                    fill_rect(tx + 4, tile_y + 4, tile_w - 8, 6, t_col[0], t_col[1], t_col[2], 255)
                else:
                    fill_rect(tx, tile_y, tile_w, tile_h, 20, 28, 46, 255)
                    draw_rect(tx, tile_y, tile_w, tile_h, 45, 60, 95, 255, thickness=1)

                ib_w = tile_w - 24
                ib_h = 26
                ib_x = tx + 12
                ib_y = tile_y + 8
                fill_rect(ib_x, ib_y, ib_w, ib_h, 14, 20, 34, 255)
                draw_rect(ib_x, ib_y, ib_w, ib_h, t_col[0], t_col[1], t_col[2], 255, thickness=1)
                draw_text(f"[{t_icon}]", font_badge, ib_x + ib_w // 2, ib_y + ib_h // 2, t_col[0], t_col[1], t_col[2], center_x=True, center_y=True)

                draw_text(t_title, font_sub, tx + tile_w // 2, tile_y + 52,
                          255, 255, 255, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 6.5. ALPHABET QUICK JUMP MODAL (A - Z GRID)
        # ----------------------------------------------------------------------
        elif j2me_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

            jw = 780
            jh_ = 420
            jx = (state.SCREEN_W - jw) // 2
            jy = (state.SCREEN_H - jh_) // 2
            fill_rect(jx, jy, jw, jh_, 16, 22, 38, 255)
            draw_rect(jx, jy, jw, jh_, 0, 246, 246, 255, thickness=3)
            fill_rect(jx + 3, jy + 3, jw - 6, 54, 24, 34, 58, 255)
            draw_text(tr("j2me_info_title"), font_item, jx + jw // 2, jy + 30,
                      0, 246, 246, center_x=True, center_y=True)

            # Real status, not a fixed "success" line: say plainly what is missing.
            missing = j2me_missing_parts()
            if j2me_modal["busy"]:
                st_txt, st_col = tr("j2me_st_installing"), (255, 200, 0)
            elif missing:
                st_txt, st_col = f"{tr('j2me_st_missing')} {', '.join(missing)}", (255, 90, 90)
            elif runtime_is_stale():
                # Five files present is not the same as the right five files.
                st_txt, st_col = tr("j2me_st_stale"), (255, 200, 0)
            else:
                st_txt, st_col = tr("j2me_st_ready"), (0, 255, 160)

            sy = jy + 78
            fill_rect(jx + 22, sy - 6, jw - 44, 40, 22, 30, 48, 255)
            draw_rect(jx + 22, sy - 6, jw - 44, 40, st_col[0], st_col[1], st_col[2], 200, thickness=2)
            draw_text(st_txt, font_sub, jx + 40, sy + 14, st_col[0], st_col[1], st_col[2], center_y=True)

            n_java = len([g for g in downloaded_games_list if g.get("sys_code") == "JAVA"])
            for r_i, (lbl, val) in enumerate((
                    (tr("j2me_row_games"), str(n_java)),
                    (tr("j2me_row_emu"), "/mnt/SDCARD/Emus/JAVA/"),
                    (tr("j2me_row_rom"), "/mnt/SDCARD/Roms/JAVA/"))):
                ry_j = jy + 150 + r_i * 42
                draw_text(lbl, font_sub, jx + 44, ry_j, 150, 165, 195)
                draw_text(val, font_sub, jx + 290, ry_j, 225, 235, 250)

            # Two buttons: reinstall and back. Without the second one there was no
            # sign that B closes the panel.
            ay = jy + jh_ - 74
            bh = 52
            gap = 20
            bw = (jw - 44 - gap) // 2
            for b_i, (b_txt, b_col, b_on) in enumerate((
                    (tr("j2me_do_install"), (255, 200, 0), not j2me_modal["busy"]),
                    (tr("j2me_do_close"), (180, 200, 230), not j2me_modal["busy"]))):
                bx_j = jx + 22 + b_i * (bw + gap)
                col = b_col if b_on else (110, 120, 140)
                fill_rect(bx_j, ay, bw, bh, 24, 34, 58, 255)
                draw_rect(bx_j, ay, bw, bh, col[0], col[1], col[2], 255, thickness=2)
                draw_text(b_txt, font_sub, bx_j + bw // 2, ay + bh // 2,
                          col[0], col[1], col[2], center_x=True, center_y=True)

        elif res_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

            row_h = 54
            rw = 420
            rh_ = 96 + row_h * len(RESOLUTIONS)
            rx = (state.SCREEN_W - rw) // 2
            ry = (state.SCREEN_H - rh_) // 2

            fill_rect(rx, ry, rw, rh_, 16, 22, 38, 255)
            draw_rect(rx, ry, rw, rh_, 0, 246, 246, 255, thickness=3)
            fill_rect(rx + 3, ry + 3, rw - 6, 56, 24, 34, 58, 255)
            draw_text(tr("act_res_title"), font_item, rx + rw // 2, ry + 31,
                      0, 246, 246, center_x=True, center_y=True)

            cur_res = resolution_of_path(game_action_modal.get("rom_path", ""))
            for r_i, r_folder in enumerate(RESOLUTIONS):
                ry_i = ry + 68 + r_i * row_h
                is_sel = (r_i == res_modal["selected_idx"])
                is_cur = (r_folder == cur_res)
                if is_sel:
                    fill_rect(rx + 12, ry_i, rw - 24, row_h - 6, 32, 50, 85, 255)
                    draw_rect(rx + 12, ry_i, rw - 24, row_h - 6, 0, 246, 246, 255, thickness=2)
                # the size the game already uses stays marked, so a pick that changes
                # nothing is obvious before pressing
                col = (0, 255, 160) if is_cur else (225, 235, 250)
                draw_text(pretty_resolution(r_folder), font_item, rx + 40,
                          ry_i + (row_h - 6) // 2, col[0], col[1], col[2], center_y=True)
                # Marker drawn from rectangles, not a glyph: the bundled font has no
                # tick or bullet, and a text label was wide enough to push the layout.
                bx = rx + rw - 46
                by = ry_i + (row_h - 6) // 2 - 10
                draw_rect(bx, by, 20, 20, 90, 110, 145, 255, thickness=2)
                if is_cur:
                    fill_rect(bx + 5, by + 5, 10, 10, 0, 255, 160, 255)

        elif alphabet_modal["active"]:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)

            mw = min(920, state.SCREEN_W - 40)
            mh = 420
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            # Header Bar
            fill_rect(mx + 3, my + 3, mw - 6, 68, 24, 34, 58, 255)
            draw_text(tr("alpha_title"), font_item, mx + mw // 2, my + 36, 0, 246, 246, center_x=True, center_y=True)

            # Subtitle guide
            draw_text(tr("alpha_sub"), font_sub, mx + mw // 2, my + 95, 170, 185, 210, center_x=True, center_y=True)

            # 3 Rows x 9 Columns Letter Grid
            cols = 9
            gap = 8
            grid_pad_x = 30
            cw = (mw - grid_pad_x * 2 - (cols - 1) * gap) // cols
            ch = 62
            grid_y = my + 120

            for idx, let in enumerate(alphabet_modal["letters"]):
                r = idx // cols
                c = idx % cols
                bx = mx + grid_pad_x + c * (cw + gap)
                by = grid_y + r * (ch + gap)

                is_sel = (idx == alphabet_modal["selected_idx"])
                has_games = (let in alphabet_modal["available_map"])
                cnt = alphabet_modal["counts_map"].get(let, 0)

                if is_sel:
                    fill_rect(bx, by, cw, ch, 255, 180, 0, 255)
                    draw_rect(bx, by, cw, ch, 255, 255, 255, 255, thickness=3)
                    draw_text(let, font_item, bx + cw // 2, by + ch // 2 - 10, 0, 0, 0, center_x=True, center_y=True)
                    draw_text(f"{cnt}", font_badge, bx + cw // 2, by + ch // 2 + 14, 0, 0, 0, center_x=True, center_y=True)
                elif has_games:
                    fill_rect(bx, by, cw, ch, 24, 38, 62, 255)
                    draw_rect(bx, by, cw, ch, 0, 210, 245, 255, thickness=1)
                    draw_text(let, font_item, bx + cw // 2, by + ch // 2 - 10, 0, 246, 246, center_x=True, center_y=True)
                    draw_text(f"{cnt}", font_badge, bx + cw // 2, by + ch // 2 + 14, 180, 220, 255, center_x=True, center_y=True)
                else:
                    fill_rect(bx, by, cw, ch, 18, 24, 36, 180)
                    draw_rect(bx, by, cw, ch, 40, 50, 70, 255, thickness=1)
                    draw_text(let, font_item, bx + cw // 2, by + ch // 2, 80, 95, 115, center_x=True, center_y=True)

            # Bottom summary line
            sel_let = alphabet_modal["letters"][alphabet_modal["selected_idx"]]
            sel_cnt = alphabet_modal["counts_map"].get(sel_let, 0)
            fill_rect(mx + 30, my + mh - 54, mw - 60, 36, 20, 28, 48, 255)
            draw_rect(mx + 30, my + mh - 54, mw - 60, 36, 60, 85, 130, 255)
            if sel_cnt > 0:
                sum_txt = f"Chữ '{sel_let}': {sel_cnt} game trong hệ máy" if state.current_lang == "VI" else f"Letter '{sel_let}': {sel_cnt} games in system"
                draw_text(sum_txt, font_sub, mx + mw // 2, my + mh - 36, 255, 215, 0, center_x=True, center_y=True)
            else:
                sum_txt = f"Chữ '{sel_let}': Không có game nào" if state.current_lang == "VI" else f"Letter '{sel_let}': No games available"
                draw_text(sum_txt, font_sub, mx + mw // 2, my + mh - 36, 140, 155, 175, center_x=True, center_y=True)

        # ----------------------------------------------------------------------
        # 7. STRUCTURED INFO / GUIDE / STORAGE PROGRESS MODAL
        # ----------------------------------------------------------------------
        elif modal_title and modal_rows:
            fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

            mw = min(940, state.SCREEN_W - 40)
            num_r = len(modal_rows)
            is_progress_mode = isinstance(modal_rows[0], dict) and ("pct" in modal_rows[0])
            # One line instead of two, so the table rows can be tighter.
            LBL_COL_W = 250
            if is_progress_mode:
                row_h = 82
            elif modal_style == "two_col":
                row_h = 64
            elif modal_style == "big":
                row_h = 58
            else:
                row_h = 72
            # The headline row carries a 54px address and needs the extra height;
            # it is added once rather than paid by every row.
            extra_first = 44 if modal_style == "big" else 0
            row_gap = 10
            header_box_h = 68
            footer_btn_h = 65

            mh = min(state.SCREEN_H - 40,
                     header_box_h + (num_r * (row_h + row_gap)) + extra_first + footer_btn_h + 20)
            mx = (state.SCREEN_W - mw) // 2
            my = (state.SCREEN_H - mh) // 2

            fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
            draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

            # Header
            fill_rect(mx + 3, my + 3, mw - 6, header_box_h, 24, 34, 58, 255)
            fill_rect(mx + 3, my + header_box_h + 1, mw - 6, 2, 0, 246, 246, 255)
            draw_text(modal_title, font_title, mx + mw // 2, my + header_box_h // 2 + 2, 0, 246, 246, center_x=True, center_y=True)

            row_start_y = my + header_box_h + 14

            for r_idx, row_data in enumerate(modal_rows):
                ry = row_start_y + r_idx * (row_h + row_gap) + (extra_first if r_idx else 0)
                this_h = row_h + (extra_first if r_idx == 0 else 0)
                rx = mx + 25
                rw = mw - 50

                fill_rect(rx, ry, rw, this_h, 22, 30, 52, 255)
                draw_rect(rx, ry, rw, this_h, 45, 65, 105, 255, thickness=1)

                if is_progress_mode and isinstance(row_data, dict):
                    r_title = row_data.get("title", "")
                    r_sub = row_data.get("sub", "")
                    r_pct = max(0, min(100, row_data.get("pct", 0)))
                    r_badge = row_data.get("badge", f"{r_pct}%")

                    # Color based on percentage load
                    if r_pct >= 90:
                        bar_r, bar_g, bar_b = 255, 65, 65
                    elif r_pct >= 75:
                        bar_r, bar_g, bar_b = 255, 175, 20
                    else:
                        bar_r, bar_g, bar_b = 0, 230, 255

                    # Accent left bar
                    fill_rect(rx + 2, ry + 2, 5, row_h - 4, bar_r, bar_g, bar_b, 255)

                    # Line 1: Title
                    draw_text(r_title, font_modal_lbl, rx + 18, ry + 16, 0, 246, 246, center_y=True)

                    # Line 2: Visual Progress Bar Track
                    track_x = rx + 18
                    track_y = ry + 34
                    track_w = rw - 36
                    track_h = 13

                    fill_rect(track_x, track_y, track_w, track_h, 12, 16, 28, 255)
                    draw_rect(track_x, track_y, track_w, track_h, 45, 60, 90, 255)

                    fill_w = int(track_w * (r_pct / 100.0))
                    if fill_w > 0:
                        fill_rect(track_x + 1, track_y + 1, fill_w - 2, track_h - 2, bar_r, bar_g, bar_b, 255)

                    # Line 3: Subtitle detail
                    draw_text(r_sub, font_sub, rx + 18, ry + 63, 185, 200, 225, center_y=True)
                elif modal_style == "big" and r_idx == 0:
                    # The address this screen exists to show, at a size readable
                    # from arm's length while typing it into another machine.
                    lbl, val = row_data
                    fill_rect(rx + 2, ry + 2, 5, row_h - 4, 0, 230, 255, 255)
                    draw_text(lbl, font_sub, rx + 22, ry + 22, 150, 175, 210, center_y=True)
                    draw_text(val, font_huge, rx + 22, ry + 66, 0, 246, 246, center_y=True)

                elif modal_style == "big":
                    lbl, val = row_data
                    fill_rect(rx + 2, ry + 2, 5, row_h - 4, 60, 80, 120, 255)
                    draw_text(lbl, font_sub, rx + 22, ry + row_h // 2 - 2,
                              150, 175, 210, center_y=True)
                    draw_text(val, font_modal_val, rx + LBL_COL_W + 22, ry + row_h // 2 - 2,
                              225, 235, 248, center_y=True)

                elif modal_style == "two_col":
                    # Table form: label and value side by side on one line, in the
                    # larger list font. Only used where values are short enough to
                    # fit the right column - the device and storage rows are not.
                    lbl, val = row_data
                    fill_rect(rx + 2, ry + 2, 5, row_h - 4, 0, 230, 255, 255)
                    fill_rect(rx + LBL_COL_W, ry + 8, 1, row_h - 16, 60, 80, 120, 255)
                    draw_text(lbl, font_item, rx + 22, ry + row_h // 2 - 2,
                              0, 230, 255, center_y=True)
                    val_col = (255, 215, 0) if val.startswith("http") else (235, 243, 255)
                    draw_text(val, font_item, rx + LBL_COL_W + 22, ry + row_h // 2 - 2,
                              val_col[0], val_col[1], val_col[2], center_y=True)

                else:
                    # Classic Tuple row (lbl, val)
                    lbl, val = row_data
                    fill_rect(rx + 2, ry + 2, 5, row_h - 4, 0, 230, 255, 255)
                    draw_text(lbl, font_modal_lbl, rx + 20, ry + 18, 0, 230, 255, center_y=True)
                    val_col = (255, 215, 0) if val.startswith("http") else (225, 235, 248)
                    draw_text(val, font_modal_val, rx + 20, ry + 48, val_col[0], val_col[1], val_col[2], center_y=True)

            # Close Button
            btn_w = 260
            btn_h = 46
            bx = mx + (mw - btn_w) // 2
            by = my + mh - 58

            fill_rect(bx, by, btn_w, btn_h, 0, 200, 120, 255)
            draw_rect(bx, by, btn_w, btn_h, 0, 255, 160, 255, thickness=2)
            draw_text("Đóng [Bấm A hoặc B]", font_badge, bx + btn_w // 2, by + btn_h // 2, 0, 0, 0, center_x=True, center_y=True)

        sdl2.SDL_RenderPresent(renderer)

        # Adaptive Dynamic Eco Power Saving (60 FPS when active, ~28 FPS when idle to save battery)
        is_active = (now - last_user_activity_time < 1.0) or dl_state.get("active", False) or (toast_msg is not None) or yt_loading_state.get("active", False)
        if is_active:
            time.sleep(0.016)
        else:
            time.sleep(0.035)

    # Cleanup
    for c in controllers:
        sdl2.SDL_GameControllerClose(c)
    for j in joysticks:
        sdl2.SDL_JoystickClose(j)

    for item in text_texture_cache.values():
        if item and item[0]:
            sdl2.SDL_DestroyTexture(item[0])

    for item in img_texture_cache.values():
        if item and item[0]:
            sdl2.SDL_DestroyTexture(item[0])

    sdlttf.TTF_CloseFont(font_title)
    sdlttf.TTF_CloseFont(font_sub)
    sdlttf.TTF_CloseFont(font_item)
    sdlttf.TTF_CloseFont(font_badge)
    sdlttf.TTF_CloseFont(font_grid_title)
    sdlttf.TTF_CloseFont(font_footer)
    sdlttf.TTF_CloseFont(font_btn_badge)
    sdlttf.TTF_CloseFont(font_toast)
    sdlttf.TTF_CloseFont(font_modal_lbl)
    sdlttf.TTF_CloseFont(font_modal_val)
    sdlttf.TTF_CloseFont(font_kb)
    sdlttf.TTF_CloseFont(font_huge)
    sdlimage.IMG_Quit()
    sdlttf.TTF_Quit()
    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdl2.SDL_Quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        sys.stderr.write(f"\n[RetroHub Crash]\n{err_msg}\n")
        try:
            with open("/mnt/SDCARD/RetroHub-loi.txt", "a", encoding="utf-8") as _ef:
                _ef.write(f"\n[RetroHub Crash at {time.strftime('%Y-%m-%d %H:%M:%S')}]\n{err_msg}\n")
        except Exception:
            pass
        raise
