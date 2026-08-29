# -*- coding: utf-8 -*-
"""Java J2ME support.

Runtime is the SDL2 build of FreeJ2ME: a bundled JRE runs freej2me-sdl.jar, which
drives the native sdl_interface straight onto the framebuffer. No RetroArch and no
libretro core are involved.

Screen size is chosen by which folder a game sits in - Roms/JAVA/240320 and friends -
because J2ME titles are each built for one specific handset resolution.

The build is the Brick Pro one, which adds a renderer.conf and picks its pad layout
from control_profile.cfg. Everything the player can change in game - display mode
on START+R3, layout on START+SELECT - writes to those files, so this module reads
them fresh rather than holding a copy.
"""

import os
import shutil
import tarfile

from .paths import SDCARD_PATH, APP_DIR
from . import state

EMU_DIR = f"{SDCARD_PATH}/Emus/JAVA"
ROM_DIR = f"{SDCARD_PATH}/Roms/JAVA"
IMG_DIR = f"{SDCARD_PATH}/Imgs/JAVA"
RUNTIME_DIR = f"{EMU_DIR}/zulu17"
PAYLOAD = os.path.join(APP_DIR, "payload", "j2me_sdl.tar.gz")

# Screen size comes from the folder a game sits in. This list must stay in step
# with the branches in the package's launch.sh: a folder with no branch there
# falls through to its `echo "none"` and the game simply never starts.
RESOLUTIONS = ["240320", "320240", "128128", "176208", "640360"]
DEFAULT_RESOLUTION = "240320"   # 644 of the 957 titles that state a size

# Display presets, straight out of the emulator's own guide. The renderer is the
# one thing about this build worth setting from the app: the three modes differ by
# five keys at once, not one, and getting a mismatched pair (say pixel mode with
# integer scaling off) looks broken rather than different.
#
# There is deliberately no key mapping here any more. This build ignores
# keymap.cfg - it parses the file at startup and never reads the values back - and
# picks the pad layout from control_profile.cfg/control_cycle.cfg instead, which
# the player cycles on the device with START+SELECT.
RENDER_MODES = ["pixel", "smooth", "hq"]
DEFAULT_RENDER_MODE = "pixel"
RENDER_PRESETS = {
    "pixel":  {"render_mode": "pixel",  "integer_scaling": "true",  "keep_aspect": "true",
               "text_aa": "false", "shape_aa": "false", "m3g_filter": "nearest"},
    "smooth": {"render_mode": "smooth", "integer_scaling": "false", "keep_aspect": "true",
               "text_aa": "true",  "shape_aa": "true",  "m3g_filter": "linear"},
    "hq":     {"render_mode": "hq",     "integer_scaling": "false", "keep_aspect": "true",
               "text_aa": "true",  "shape_aa": "true",  "m3g_filter": "linear"},
}


def j2me_runtime_paths():
    """Where each piece of the SDL runtime has to live."""
    return {
        "java": f"{RUNTIME_DIR}/bin/java",
        "jar": f"{RUNTIME_DIR}/bin/freej2me-sdl.jar",
        "sdl": f"{RUNTIME_DIR}/bin/sdl_interface",
        "config": f"{EMU_DIR}/config.json",
        "launch": f"{EMU_DIR}/launch.sh",
    }


def j2me_missing_parts():
    """Names of the pieces that are absent. Empty means ready to play."""
    return [k for k, p in j2me_runtime_paths().items() if not os.path.exists(p)]


def is_j2me_runtime_ready():
    """True when a game can actually be launched."""
    return not j2me_missing_parts()


def runtime_supports_renderer():
    """True when the installed sdl_interface is a build that reads renderer.conf.

    An in-app update carries only the app's .py files - the 66MB runtime ships
    with the full package, not on every update - so a device can end up running
    this version of the app against the older emulator. That build has no
    renderer.conf at all, and a display screen wired to a binary that ignores it
    is a screen that does nothing.
    """
    sdl = j2me_runtime_paths()["sdl"]
    try:
        with open(sdl, "rb") as f:
            return b"renderer.conf" in f.read()
    except Exception:
        return False


