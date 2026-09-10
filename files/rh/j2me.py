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
import re
import shutil
import tarfile
import tempfile
import zipfile

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
# Doi tu 240320 sang 320240: chi khoang mot phan tu so muc Java khai kich thuoc
# trong ten file, phan con lai roi vao mac dinh nay. Man may la 4:3 nam ngang,
# nen 320x240 lap day duoc con 240x320 de lai hai vien den hai ben. Game nao ten
# co ghi ro kich thuoc thi van ve dung thu muc cua no - resolution_from_filename
# doc truoc, mac dinh chi la duong lui.
DEFAULT_RESOLUTION = "320240"

# Display presets, straight out of the emulator's own guide. The renderer is the
# one thing about this build worth setting from the app: the three modes differ by
# five keys at once, not one, and getting a mismatched pair (say pixel mode with
# integer scaling off) looks broken rather than different.
#
# There is deliberately no key mapping here any more. This build ignores
# keymap.cfg - it parses the file at startup and never reads the values back - and
# picks the pad layout from control_profile.cfg/control_cycle.cfg instead, which
# the player cycles on the device with START+SELECT.
RENDER_MODES = ["hq", "smooth", "pixel"]
DEFAULT_RENDER_MODE = "hq"
RENDER_PRESETS = {
    "hq":     {"render_mode": "hq",     "integer_scaling": "false", "keep_aspect": "true",
               "text_aa": "true",  "shape_aa": "true",  "m3g_filter": "linear"},
    "smooth": {"render_mode": "smooth", "integer_scaling": "false", "keep_aspect": "true",
               "text_aa": "true",  "shape_aa": "true",  "m3g_filter": "linear"},
    "pixel":  {"render_mode": "pixel",  "integer_scaling": "true",  "keep_aspect": "true",
               "text_aa": "false", "shape_aa": "false", "m3g_filter": "nearest"},
}


# Default keypad profile (phone mode): N (Nokia - recommended GameAction navigation),
# P (Plain - 2/4/6/8/5), E (Sony Ericsson), S (Siemens), M (Motorola).
PHONE_MODES = ["N", "P", "E", "S", "M"]
DEFAULT_PHONE_MODE = "N"

# The player's save and config data: stored safely in persistent folders outside
# zulu17 runtime directory so JRE reinstalls or updates NEVER wipe saves.
PERSISTENT_RMS = f"{EMU_DIR}/rms"
PERSISTENT_CONFIG = f"{EMU_DIR}/config"
BACKUP_DIR = f"{EMU_DIR}/saves_backup"

USER_DATA_DIRS = ("bin/rms", "bin/config")
USER_DATA_FILES = ()


def default_phone_cfg_path():
    return f"{EMU_DIR}/default_phone.cfg"


def load_default_phone_mode():
    """Returns current default phone keypad profile ('N', 'P', 'E', 'S', 'M')."""
    for p in (default_phone_cfg_path(), f"{RUNTIME_DIR}/bin/default_phone.cfg"):
        try:
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    val = f.read().strip().upper()
                    if val in PHONE_MODES:
                        return val
        except Exception:
            pass
    return DEFAULT_PHONE_MODE


def save_default_phone_mode(mode):
    """Saves default phone keypad profile. Returns True on success."""
    if mode not in PHONE_MODES:
        return False
    val = mode.strip().lower()
    success = False
    for p in (default_phone_cfg_path(), f"{RUNTIME_DIR}/bin/default_phone.cfg"):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(val + "\n")
            success = True
        except Exception as e:
            print(f"Error writing {p}: {e}")
    return success


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


# Answers cached against each file's own (size, mtime): the menus rebuild their
# rows every frame, and reading a 450KB binary - let alone a 66MB archive - at
# 60fps is not something to do to an SD card.
_probe_cache = {}


def _cached_probe(path, key, probe):
    """Run `probe` once per version of `path`, keyed on its size and mtime."""
    try:
        st = os.stat(path)
        stamp = (st.st_size, st.st_mtime_ns)
    except Exception:
        _probe_cache.pop(key, None)
        return False
    hit = _probe_cache.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        answer = probe(path)
    except Exception:
        answer = False
    _probe_cache[key] = (stamp, answer)
    return answer


