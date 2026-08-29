# -*- coding: utf-8 -*-
"""Self-update from a published manifest.

The app ships as sourceless bytecode, so an update is just a set of files to
swap. The manifest lists every shipped file with its sha256; only the ones that
differ from what is already on disk get fetched.

Nothing is moved into place until every file has been downloaded *and* its hash
checked, so a dropped connection halfway through leaves the running install
untouched rather than half-replaced."""

import gzip
import hashlib
import json
import os
import shutil
import ssl
import urllib.error
import urllib.request

from . import state
from .paths import APP_DIR
from .storage import free_space as _free_space, human_bytes as _human
from .version import APP_VERSION, is_newer

# Where releases are published. Overridable from settings.json so a repo move
# does not need a rebuild.
UPDATE_BASE_URL = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main"

# Downloads land here first. It has to sit inside APP_DIR: os.replace cannot
# rename across filesystems, and /tmp is a different one on this device.
STAGING_DIR = os.path.join(APP_DIR, ".update_staging")

# Rieng mot cho, khong dung chung STAGING_DIR: _stage_files() mo dau bang
# rmtree(STAGING_DIR) va apply_update() ket thuc bang dung lenh do, nen 9,6 MB
# vua tai xong se bi xoa sach ngay truoc hoac sau khi cai cac file .py.
CATALOG_STAGING_DIR = os.path.join(APP_DIR, ".catalog_staging")

UA = "RetroHub/%s" % APP_VERSION
TIMEOUT = 20

# Refuse a manifest that is implausibly large or names paths outside the app.
MAX_MANIFEST_BYTES = 512 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024

# Ban nen cua catalogue: 9,6 MB hom nay, de rong ra cho no lon dan. Tran nay
# truyen thang vao _get - MAX_FILE_BYTES chi la mac dinh cua duong "files",
# khong phai gioi han cung cua ham.
MAX_CATALOG_BYTES = 64 * 1024 * 1024
# Bung sat rip the thi lan ghi ke tiep cua may cung chet. Chua lai mot khoang,
# cung con so voi rh/archive.py.
CATALOG_SPACE_MARGIN = 64 * 1024 * 1024
CATALOG_CHUNK = 256 * 1024

# Ly do that bai, la key cua rh.i18n de nguoi goi tu dich.
CATALOG_NO_SPACE = "upd_cat_err_space"
CATALOG_BAD_HASH = "upd_cat_err_hash"
CATALOG_FAILED = "upd_cat_err_failed"
CATALOG_KEYS = frozenset([CATALOG_NO_SPACE, CATALOG_BAD_HASH, CATALOG_FAILED])


class CatalogError(Exception):
    """That bai khi lay kho game, kem mot key dich duoc va so lieu di kem."""

    def __init__(self, key, detail=""):
        super().__init__(f"{key}: {detail}" if detail else key)
        self.key = key
        self.detail = detail


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


def catalog_entry(manifest):
    """Khoa "catalog" cua manifest khi no dung dinh dang, None khi khong.

    Manifest den tu mang nen o day khong tin gi ca: thieu khoa, sai kieu, hash
    cut hay duong dan thoat ra ngoai thu muc app deu tra None. Ban 1.35-1.38
    khong co khoa nay, va do la truong hop binh thuong chu khong phai loi."""
    c = (manifest or {}).get("catalog")
    if not isinstance(c, dict):
        return None
    path = c.get("path")
    url = c.get("url")
    sha256 = c.get("sha256")
    sha256_plain = c.get("sha256_plain")
    if not isinstance(path, str) or not isinstance(url, str) or not isinstance(sha256, str) or not isinstance(sha256_plain, str):
        return None
    if not _safe_rel(path) or not _safe_rel(url):
        return None
    if len(sha256) != 64 or len(sha256_plain) != 64:
        return None
    if not isinstance(c.get("size"), int) or not isinstance(c.get("size_plain"), int):
        return None
    return c


def catalog_pending(manifest):
    """True khi manifest mang catalogue khac thu dang nam tren may.

    So chuoi voi chuoi chu khong doc file: bam lai 33 MB tu the o duong kiem
    tra cap nhat se bien mot thao tac gan nhu tuc thi thanh vai giay."""
    c = catalog_entry(manifest)
    return bool(c) and c["sha256_plain"] != state.catalog_sha


def pending_files(manifest):
    """Files whose on-disk hash differs from the manifest."""
    out = []
    for f in manifest["files"]:
        local = os.path.join(APP_DIR, f["path"])
        if sha256_of(local) != f["sha256"]:
            out.append(f)
    return out


