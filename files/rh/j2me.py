# -*- coding: utf-8 -*-
"""Java J2ME support.

Runtime is the SDL2 build of FreeJ2ME: a bundled JRE runs freej2me-sdl.jar, which
drives the native sdl_interface straight onto the framebuffer. No RetroArch and no
libretro core are involved.

Screen size is chosen by which folder a game sits in - Roms/JAVA/240320 and friends -
because J2ME titles are each built for one specific handset resolution.
"""

import os
import json
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

# Phone keys the native side actually honours, in the order its lookup table lists
# them. The two Chinese names are the left and right softkeys (KEY_LEFT/KEY_RIGHT);
# they are stored as UTF-8 in the binary, which is why an ASCII-only scan misses
# them. There is no key 5 - OK is the centre/fire key that games use in its place.
SOFT_LEFT = "\u5de6\u952e"
SOFT_RIGHT = "\u53f3\u952e"
VALID_KEYS = [SOFT_LEFT, SOFT_RIGHT, "OK", "*", "#", "0", "1", "3", "7", "9"]
# Pad buttons that can be bound to them.
VALID_BUTTONS = ["A", "B", "X", "Y", "L", "R", "L2", "R2", "SELECT", "START"]

# The package's own mapping, copied from the keymap.cfg inside the payload so the
# two cannot drift. This is what the emulator ships with and what works.
DEFAULT_KEYMAP = {
    "左键": "Y",
    "右键": "A",
    "OK": "X",
    "*": "SELECT",
    "#": "START",
    "0": "B",
    "1": "L",
    "3": "R",
    "7": "L2",
    "9": "R2",
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


def has_payload():
    """True when the bundled installer archive is present in the app folder."""
    return os.path.exists(PAYLOAD)


# ------------------------------------------------------------------ key mapping
def keymap_path():
    return f"{RUNTIME_DIR}/bin/keymap.cfg"


def load_keymap():
    """Current phone-key -> pad-button map, falling back to the default."""
    try:
        with open(keymap_path(), "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Drop entries the native side does not understand rather than passing
        # them on; they would look bound in the UI but do nothing in game.
        cleaned = {k: v for k, v in raw.items()
                   if k in VALID_KEYS and v in VALID_BUTTONS}
        return cleaned or dict(DEFAULT_KEYMAP)
    except Exception:
        return dict(DEFAULT_KEYMAP)


def save_keymap(mapping):
    """Write the map back, keeping only bindings the native side honours."""
    cleaned = {k: v for k, v in mapping.items()
               if k in VALID_KEYS and v in VALID_BUTTONS}
    try:
        os.makedirs(os.path.dirname(keymap_path()), exist_ok=True)
        with open(keymap_path(), "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving J2ME keymap: {e}")
        return False


def button_in_use(mapping, button, except_key=None):
    """Which phone key currently holds this button, if any."""
    for k, v in mapping.items():
        if v == button and k != except_key:
            return k
    return None


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
    install that has gone bad. The key mapping is kept: it is validated on load, so
    a damaged one cannot break the emulator, and losing it would be a nasty
    surprise for someone who only wanted to fix a crash.
    """
    vi = state.current_lang == "VI"
    try:
        saved_keys = load_keymap() if force else None
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
        # one. These three are the package's own, known-good files; hand-written
        # replacements are what broke a working install before.
        for member, dest in (("JAVA/config.json", f"{EMU_DIR}/config.json"),
                             ("JAVA/launch.sh", f"{EMU_DIR}/launch.sh"),
                             ("JAVA/zulu17/bin/keymap.cfg", keymap_path())):
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

        # A reinstall wipes zulu17, and the keymap lives inside it, so put the
        # user's bindings back on top of the restored default.
        if saved_keys:
            save_keymap(saved_keys)

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