def runtime_supports_renderer():
    """True when the installed sdl_interface is a build that reads renderer.conf or graphics.cfg.

    An in-app update carries only the app's .py files - the 66MB runtime ships
    with the full package, not on every update - so a device can end up running
    this version of the app against the older emulator. That build has no
    renderer.conf/graphics.cfg, and a display screen wired to a binary that
    ignores it is a screen that does nothing.
    """
    def probe(path):
        with open(path, "rb") as f:
            data = f.read()
            return (b"renderer.conf" in data) or (b"graphics.cfg" in data)
    return _cached_probe(j2me_runtime_paths()["sdl"], "runtime", probe)


# The two files that decide which emulator is installed. Sizes are compared
# rather than hashes: hashing 66MB on this hardware costs seconds, while the tar
# header carries the size for free and no two builds of these have ever matched
# byte-count without being the same build.
_VERSIONED = {"jar": "zulu17/bin/freej2me-sdl.jar",
              "sdl": "zulu17/bin/sdl_interface"}

# Known target binary sizes for current release (FreeJ2ME v1.82+).
CURRENT_RUNTIME_SIZES = {
    "jar": 1483099,
    "sdl": 450072,
}


def target_runtime_sizes():
    """Dynamically determine target binary sizes from APP_DIR/emus/JAVA if present, else fallback."""
    sizes = dict(CURRENT_RUNTIME_SIZES)
    bundled_jar = os.path.join(APP_DIR, "emus", "JAVA", "zulu17", "bin", "freej2me-sdl.jar")
    if os.path.isfile(bundled_jar):
        try:
            sizes["jar"] = os.path.getsize(bundled_jar)
        except OSError:
            pass
    bundled_sdl = os.path.join(APP_DIR, "emus", "JAVA", "zulu17", "bin", "sdl_interface")
    if os.path.isfile(bundled_sdl):
        try:
            sizes["sdl"] = os.path.getsize(bundled_sdl)
        except OSError:
            pass
    return sizes


def is_runtime_current():
    """True when the emulator binaries on disk match the current target release."""
    if not is_j2me_runtime_ready():
        return False
    paths = j2me_runtime_paths()
    targets = target_runtime_sizes()
    for key, size in targets.items():
        try:
            if os.path.getsize(paths[key]) != size:
                return False
        except OSError:
            return False
    # Check if launch.sh in EMU_DIR differs from bundled launch.sh
    bundled_launch = os.path.join(APP_DIR, "emus", "JAVA", "launch.sh")
    if os.path.isfile(bundled_launch):
        try:
            target_launch = f"{EMU_DIR}/launch.sh"
            if not os.path.exists(target_launch) or os.path.getsize(bundled_launch) != os.path.getsize(target_launch):
                return False
        except OSError:
            return False
    return True


def runtime_is_stale():
    """True when the emulator on the card is missing, unconfigured, or differs from current release."""
    if not is_j2me_runtime_ready():
        return True
    if not is_runtime_current():
        return True
    return False


def sync_bundled_runtime_files():
    """Copies newer or missing emulator files from APP_DIR/emus/JAVA to SDCARD_PATH/Emus/JAVA.
    Returns list of updated file basenames.
    """
    bundled_root = os.path.join(APP_DIR, "emus", "JAVA")
    if not os.path.isdir(bundled_root):
        return []
    updated = []
    os.makedirs(EMU_DIR, exist_ok=True)
    os.makedirs(os.path.join(RUNTIME_DIR, "bin"), exist_ok=True)
    for root, _, files in os.walk(bundled_root):
        for fname in files:
            # Skip user-customized files if they already exist
            if fname in ("graphics.cfg", "renderer.conf", "default_phone.cfg"):
                dst = os.path.join(EMU_DIR, os.path.relpath(os.path.join(root, fname), bundled_root))
                if os.path.exists(dst):
                    continue
            src = os.path.join(root, fname)
            rel = os.path.relpath(src, bundled_root)
            dst = os.path.join(EMU_DIR, rel)
            should_copy = False
            if not os.path.exists(dst):
                should_copy = True
            else:
                try:
                    if os.path.getsize(src) != os.path.getsize(dst):
                        should_copy = True
                    elif os.path.getsize(src) < 65536:
                        with open(src, "rb") as f1, open(dst, "rb") as f2:
                            if f1.read() != f2.read():
                                should_copy = True
                except OSError:
                    should_copy = True
            if should_copy:
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    if fname in ("launch.sh", "sdl_interface", "java"):
                        try:
                            os.chmod(dst, 0o755)
                        except OSError:
                            pass
                    updated.append(fname)
                except Exception as e:
                    print(f"Error syncing {rel}: {e}")
    return updated