def download_catalog(manifest, free_space=None, on_phase=None):
    """Tai, kiem va giai nen catalogue vao staging. Tra duong dan file da bung.

    Nem CatalogError o moi loi, kem key dich duoc. Hong o bat ky buoc nao thi
    xoa sach staging: mot file .sqlite3 bung do dang con te hon la khong co gi,
    vi lan sau se khong biet no dang do.

    on_phase, khi co, duoc goi dung mot lan ngay truoc khi vong giai nen bat
    dau - tai ve va giai nen deu nam trong ham nay, nen nguoi goi can mot moc
    de doi nhan UI tu "dang tai" sang "dang giai nen" dung luc, thay vi doan
    mo hay ghi nhan sai thu tu that."""
    c = catalog_entry(manifest)
    if not c:
        raise CatalogError(CATALOG_FAILED, "manifest khong co catalogue")
    free_space = free_space or _free_space

    # Don rac mo coi TRUOC khi do cho trong: mot lan chay truoc chet dua, con
    # staging cu con nguyen tren the, thi lan nay se bi do nham thanh thieu
    # cho boi chinh so byte sap duoc giai phong.
    shutil.rmtree(CATALOG_STAGING_DIR, ignore_errors=True)

    # Kiem truoc khi tai. Bung 33 MB ra roi moi bao thieu cho la mat khong ca
    # luot tai cua nguoi dung.
    need = c["size"] + c["size_plain"] + CATALOG_SPACE_MARGIN
    try:
        have = free_space(APP_DIR)
    except OSError as e:
        # os.statvfs nam ngoai moi try/except khac trong ham nay - khong bat
        # o day thi loi tho se thoat thang ra ngoai CatalogError, va nguoi
        # goi (app.py) khong con biet duong nao ma dich sang thong bao cho
        # nguoi dung.
        raise CatalogError(CATALOG_FAILED, str(e)[:40])
    if need > have:
        raise CatalogError(CATALOG_NO_SPACE,
                           "can %s, con %s" % (_human(need), _human(have)))

    # ok chi thanh True ngay truoc return: don sach o finally chay cho MOI
    # duong thoat khong thanh cong, bat ke loi la kieu gi - ke ca mot loi
    # chua ai tung nghi toi (vd zlib.error tu giua luc giai nen). Don theo
    # cau truc nhu vay thi khong con phai doan het cac kieu exception.
    ok = False
    try:
        os.makedirs(CATALOG_STAGING_DIR, exist_ok=True)
        gz_path = os.path.join(CATALOG_STAGING_DIR, "catalog.gz")
        out_path = os.path.join(CATALOG_STAGING_DIR, "catalog.sqlite3")

        # _get nhan tran qua tham so, nen MAX_FILE_BYTES 32 MB chi rang buoc
        # duong "files" chu khong rang buoc ham. 9,6 MB nam gon trong RAM cua
        # may, doi lai khong phai viet rieng mot duong tai theo dong.
        blob = _get("%s/%s" % (base_url(), c["url"]), MAX_CATALOG_BYTES)
        if hashlib.sha256(blob).hexdigest() != c["sha256"]:
            raise CatalogError(CATALOG_BAD_HASH, "ban nen")
        with open(gz_path, "wb") as f:
            f.write(blob)

        if on_phase:
            on_phase()

        h = hashlib.sha256()
        with gzip.open(gz_path, "rb") as src, open(out_path, "wb") as dst:
            while True:
                chunk = src.read(CATALOG_CHUNK)
                if not chunk:
                    break
                dst.write(chunk)
                h.update(chunk)
        if h.hexdigest() != c["sha256_plain"]:
            raise CatalogError(CATALOG_BAD_HASH, "ban bung")

        # Ban nen da het viec; giu lai chi ton cho tren the. Xoa duoc hay
        # khong deu khong doi gi: ca thu muc staging se bi don o buoc cai.
        try:
            os.remove(gz_path)
        except OSError:
            pass
        ok = True
        return out_path
    except CatalogError:
        raise
    except Exception as e:
        # Bat het: mot deflate body hong nem zlib.error, khong phai OSError
        # hay ValueError, va nguoi goi khong duoc thay kieu loi thu vien tho -
        # chi CatalogError voi key dich duoc.
        raise CatalogError(CATALOG_FAILED, str(e)[:40])
    finally:
        if not ok:
            shutil.rmtree(CATALOG_STAGING_DIR, ignore_errors=True)


def apply_catalog(manifest, staged_path):
    """Doi catalogue da kiem sang cho that. True khi xong.

    os.replace doi muc luc thu muc trong mot nhip, nen hong giua chung thi ban
    cu con nguyen chu khong con mot file nua cu nua moi. Dau catalog_sha ghi
    SAU khi doi xong, cung loi nghi voi rh/version.py duoc cai cuoi cung: chet
    giua chung thi lan sau thu lai, chu khong tuong nham la da xong."""
    c = catalog_entry(manifest)
    if not c:
        return False
    dst = os.path.join(APP_DIR, c["path"])
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(staged_path, dst)
    except OSError as e:
        print("Catalog install failed: %s" % e)
        # os.replace hong thi staged_path (33 MB da giai nen) con nguyen
        # trong CATALOG_STAGING_DIR - khong don o day thi no nam lai mai mai,
        # vi khong con dau hieu nao noi la con dang do.
        shutil.rmtree(CATALOG_STAGING_DIR, ignore_errors=True)
        return False

    state.catalog_sha = c["sha256_plain"]
    state.save_settings()
    shutil.rmtree(CATALOG_STAGING_DIR, ignore_errors=True)
    return True


def check_for_update(force=False):
    """(manifest, files) when a newer version is published, else None.

    Versions the user chose to skip are treated as already handled - except
    when *force* is set, which is the case for a check the user asked for by
    hand. Having explicitly gone looking, they should not be told there is
    nothing there because of a skip they made earlier."""
    m = fetch_manifest()
    if not m:
        return None
    # Catalogue di lech mot minh la chuyen thuong: ban .py cai xong roi khoi
    # dong lai thi phien ban da bang nhau, ma kho game thi chua ve. Chi xet
    # phien ban thoi se bo quen no mai mai.
    if not is_newer(m["version"], APP_VERSION) and not catalog_pending(m):
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
            # Binary giai nen cung phai chay duoc, khong chi script. Luat nay
            # chi co tac dung tu ban SAU, vi ban cai lan nay la updater cu -
            # rh.archive.sevenzip() tu bat co thuc thi nen khong phu thuoc no.
            if f["path"].endswith(".sh") or f["path"].startswith("bin/"):
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
