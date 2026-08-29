# -*- coding: utf-8 -*-
"""Self-update from a published manifest.

The app ships as sourceless bytecode, so an update is just a set of files to
swap. The manifest lists every shipped file with its sha256; only the ones that
differ from what is already on disk get fetched.

Nothing is moved into place until every file has been downloaded *and* its hash
checked, so a dropped connection halfway through leaves the running install
untouched rather than half-replaced."""

import hashlib
import json
import os
import shutil
import ssl
import urllib.error
import urllib.request

from . import state
from .paths import APP_DIR
from .version import APP_VERSION, is_newer

# Where releases are published. Overridable from settings.json so a repo move
# does not need a rebuild.
UPDATE_BASE_URL = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main"

# Downloads land here first. It has to sit inside APP_DIR: os.replace cannot
# rename across filesystems, and /tmp is a different one on this device.
STAGING_DIR = os.path.join(APP_DIR, ".update_staging")

UA = "RetroHub/%s" % APP_VERSION
TIMEOUT = 20

# Refuse a manifest that is implausibly large or names paths outside the app.
MAX_MANIFEST_BYTES = 512 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024


def base_url():
    return (getattr(state, "update_url", "") or UPDATE_BASE_URL).rstrip("/")


def _get(url, max_bytes):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT) as resp:
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("response larger than %d bytes" % max_bytes)
    return data


def _safe_rel(rel):
    """True when *rel* stays inside the app directory.

    The manifest is fetched over the network, so a path like ``../../etc/x`` or
    ``/etc/x`` must never be honoured."""
    if not rel or rel.startswith("/") or "\\" in rel:
        return False
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    return True


def sha256_of(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 18), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def fetch_manifest():
    """Download and validate the published manifest. None when unavailable."""
    try:
        raw = _get(base_url() + "/manifest.json", MAX_MANIFEST_BYTES)
        m = json.loads(raw.decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, UnicodeDecodeError) as e:
        print("Update check failed: %s" % e)
        return None

    if not isinstance(m, dict) or not m.get("version") or not isinstance(m.get("files"), list):
        print("Update check failed: malformed manifest")
        return None
    for f in m["files"]:
        if not isinstance(f, dict) or not _safe_rel(f.get("path", "")) or len(f.get("sha256", "")) != 64:
            print("Update check failed: bad entry %r" % (f.get("path") if isinstance(f, dict) else f))
            return None
    return m


def release_note(manifest, lang="VI"):
    """Mot dong noi ban moi sua gi, lay tu manifest. "" khi khong co.

    Man hinh cap nhat cu chi noi co ban moi va bao nhieu tep phai tai, tu do
    khong ai biet co dang cai bay gio hay de sau. Manifest den tu mang va moi
    ban phat hanh cu deu khong co truong nay, nen o day khong duoc tin gi ca:
    thieu, sai kieu hay rong thi coi nhu khong co ghi chu."""
    note = (manifest or {}).get("note") if isinstance(manifest, dict) else None
    if isinstance(note, str):
        note = {"vi": note, "en": note}
    if not isinstance(note, dict):
        return ""
    key = str(lang or "VI").lower()
    other = "en" if key == "vi" else "vi"
    for k in (key, other):
        text = note.get(k)
        if isinstance(text, str) and text.strip():
            # Modal ve tung dong nguyen van, nen ghi chu phai phang lam mot dong.
            return " ".join(text.split())
    return ""


def pending_files(manifest):
    """Files whose on-disk hash differs from the manifest."""
    out = []
    for f in manifest["files"]:
        local = os.path.join(APP_DIR, f["path"])
        if sha256_of(local) != f["sha256"]:
            out.append(f)
    return out


def check_for_update(force=False):
    """(manifest, files) when a newer version is published, else None.

    Versions the user chose to skip are treated as already handled - except
    when *force* is set, which is the case for a check the user asked for by
    hand. Having explicitly gone looking, they should not be told there is
    nothing there because of a skip they made earlier."""
    m = fetch_manifest()
    if not m:
        return None
    if not is_newer(m["version"], APP_VERSION):
        return None
    if not force and m["version"] in (state.skipped_versions or []):
        return None
    return m, pending_files(m)