def ensure_latest_j2me_installed():
    """Ensure latest Java J2ME emulator is installed and up-to-date.
    Called both on app startup and after an app update.
    Returns (ok, message or None).
    """
    vi = state.current_lang == "VI"
    updated_files = []

    # 0. Always safeguard, recover and sync user saves first
    try:
        recover_orphaned_saves()
        sync_persistent_saves_to_runtime()
        sync_user_saves_to_persistent()
    except Exception as e:
        print(f"Save sync warning: {e}")

    # 1. If Java JRE is missing and payload exists, unpack full JRE
    if not os.path.exists(f"{RUNTIME_DIR}/bin/java") and has_payload():
        ok, msg = install_j2me_emulator(force=False)
        if not ok:
            return False, msg
        updated_files.append("java")

    # 2. Always sync latest bundled files from APP_DIR/emus/JAVA
    synced = sync_bundled_runtime_files()
    if synced:
        updated_files.extend(synced)
        _probe_cache.pop("runtime", None)

    # 3. Ensure configs and directories exist
    ensure_rom_dirs()
    if not os.path.exists(renderer_conf_path()) and not os.path.exists(graphics_cfg_path()):
        save_render_mode(DEFAULT_RENDER_MODE)
    if not os.path.exists(default_phone_cfg_path()):
        save_default_phone_mode(DEFAULT_PHONE_MODE)

    # 4. Ensure executable permissions
    for p in (f"{EMU_DIR}/launch.sh", f"{RUNTIME_DIR}/bin/sdl_interface", f"{RUNTIME_DIR}/bin/java"):
        if os.path.exists(p):
            try:
                os.chmod(p, 0o755)
            except OSError:
                pass

    # 5. Ensure NextUI Pak
    for plat in ("tg5040", "tg5050"):
        pak_dir = f"{SDCARD_PATH}/Emus/{plat}/JAVA.pak"
        try:
            os.makedirs(pak_dir, exist_ok=True)
            launch_dest = f"{pak_dir}/launch.sh"
            if not os.path.exists(launch_dest) and os.path.exists(f"{EMU_DIR}/launch.sh"):
                shutil.copy2(f"{EMU_DIR}/launch.sh", launch_dest)
                os.chmod(launch_dest, 0o755)
            cfg_dest = f"{pak_dir}/config.json"
            if not os.path.exists(cfg_dest) and os.path.exists(f"{EMU_DIR}/config.json"):
                shutil.copy2(f"{EMU_DIR}/config.json", cfg_dest)
        except Exception as e:
            print(f"Failed to setup {plat} JAVA.pak: {e}")

    if updated_files:
        msg = ("Đã cài đặt/cập nhật Giả lập Java mới nhất" if vi
               else "Installed/updated latest Java emulator")
        return True, msg
    return True, None


def has_payload():
    """True when the bundled installer archive is present in the app folder."""
    return os.path.exists(PAYLOAD)


# ------------------------------------------------------------------ renderer
def renderer_conf_path():
    return f"{RUNTIME_DIR}/bin/renderer.conf"


def graphics_cfg_path():
    return f"{RUNTIME_DIR}/bin/graphics.cfg"


