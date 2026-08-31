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


# The player's own data lives *inside* the runtime folder: rms/ holds J2ME game
# saves and config/ holds the per-game settings the emulator writes. A repair
# that wipes zulu17 to unpack a fresh copy would take both with it, so they are
# moved aside first and put back afterwards.
USER_DATA_DIRS = ("bin/rms", "bin/config")


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
    """True when the installed sdl_interface is a build that reads renderer.conf.

    An in-app update carries only the app's .py files - the 66MB runtime ships
    with the full package, not on every update - so a device can end up running
    this version of the app against the older emulator. That build has no
    renderer.conf at all, and a display screen wired to a binary that ignores it
    is a screen that does nothing.
    """
    def probe(path):
        with open(path, "rb") as f:
            return b"renderer.conf" in f.read()
    return _cached_probe(j2me_runtime_paths()["sdl"], "runtime", probe)


# The two files that decide which emulator is installed. Sizes are compared
# rather than hashes: hashing 66MB on this hardware costs seconds, while the tar
# header carries the size for free and no two builds of these have ever matched
# byte-count without being the same build.
_VERSIONED = {"jar": "zulu17/bin/freej2me-sdl.jar",
              "sdl": "zulu17/bin/sdl_interface"}


def payload_binary_sizes():
    """Sizes of the emulator binaries inside the bundled archive.

    Reads tar headers and stops once both are seen - they sit early in the
    stream. Measured at about 2s on a Brick Pro, and cached, so that is paid
    once per version of the payload.
    """
    def probe(path):
        want = dict(_VERSIONED)
        found = {}
        with tarfile.open(path, "r:gz") as tf:
            for m in tf:
                for key, tail in want.items():
                    if m.name.endswith(tail):
                        found[key] = m.size
                if len(found) == len(want):
                    break
        return found or False
    return _cached_probe(PAYLOAD, "payload", probe) or {}


def runtime_is_stale():
    """True when the emulator on the card is not the one inside the app.

    This is the ordinary state after an in-app update: updates carry the app's
    own files, never the 66MB runtime, so a device keeps whatever emulator it
    was installed with until something notices. Comparing against the payload
    rather than looking for one particular feature means a later change to the
    emulator is picked up too, without this having to learn a new marker each
    time.
    """
    if not is_j2me_runtime_ready():
        return False
    sizes = payload_binary_sizes()
    if not sizes:
        return False
    paths = j2me_runtime_paths()
    for key, size in sizes.items():
        try:
            if os.path.getsize(paths[key]) != size:
                return True
        except OSError:
            return True
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


# ------------------------------------------------------------------ launcher
def _stash_user_data(stash):
    """Move save data out of the runtime into `stash`. Returns what was moved."""
    moved = []
    for rel in USER_DATA_DIRS:
        src = os.path.join(RUNTIME_DIR, rel)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(stash, rel)
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            moved.append(rel)
        except Exception as e:
            print(f"stash {rel} failed: {e}")
    return moved


def _restore_user_data(stash):
    """Put stashed data back, merging over whatever the fresh runtime created.

    The unpacked archive carries rms/ and config/ as empty folders, so this walks
    the entries rather than moving the folder itself - a plain move would fail on
    a destination that already exists.
    """
    for rel in USER_DATA_DIRS:
        src = os.path.join(stash, rel)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(RUNTIME_DIR, rel)
        try:
            os.makedirs(dst, exist_ok=True)
            for name in os.listdir(src):
                s_path, d_path = os.path.join(src, name), os.path.join(dst, name)
                if os.path.isdir(d_path):
                    shutil.rmtree(d_path, ignore_errors=True)
                elif os.path.exists(d_path):
                    os.remove(d_path)
                shutil.move(s_path, d_path)
        except Exception as e:
            print(f"restore {rel} failed: {e}")


def install_j2me_emulator(force=False):
    """Install the SDL runtime from the bundled payload and wire JAVA into the menu.

    Returns (ok, message). The runtime ships inside the app so this works with no
    network - the archive is ~65MB of JRE, which is why it is not re-downloaded.

    force=True wipes the runtime first and unpacks it again, for repairing an
    install that has gone bad. Game saves, per-game settings and the chosen
    display preset all survive that: someone repairing a crash is not asking to
    lose their progress.

    A runtime older than the bundled archive is replaced the same way, without
    being asked. Leaving it in place was the old behaviour and it stranded
    people: the emulator they had still ran, so nothing looked broken, while
    every feature the newer one added stayed permanently out of reach.
    """
    vi = state.current_lang == "VI"
    stash = None
    upgraded = False
    try:
        stale = (not force) and runtime_is_stale()
        force = force or stale
        saved_mode = load_render_mode() if force else None
        if force and os.path.isdir(RUNTIME_DIR):
            stash = tempfile.mkdtemp(prefix=".rh_j2me_", dir=EMU_DIR)
            _stash_user_data(stash)
            shutil.rmtree(RUNTIME_DIR, ignore_errors=True)
        os.makedirs(EMU_DIR, exist_ok=True)
        os.makedirs(IMG_DIR, exist_ok=True)
        ensure_rom_dirs()

        # Unpack only when there is nothing there - a repair and an upgrade both
        # cleared the folder above, so both land here. Re-extracting 65MB on every
        # press would take minutes on this hardware.
        if not os.path.exists(f"{RUNTIME_DIR}/bin/java"):
            if not has_payload():
                return False, ("Thiếu gói cài trong app (payload/j2me_sdl.tar.gz)"
                               if vi else "Installer payload missing from app folder")
            with tarfile.open(PAYLOAD, "r:gz") as tf:
                tf.extractall(f"{SDCARD_PATH}/Emus")
            upgraded = stale
            # Both binaries on disk just changed under the cached answers.
            _probe_cache.pop("runtime", None)

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
            return True, ("Đã nâng cấp giả lập Java J2ME lên bản mới"
                          if vi else "Java J2ME emulator upgraded to the new build")
        if force:
            return True, ("Đã cài lại giả lập Java J2ME" if vi else "Java J2ME emulator reinstalled")
        return True, ("Đã cài giả lập Java J2ME" if vi else "Java J2ME emulator installed")
    except Exception as e:
        print(f"J2ME install error: {e}")
        return False, (f"Lỗi cài đặt: {e}" if vi else f"Install failed: {e}")
    finally:
        # Even when the unpack blew up: the saves go back where they belong
        # rather than staying in a hidden folder nobody will ever look in.
        if stash:
            _restore_user_data(stash)
            shutil.rmtree(stash, ignore_errors=True)