def download_update(manifest, files, progress=None):
    """Fetch every pending file into staging and verify it. True on success.

    A failed attempt takes its half-written staging tree with it, so nothing
    partial is left sitting inside the app directory."""
    ok = _stage_files(manifest, files, progress)
    if not ok:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
    return ok


def _stage_files(manifest, files, progress=None):
    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    try:
        os.makedirs(STAGING_DIR, exist_ok=True)
    except OSError as e:
        print("Update staging failed: %s" % e)
        return False

    total = len(files)
    for i, f in enumerate(files):
        if progress:
            progress(i, total, f["path"])
        url = "%s/files/%s" % (base_url(), f["path"])
        try:
            data = _get(url, MAX_FILE_BYTES)
        except (urllib.error.URLError, OSError, ValueError) as e:
            print("Update download failed for %s: %s" % (f["path"], e))
            return False
        if hashlib.sha256(data).hexdigest() != f["sha256"]:
            print("Update hash mismatch for %s" % f["path"])
            return False
        dst = os.path.join(STAGING_DIR, f["path"])
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(data)
        except OSError as e:
            print("Update write failed for %s: %s" % (f["path"], e))
            return False
    if progress:
        progress(total, total, "")
    return True


def apply_update(manifest, files):
    """Move verified files into place. True when the install completed.

    os.replace, never open("w"): launch.sh is being executed by the shell that
    started this process, and truncating it mid-run corrupts the script. A
    rename swaps the directory entry while the running shell keeps reading the
    old inode."""
    # Install the version marker last. If the run dies partway through, the
    # on-disk version still reads as the old one, so the next launch sees the
    # update as outstanding and retries the files that did not make it, instead
    # of believing it is already up to date.
    ordered = sorted(files, key=lambda f: f["path"] == "rh/version.py")

    moved = 0
    for f in ordered:
        src = os.path.join(STAGING_DIR, f["path"])
        dst = os.path.join(APP_DIR, f["path"])
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)
            if f["path"].endswith(".sh"):
                os.chmod(dst, 0o755)
            moved += 1
        except OSError as e:
            print("Update install failed for %s: %s" % (f["path"], e))
            return False

    # Drop sources left over from a pre-bytecode install: Python prefers a .py
    # next to a .pyc, so a stale app.py would keep winning after the update.
    for rel in manifest.get("remove", []):
        if not _safe_rel(rel):
            continue
        try:
            os.remove(os.path.join(APP_DIR, rel))
        except OSError:
            pass
    _purge_pycache()

    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    print("Update installed: %d file(s) -> %s" % (moved, manifest["version"]))
    return True


def _purge_pycache():
    """Remove __pycache__ trees so no stale cached module outranks a new one.

    python/ is skipped: it is the bundled interpreter the Brick Pro needs, and
    its stdlib ships precompiled. Those caches belong to files this updater
    never touches, and wiping them on every update would only make the next
    launch recompile the standard library on a slow card."""
    for root, dirs, _ in os.walk(APP_DIR):
        if root == APP_DIR and "python" in dirs:
            dirs.remove("python")
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def skip_version(version):
    if version not in state.skipped_versions:
        state.skipped_versions.append(version)
        state.save_settings()


def request_restart():
    """Ask launch.sh to run the app again instead of returning to the menu.

    The launcher already loops while /tmp/launch_game.sh exists, so dropping a
    no-op script there restarts the app with the new bytecode."""
    try:
        with open("/tmp/launch_game.sh", "w") as f:
            f.write("#!/bin/sh\n:\n")
        os.chmod("/tmp/launch_game.sh", 0o755)
        return True
    except OSError as e:
        print("Restart request failed: %s" % e)
        return False