def load_render_mode():
    """Which of the three presets is in force, from renderer.conf or graphics.cfg."""
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
    try:
        with open(graphics_cfg_path(), "r", encoding="utf-8") as f:
            val = f.read().strip()
            if val == "0":
                return "pixel"
            elif val == "1":
                return "smooth"
    except Exception:
        pass
    return DEFAULT_RENDER_MODE


def save_render_mode(mode):
    """Write preset out to both graphics.cfg and renderer.conf. Returns True when saved."""
    if mode not in RENDER_MODES:
        return False
    # graphics.cfg: 0 = nearest/pixel, 1 = linear/smooth/hq
    g_val = "0" if mode == "pixel" else "1"
    try:
        os.makedirs(os.path.dirname(graphics_cfg_path()), exist_ok=True)
        with open(graphics_cfg_path(), "w", encoding="utf-8") as f:
            f.write(g_val + "\n")
    except Exception as e:
        print(f"Error saving J2ME graphics.cfg: {e}")

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
    """Folder a jar belongs in, read out of its name, e.g. Game_240x320.jar.

    Two things a single leftmost match gets wrong, both seen in the catalogue:

    A year is not a screen size. "Wimbledon-2009-320x240.jar" contains "009-320"
    before it contains "320x240", and a hyphen used to count as a separator - so
    the first match was a pair no folder is named after, and the whole name fell
    through to the default. That put 320x240 builds in the 240x320 folder.

    A variant name carries both sizes. These sources name a variant by appending
    its size to the base name, so "Sushi-Suffle-240x320-320x240.jar" is the
    320x240 build of a jar whose own name already said 240x320. The size that
    counts is the last one, not the first.

    So: every explicit "x" pair is considered and the last valid one wins, and
    the looser separators are only consulted when no "x" pair names a folder.

    Only about a quarter of Java entries state a size at all - the jar manifest
    has no size attribute and the catalogue has no column for it - so anything
    unrecognised goes to the default and can be moved afterwards.
    """
    name = filename or ""
    for pattern in (r"(\d{2,3})\s*[xX]\s*(\d{2,3})",
                    r"(\d{2,3})\s*[_\-]\s*(\d{2,3})"):
        found = None
        for m in re.finditer(pattern, name):
            for cand in (m.group(1) + m.group(2), m.group(2) + m.group(1)):
                if cand in RESOLUTIONS:
                    found = cand
                    break
        if found:
            return found
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


# Characters the emulator cannot survive in a file name. It opens a jar by
# building a "jar:file:<path>" URI and handing that to the zip filesystem, with
# nothing percent-encoded - so a single space makes java.net.URI throw
# "Illegal character in opaque part", the manifest goes unread, and the game
# dies with a null MIDlet class before drawing anything. Brackets do the same.
# 758 of the 3,357 Java sources in the catalogue carry one of these.
_UNSAFE_IN_URI = re.compile(r'[\s"<>#%{}|\\^`\[\]]+')


def safe_jar_name(filename):
    """A file name this emulator can actually open. Extension is kept."""
    stem, ext = os.path.splitext(filename or "")
    stem = _UNSAFE_IN_URI.sub("_", stem).strip("_")
    return (stem or "game") + ext


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
        drop_rom_cache()
        return dst
    except Exception as e:
        print(f"move_to_resolution failed: {e}")
        return None


def strip_encrypted_markers(jar_path):
    """Drop zero-length entries flagged encrypted. True when the jar was rewritten.

    The emulator opens a jar as a Java zip filesystem, and that refuses the whole
    archive the moment any entry carries the encryption bit - "invalid CEN header
    (encrypted entry)" - even when nothing ever reads that entry. Some packers
    leave a zero-byte "Password" entry with the bit set as a watermark, and one
    of those makes an otherwise perfect game unopenable.

    Only empty entries are dropped. One that actually carries bytes might be
    something the game needs, and quietly deleting it would be damaging the game
    rather than repairing it - better to leave it and let the failure stay
    visible.
    """
    try:
        with zipfile.ZipFile(jar_path) as zin:
            infos = zin.infolist()
            marked = [i for i in infos if i.flag_bits & 0x1]
            if not marked or any(i.file_size for i in marked):
                return False
            keep = [i for i in infos if not (i.flag_bits & 0x1)]
            tmp = jar_path + ".rh_tmp"
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                for i in keep:
                    zout.writestr(i, zin.read(i.filename))
    except Exception as e:
        print(f"strip markers {os.path.basename(jar_path)} failed: {e}")
        try:
            os.remove(jar_path + ".rh_tmp")
        except OSError:
            pass
        return False
    try:
        os.replace(tmp, jar_path)
    except OSError as e:
        print(f"replace {os.path.basename(jar_path)} failed: {e}")
        return False
    return True