def has_payload():
    """True when the bundled installer archive is present in the app folder."""
    return os.path.exists(PAYLOAD)


# ------------------------------------------------------------------ renderer
def renderer_conf_path():
    return f"{RUNTIME_DIR}/bin/renderer.conf"


def load_render_mode():
    """Which of the three presets is in force, from renderer.conf.

    The player can also change this on the device with START+R3, which rewrites
    the same file, so this is read fresh every time rather than cached.
    """
    try:
        with open(renderer_conf_path(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == "render_mode":
                    v = v.strip().lower()
                    return v if v in RENDER_MODES else DEFAULT_RENDER_MODE
    except Exception:
        pass
    return DEFAULT_RENDER_MODE


def save_render_mode(mode):
    """Write a whole preset out. Returns True when the file was replaced."""
    if mode not in RENDER_MODES:
        return False
    preset = RENDER_PRESETS[mode]
    lines = ["# FreeJ2ME Brick Pro renderer",
             "# pixel = nearest-neighbor; smooth = linear; hq = SDL best-quality fallback"]
    lines += [f"{k}={v}" for k, v in preset.items()]
    try:
        os.makedirs(os.path.dirname(renderer_conf_path()), exist_ok=True)
        with open(renderer_conf_path(), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except Exception as e:
        print(f"Error saving J2ME renderer.conf: {e}")
        return False


# ------------------------------------------------------------------ rom folders
def resolution_from_filename(filename):
    """Folder a jar belongs in, guessed from its name, e.g. Game_240x320.jar.

    Only 957 of 3357 Java entries state a size and nothing else does - the jar
    manifest has no size attribute and the catalogue has no column for it - so
    anything unrecognised goes to the default and can be moved afterwards.
    """
    import re
    m = re.search(r"(\d{2,3})\s*[xX_\-]\s*(\d{2,3})", filename or "")
    if m:
        for cand in (m.group(1) + m.group(2), m.group(2) + m.group(1)):
            if cand in RESOLUTIONS:
                return cand
    return DEFAULT_RESOLUTION


def resolution_of_path(rom_path):
    """Which resolution folder this file currently sits in, or the default."""
    folder = os.path.basename(os.path.dirname(rom_path or ""))
    return folder if folder in RESOLUTIONS else DEFAULT_RESOLUTION


def pretty_resolution(folder):
    """240320 -> 240x320, for showing in the UI."""
    if folder in RESOLUTIONS and len(folder) == 6:
        return folder[:3] + "x" + folder[3:]
    return folder


def rom_dir_for(filename):
    """Destination folder for a downloaded jar."""
    return os.path.join(ROM_DIR, resolution_from_filename(filename))


def ensure_rom_dirs():
    for r in RESOLUTIONS:
        try:
            os.makedirs(os.path.join(ROM_DIR, r), exist_ok=True)
        except Exception:
            pass


def move_to_resolution(rom_path, folder):
    """Move a game into another resolution folder. Returns the new path, or None.

    The stock menu caches its rom list, so the cache is dropped here - otherwise it
    would keep launching the old path and the game would fail to start.
    """
    import shutil
    if not rom_path or not os.path.exists(rom_path) or folder not in RESOLUTIONS:
        return None
    dst_dir = os.path.join(ROM_DIR, folder)
    try:
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, os.path.basename(rom_path))
        if os.path.abspath(dst) == os.path.abspath(rom_path):
            return rom_path
        shutil.move(rom_path, dst)
        for db in ("JAVA_cache7.db", "JAVA_cache6.db", "JAVA_cache.db"):
            try:
                os.remove(os.path.join(ROM_DIR, db))
            except Exception:
                pass
        return dst
    except Exception as e:
        print(f"move_to_resolution failed: {e}")
        return None


# ------------------------------------------------------------------ launcher
def install_j2me_emulator(force=False):
    """Install the SDL runtime from the bundled payload and wire JAVA into the menu.

    Returns (ok, message). The runtime ships inside the app so this works with no
    network - the archive is ~65MB of JRE, which is why it is not re-downloaded.

    force=True wipes the runtime first and unpacks it again, for repairing an
    install that has gone bad. The chosen display preset is kept: it is validated
    on load, so a damaged one cannot break the emulator, and losing it would be a
    nasty surprise for someone who only wanted to fix a crash.
    """
    vi = state.current_lang == "VI"
    try:
        saved_mode = load_render_mode() if force else None
        if force and os.path.isdir(RUNTIME_DIR):
            shutil.rmtree(RUNTIME_DIR, ignore_errors=True)
        os.makedirs(EMU_DIR, exist_ok=True)
        os.makedirs(IMG_DIR, exist_ok=True)
        ensure_rom_dirs()

        # Unpack the runtime only when it is not already there; re-extracting 65MB
        # on every press would take minutes on this hardware.
        if not os.path.exists(f"{RUNTIME_DIR}/bin/java"):
            if not has_payload():
                return False, ("Thiếu gói cài trong app (payload/j2me_sdl.tar.gz)"
                               if vi else "Installer payload missing from app folder")
            with tarfile.open(PAYLOAD, "r:gz") as tf:
                tf.extractall(f"{SDCARD_PATH}/Emus")

        for rel in ("zulu17/bin/java", "zulu17/bin/sdl_interface"):
            p = os.path.join(EMU_DIR, rel)
            if os.path.exists(p):
                os.chmod(p, 0o755)

        # Restore any missing config file from the payload rather than generating
        # one. These are the package's own, known-good files; hand-written
        # replacements are what broke a working install before. control_cycle and
        # control_profile decide the pad layout, so a missing one leaves the player
        # with buttons that do not match what the emulator's guide describes.
        for member, dest in (("JAVA/config.json", f"{EMU_DIR}/config.json"),
                             ("JAVA/launch.sh", f"{EMU_DIR}/launch.sh"),
                             ("JAVA/zulu17/bin/renderer.conf", renderer_conf_path()),
                             ("JAVA/zulu17/bin/control_cycle.cfg", f"{RUNTIME_DIR}/bin/control_cycle.cfg"),
                             ("JAVA/zulu17/bin/control_profile.cfg", f"{RUNTIME_DIR}/bin/control_profile.cfg")):
            if os.path.exists(dest) or not has_payload():
                continue
            try:
                with tarfile.open(PAYLOAD, "r:gz") as tf:
                    src = tf.extractfile(member)
                    if src:
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, "wb") as out:
                            out.write(src.read())
            except Exception as e:
                print(f"restore {member} failed: {e}")

        lp = f"{EMU_DIR}/launch.sh"
        if os.path.exists(lp):
            os.chmod(lp, 0o755)

        # A reinstall wipes zulu17, and renderer.conf lives inside it, so put the
        # user's display preset back on top of the restored default.
        if saved_mode:
            save_render_mode(saved_mode)

        # The stock menu caches its rom list; a stale cache would keep launching the
        # old flat paths and never find games in the resolution folders.
        for db in ("JAVA_cache7.db", "JAVA_cache6.db", "JAVA_cache.db"):
            try:
                os.remove(os.path.join(ROM_DIR, db))
            except Exception:
                pass

        missing = j2me_missing_parts()
        if missing:
            return False, ("Cài chưa đủ, còn thiếu: " if vi else "Incomplete, missing: ") + ", ".join(missing)

        if "JAVA" not in state.catalogs:
            state.catalogs["JAVA"] = {
                "system_name": "Java J2ME (Mobile .jar)",
                "rom_dir": ROM_DIR, "img_dir": IMG_DIR, "games": [],
            }
        if force:
            return True, ("Đã cài lại giả lập Java J2ME" if vi else "Java J2ME emulator reinstalled")
        return True, ("Đã cài giả lập Java J2ME" if vi else "Java J2ME emulator installed")
    except Exception as e:
        print(f"J2ME install error: {e}")
        return False, (f"Lỗi cài đặt: {e}" if vi else f"Install failed: {e}")