def repair_encrypted_jars():
    """Rewrite jars the emulator cannot open. Returns how many were fixed.

    Cheap enough to run at every startup: it reads each jar's central directory,
    not its contents, and only rewrites the ones that carry the marker.
    """
    fixed = 0
    for folder, _ in _rom_folders():
        try:
            entries = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in entries:
            if name.lower().endswith(".jar") and strip_encrypted_markers(
                    os.path.join(folder, name)):
                fixed += 1
    return fixed


def _rename_game_data(old_stem, new_stem, res):
    """Follow a renamed jar with the folders the emulator keeps for it.

    Both config/ and rms/ are named after the jar's stem with the resolution
    stuck on the end - "Ninja School 1" in 240320 becomes "Ninja School 1240320"
    - so a jar that changes name would otherwise leave its saves behind under a
    name nothing looks for again.
    """
    for sub in ("config", "rms"):
        src = os.path.join(RUNTIME_DIR, "bin", sub, old_stem + res)
        dst = os.path.join(RUNTIME_DIR, "bin", sub, new_stem + res)
        if os.path.isdir(src) and not os.path.exists(dst):
            try:
                os.rename(src, dst)
            except Exception as e:
                print(f"rename {sub}/{old_stem}{res} failed: {e}")

    # Box art is filed under the rom's own stem, so it has to move too or the
    # game loses its picture the moment the jar is renamed.
    src = os.path.join(IMG_DIR, old_stem + ".png")
    dst = os.path.join(IMG_DIR, new_stem + ".png")
    if os.path.isfile(src) and not os.path.exists(dst):
        try:
            os.rename(src, dst)
        except Exception as e:
            print(f"rename boxart {old_stem} failed: {e}")


def _rom_folders():
    """[(duong dan, ten thu muc)] cho moi cho co the chua game Java.

    Khong chi nam thu muc do phan giai: phep quet noi bo cua app nhat ca tep nam
    thang trong Roms/JAVA lan trong bat ky thu muc con nao, nen mot lan sua chi
    di qua nam thu muc quen thuoc se bo lai tep ma app van liet ke va van khong
    mo duoc.
    """
    out = [(ROM_DIR, "")]
    try:
        for name in sorted(os.listdir(ROM_DIR)):
            path = os.path.join(ROM_DIR, name)
            if os.path.isdir(path):
                out.append((path, name))
    except OSError:
        pass
    return out


def repair_unsafe_jar_names():
    """Rename jars this emulator cannot open. Returns how many were renamed.

    A file name with a space in it is not a cosmetic problem here: the emulator
    cannot read the jar's manifest at all, so the game dies before drawing a
    frame. Games downloaded before this was fixed are already sitting on the
    card under those names, and re-downloading would not help - the fix has to
    reach the files that are already there.
    """
    renamed = 0
    for folder, res in _rom_folders():
        try:
            entries = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in entries:
            if not name.lower().endswith(".jar"):
                continue
            safe = safe_jar_name(name)
            if safe == name:
                continue
            src, dst = os.path.join(folder, name), os.path.join(folder, safe)
            # A copy under the safe name already there means the player has the
            # game twice; renaming over it would destroy the working one.
            if os.path.exists(dst):
                continue
            try:
                os.rename(src, dst)
            except Exception as e:
                print(f"rename {name} failed: {e}")
                continue
            _rename_game_data(os.path.splitext(name)[0],
                              os.path.splitext(safe)[0], res)
            renamed += 1
    if renamed:
        drop_rom_cache()
    return renamed


def drop_rom_cache():
    """Forget the stock menu's cached game list.

    It caches by path, so after anything moves or is renamed it keeps launching
    a file that is no longer there.
    """
    for db in ("JAVA_cache7.db", "JAVA_cache6.db", "JAVA_cache.db"):
        try:
            os.remove(os.path.join(ROM_DIR, db))
        except Exception:
            pass


# ------------------------------------------------------------------ launcher & persistent save safeguards
def recover_orphaned_saves():
    """Scan and recover any saves left behind in .rh_j2me_* temporary folders from previous crashes."""
    recovered = 0
    if not os.path.isdir(EMU_DIR):
        return 0
    try:
        for entry in os.listdir(EMU_DIR):
            if entry.startswith(".rh_j2me_"):
                stash_dir = os.path.join(EMU_DIR, entry)
                if not os.path.isdir(stash_dir):
                    continue
                for sub in ("bin/rms", "rms"):
                    src_rms = os.path.join(stash_dir, sub)
                    if os.path.isdir(src_rms):
                        os.makedirs(PERSISTENT_RMS, exist_ok=True)
                        os.makedirs(os.path.join(RUNTIME_DIR, "bin", "rms"), exist_ok=True)
                        for game_f in os.listdir(src_rms):
                            s_p = os.path.join(src_rms, game_f)
                            p_dst = os.path.join(PERSISTENT_RMS, game_f)
                            r_dst = os.path.join(RUNTIME_DIR, "bin", "rms", game_f)
                            try:
                                if os.path.isdir(s_p):
                                    if not os.path.exists(p_dst):
                                        shutil.copytree(s_p, p_dst)
                                    if not os.path.exists(r_dst):
                                        shutil.copytree(s_p, r_dst)
                                    recovered += 1
                            except Exception as e:
                                print(f"Error restoring orphaned save {s_p}: {e}")
                shutil.rmtree(stash_dir, ignore_errors=True)
    except Exception as e:
        print(f"Error recovering orphaned saves: {e}")
    return recovered


def sync_user_saves_to_persistent():
    """Deep-copy all user saves (RMS) and game configs to persistent directory outside zulu17."""
    os.makedirs(PERSISTENT_RMS, exist_ok=True)
    os.makedirs(PERSISTENT_CONFIG, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rt_rms = os.path.join(RUNTIME_DIR, "bin", "rms")
    rt_cfg = os.path.join(RUNTIME_DIR, "bin", "config")
    if os.path.isdir(rt_rms):
        for g in os.listdir(rt_rms):
            src = os.path.join(rt_rms, g)
            dst1 = os.path.join(PERSISTENT_RMS, g)
            dst2 = os.path.join(BACKUP_DIR, g)
            try:
                if os.path.isdir(src):
                    if os.path.exists(dst1):
                        shutil.rmtree(dst1, ignore_errors=True)
                    shutil.copytree(src, dst1)
                    if os.path.exists(dst2):
                        shutil.rmtree(dst2, ignore_errors=True)
                    shutil.copytree(src, dst2)
            except Exception as e:
                print(f"Error syncing {src} to persistent: {e}")
    if os.path.isdir(rt_cfg):
        for g in os.listdir(rt_cfg):
            src = os.path.join(rt_cfg, g)
            dst1 = os.path.join(PERSISTENT_CONFIG, g)
            try:
                if os.path.isdir(src):
                    if os.path.exists(dst1):
                        shutil.rmtree(dst1, ignore_errors=True)
                    shutil.copytree(src, dst1)
            except Exception as e:
                print(f"Error syncing config {src}: {e}")


def sync_persistent_saves_to_runtime():
    """Copy persistent user saves and configs back to runtime working directory."""
    rt_rms = os.path.join(RUNTIME_DIR, "bin", "rms")
    rt_cfg = os.path.join(RUNTIME_DIR, "bin", "config")
    os.makedirs(rt_rms, exist_ok=True)
    os.makedirs(rt_cfg, exist_ok=True)
    if os.path.isdir(PERSISTENT_RMS):
        for g in os.listdir(PERSISTENT_RMS):
            src = os.path.join(PERSISTENT_RMS, g)
            dst = os.path.join(rt_rms, g)
            try:
                if os.path.isdir(src) and not os.path.exists(dst):
                    shutil.copytree(src, dst)
            except Exception as e:
                print(f"Error copying {src} to runtime: {e}")
    if os.path.isdir(PERSISTENT_CONFIG):
        for g in os.listdir(PERSISTENT_CONFIG):
            src = os.path.join(PERSISTENT_CONFIG, g)
            dst = os.path.join(rt_cfg, g)
            try:
                if os.path.isdir(src) and not os.path.exists(dst):
                    shutil.copytree(src, dst)
            except Exception as e:
                print(f"Error copying config {src}: {e}")


def _safe_clean_runtime_dir():
    """Wipe JRE runtime binaries without touching user saves (bin/rms) or configs (bin/config)."""
    if not os.path.isdir(RUNTIME_DIR):
        return
    for sub in ("lib", "legal", "conf", "include", "man", ".java"):
        p = os.path.join(RUNTIME_DIR, sub)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    for item in os.listdir(RUNTIME_DIR):
        p = os.path.join(RUNTIME_DIR, item)
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass
    rt_bin = os.path.join(RUNTIME_DIR, "bin")
    if os.path.isdir(rt_bin):
        for item in os.listdir(rt_bin):
            if item in ("rms", "config"):
                continue
            p = os.path.join(rt_bin, item)
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    os.remove(p)
            except OSError:
                pass


def _stash_user_data(stash):
    """Safely copy user data to stash. Uses copytree so source data is never destroyed prematurely."""
    moved = []
    for rel in USER_DATA_DIRS:
        src = os.path.join(RUNTIME_DIR, rel)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(stash, rel)
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst)
            moved.append(rel)
        except Exception as e:
            print(f"stash {rel} failed: {e}")
    for rel in USER_DATA_FILES:
        src = os.path.join(RUNTIME_DIR, rel)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(stash, rel)
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            moved.append(rel)
        except Exception as e:
            print(f"stash {rel} failed: {e}")
    return moved


def _restore_user_data(stash):
    """Put stashed data back, merging over whatever the fresh runtime created."""
    for rel in USER_DATA_DIRS:
        src = os.path.join(stash, rel)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(RUNTIME_DIR, rel)
        try:
            os.makedirs(dst, exist_ok=True)
            for name in os.listdir(src):
                s_path, d_path = os.path.join(src, name), os.path.join(dst, name)
                if not os.path.exists(d_path):
                    if os.path.isdir(s_path):
                        shutil.copytree(s_path, d_path)
                    else:
                        shutil.copy2(s_path, d_path)
        except Exception as e:
            print(f"restore {rel} failed: {e}")
    for rel in USER_DATA_FILES:
        src = os.path.join(stash, rel)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(RUNTIME_DIR, rel)
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"restore {rel} failed: {e}")


def install_j2me_emulator(force=False):
    """Install the SDL runtime from the bundled payload and wire JAVA into the menu.

    Returns (ok, message). Saves and configurations are guaranteed to persist.
    """
    vi = state.current_lang == "VI"
    stash = None
    upgraded = False
    try:
        saved_mode = load_render_mode() if force else None
        saved_phone = load_default_phone_mode() if force else None

        # Safeguard user saves first
        recover_orphaned_saves()
        sync_user_saves_to_persistent()

        # Only clean JRE runtime binaries if user explicitly requested full repair/reinstall
        if force and os.path.isdir(RUNTIME_DIR):
            stash = tempfile.mkdtemp(prefix=".rh_j2me_", dir=EMU_DIR)
            _stash_user_data(stash)
            _safe_clean_runtime_dir()

        os.makedirs(EMU_DIR, exist_ok=True)
        os.makedirs(IMG_DIR, exist_ok=True)
        ensure_rom_dirs()

        # Unpack JRE payload only when java binary is missing
        if not os.path.exists(f"{RUNTIME_DIR}/bin/java"):
            if not has_payload():
                return False, ("Thiếu gói cài trong app (payload/j2me_sdl.tar.gz)"
                               if vi else "Installer payload missing from app folder")
            with tarfile.open(PAYLOAD, "r:gz") as tf:
                tf.extractall(f"{SDCARD_PATH}/Emus")
            upgraded = True
            _probe_cache.pop("runtime", None)

        # Restore user saves from persistent backup into runtime working dir
        sync_persistent_saves_to_runtime()

        # Always sync latest bundled files (freej2me-sdl.jar, sdl_interface, launch.sh, etc.)
        synced = sync_bundled_runtime_files()
        if synced:
            upgraded = True
            _probe_cache.pop("runtime", None)

        for rel in ("zulu17/bin/java", "zulu17/bin/sdl_interface"):
            p = os.path.join(EMU_DIR, rel)
            if os.path.exists(p):
                os.chmod(p, 0o755)

        # Restore any missing config file from the payload rather than generating one
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

        if saved_mode:
            save_render_mode(saved_mode)
        elif not os.path.exists(renderer_conf_path()) and not os.path.exists(graphics_cfg_path()):
            save_render_mode(DEFAULT_RENDER_MODE)

        if saved_phone:
            save_default_phone_mode(saved_phone)
        elif not os.path.exists(default_phone_cfg_path()):
            save_default_phone_mode(DEFAULT_PHONE_MODE)

        # The stock menu caches its rom list; drop cache after setup
        drop_rom_cache()

        # Setup NextUI Emulator Pak for tg5040 and tg5050
        for plat in ("tg5040", "tg5050"):
            pak_dir = f"{SDCARD_PATH}/Emus/{plat}/JAVA.pak"
            try:
                os.makedirs(pak_dir, exist_ok=True)
                pak_launch = os.path.join(pak_dir, "launch.sh")
                with open(pak_launch, "w") as f:
                    f.write("#!/bin/sh\n"
                            "ROM=\"$1\"\n"
                            "EMU_ROOT=\"/mnt/SDCARD/Emus/JAVA\"\n"
                            "if [ -f \"$EMU_ROOT/launch.sh\" ]; then\n"
                            "    exec \"$EMU_ROOT/launch.sh\" \"$ROM\"\n"
                            "else\n"
                            "    cd \"$EMU_ROOT/zulu17/bin\"\n"
                            "    exec ./java -Djava.awt.headless=true -jar ./freej2me-sdl.jar \"$ROM\"\n"
                            "fi\n")
                os.chmod(pak_launch, 0o755)
            except Exception as e:
                print(f"NextUI JAVA.pak setup failed: {e}")

        missing = j2me_missing_parts()
        if missing:
            return False, ("Cài chưa đủ, còn thiếu: " if vi else "Incomplete, missing: ") + ", ".join(missing)

        if "JAVA" not in state.catalogs:
            state.catalogs["JAVA"] = {
                "system_name": "Java J2ME (Mobile .jar)",
                "rom_dir": ROM_DIR, "img_dir": IMG_DIR, "games": [],
            }
        if upgraded:
            return True, ("Đã nâng cấp giả lập Java J2ME lên bản mới (Save game an toàn)"
                          if vi else "Java J2ME emulator upgraded (Save games preserved)")
        if force:
            return True, ("Đã cài lại giả lập Java J2ME (Save game an toàn)"
                          if vi else "Java J2ME emulator reinstalled (Save games preserved)")
        return True, ("Đã cài giả lập Java J2ME" if vi else "Java J2ME emulator installed")
    except Exception as e:
        print(f"J2ME install error: {e}")
        return False, (f"Lỗi cài đặt: {e}" if vi else f"Install failed: {e}")
    finally:
        if stash:
            _restore_user_data(stash)
            shutil.rmtree(stash, ignore_errors=True)
        try:
            sync_user_saves_to_persistent()
        except Exception:
            pass
