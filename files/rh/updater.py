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
import time
import urllib.error
import urllib.parse
import urllib.request

from . import state
from .paths import APP_DIR, SDCARD_PATH
from .storage import free_space as _free_space, human_bytes as _human
from .version import APP_VERSION, is_newer

# Where releases are published. Overridable from settings.json so a repo move
# does not need a rebuild.
UPDATE_BASE_URL = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main"
CDN_BASE_URL = "https://cdn.jsdelivr.net/gh/nguyenxuanhoa493/repohubtool@main"
GHPROXY_BASE_URL = "https://ghproxy.net/" + UPDATE_BASE_URL

# Nhung dinh dang jsDelivr chan (HTTP 403 Forbidden) thi bo qua khong goi CDN
CDN_EXCLUDED_EXTS = (".jar", ".zip", ".exe")

# Downloads land here first. It has to sit inside APP_DIR: os.replace cannot
# rename across filesystems, and /tmp is a different one on this device.
STAGING_DIR = os.path.join(APP_DIR, ".update_staging")

# Rieng mot cho, khong dung chung STAGING_DIR: _stage_files() mo dau bang
# rmtree(STAGING_DIR) va apply_update() ket thuc bang dung lenh do, nen 9,6 MB
# vua tai xong se bi xoa sach ngay truoc hoac sau khi cai cac file .py.
CATALOG_STAGING_DIR = os.path.join(APP_DIR, ".catalog_staging")

UA = "RetroHub/%s" % APP_VERSION
TIMEOUT = 15

# Refuse a manifest that is implausibly large or names paths outside the app.
MAX_MANIFEST_BYTES = 512 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024

# Ban nen cua catalogue: 9,6 MB hom nay, de rong ra cho no lon dan. Tran nay
# truyen thang vao _get - MAX_FILE_BYTES chi la mac dinh cua duong "files",
# khong phai gioi han cung cua ham.
MAX_CATALOG_BYTES = 64 * 1024 * 1024
# Dinh that su khi cap nhat kho game: .gz va .sqlite3 cung nam trong staging mot
# luc (39,6 MB voi ban hom nay). Truong 64 MB cu doi 101,8 MB trong, nen the con
# ~90 MB bao thieu cho du chi can them ~40 MB - va popup cu the ma hoi mai.
# 16 MB du de bu cho FAT/exFAT va cho mot ROM dang tai do dang.
CATALOG_SPACE_MARGIN = 16 * 1024 * 1024
CATALOG_CHUNK = 256 * 1024

# Ly do that bai, la key cua rh.i18n de nguoi goi tu dich.
CATALOG_NO_SPACE = "upd_cat_err_space"
CATALOG_BAD_HASH = "upd_cat_err_hash"
CATALOG_FAILED = "upd_cat_err_failed"
CATALOG_KEYS = frozenset([CATALOG_NO_SPACE, CATALOG_BAD_HASH, CATALOG_FAILED])

# Bo gia lap Java. Ca thu muc runtime nang 66 MB va gan het la ban JRE - thu
# chua bao gio doi - nen duong cap nhat chi mang nhung tep that su co the doi
# giua hai ban: tep .jar, tep nhi phan SDL va may tep cau hinh. Bang liet ke do
# nam trong manifest; goc thi chot cung o day chu khong lay tu manifest, vi
# manifest den tu mang va khong duoc phep chi ung dung ghi vao dau.
RUNTIME_ROOT = os.path.join(SDCARD_PATH, "Emus", "JAVA")
RUNTIME_STAGING_DIR = os.path.join(RUNTIME_ROOT, ".rh_runtime_staging")
# Tep can quyen chay sau khi thay. Thu muc goc nam tren the FAT/exFAT nen chmod
# co the bi tu choi - do khong phai ly do de coi ban cai la that bai.
RUNTIME_EXECUTABLE = ("zulu17/bin/sdl_interface", "zulu17/bin/java", "launch.sh")
MAX_RUNTIME_BYTES = 24 * 1024 * 1024

RUNTIME_NO_SPACE = "upd_rt_err_space"
RUNTIME_BAD_HASH = "upd_rt_err_hash"
RUNTIME_FAILED = "upd_rt_err_failed"
RUNTIME_KEYS = frozenset([RUNTIME_NO_SPACE, RUNTIME_BAD_HASH, RUNTIME_FAILED])

# Dai tien do cua modal cap nhat, mot cho duy nhat. Cac dai phai noi tiep nhau
# va di len: tai file -> cai -> bo gia lap -> chuan bi gia lap -> kho game. Ban
# cu chia moc o ba cho khac nhau (0.95 / 0.92 / 0.96) nen thanh tien do nhay
# nguoc va nguoi dung doc ra "ket o 95%" trong khi van dang tai 8 MB + bung 31 MB.
PROGRESS_WINDOWS = {
    "files": (0.00, 0.85),
    "install": (0.86, 0.86),
    "runtime": (0.86, 0.90),
    "catalog": (0.90, 0.96),
    "unpack": (0.96, 1.00),
    "catalog_only": (0.00, 0.45),
    "catalog_only_unpack": (0.45, 0.95),
}


def phase_pct(name, fraction=0.0, cat_only=False):
    """Phan tram hien thi (0.0-1.0) cua mot pha trong modal cap nhat.

    cat_only: may chi thieu kho game, nen kho game duoc dung ca dai tien do."""
    windows = PROGRESS_WINDOWS
    if cat_only and name == "catalog":
        name = "catalog_only"
    elif cat_only and name == "unpack":
        name = "catalog_only_unpack"
    lo, hi = windows.get(name, (0.0, 0.0))
    return lo + (hi - lo) * min(1.0, max(0.0, fraction or 0.0))


class CatalogError(Exception):
    """That bai khi lay kho game, kem mot key dich duoc va so lieu di kem."""

    def __init__(self, key, detail=""):
        super().__init__(f"{key}: {detail}" if detail else key)
        self.key = key
        self.detail = detail


class UpdateCancelled(Exception):
    """Nguoi dung bam B giua luc tai. Khong phai loi, khong duoc bao that bai.

    Chi nem ra tu cac ham TAI (download_*) - khong bao gio tu apply_*, vi nua
    chung thi ban cai dang do: apply_update doi tung file mot.
    """


def base_url():
    return (getattr(state, "update_url", "") or UPDATE_BASE_URL).rstrip("/")


def candidate_base_urls(rel_path=""):
    """Danh sach base URL de thu theo thu tu uu tien (jsDelivr CDN -> ghproxy -> GitHub Raw).

    Voi manifest.json va cac file metadata json, luon uu tien lay truc tiep tu GHProxy & GitHub Raw
    de tranh bi tinh trang CDN cache cu khien khong nhan dien duoc ban cap nhat moi nhat.
    """
    custom = (getattr(state, "update_url", "") or "").rstrip("/")
    if custom:
        candidates = []
        if "raw.githubusercontent.com" in custom:
            candidates.append(custom)
            candidates.append("https://ghproxy.net/" + custom)
            if not rel_path.lower().endswith(CDN_EXCLUDED_EXTS) and "manifest" not in rel_path.lower():
                parts = custom.replace("https://raw.githubusercontent.com/", "").strip("/").split("/", 2)
                if len(parts) == 3:
                    candidates.append("https://cdn.jsdelivr.net/gh/%s/%s@%s" % (parts[0], parts[1], parts[2]))
        else:
            candidates.append(custom)
        return candidates

    candidates = []
    # Uu tien GHProxy va GitHub Raw cho manifest.json de lay thong tin cap nhat real-time
    if rel_path.lower().endswith(CDN_EXCLUDED_EXTS) or "manifest" in rel_path.lower() or rel_path.lower().endswith(".json"):
        candidates.append(GHPROXY_BASE_URL)
        candidates.append(UPDATE_BASE_URL)
    else:
        candidates.append(CDN_BASE_URL)
        candidates.append(GHPROXY_BASE_URL)
        candidates.append(UPDATE_BASE_URL)
    return candidates


def _get(url, max_bytes, timeout=TIMEOUT, progress=None):
    headers = {
        "User-Agent": UA,
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }
    req = urllib.request.Request(url, headers=headers)
    kwargs = {"timeout": timeout}
    try:
        ctx = ssl._create_unverified_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if url.startswith("https://"):
            kwargs["context"] = ctx
    except Exception:
        pass

    with urllib.request.urlopen(req, **kwargs) as resp:
        content_length = resp.headers.get("Content-Length")
        total_size = int(content_length) if (content_length and content_length.isdigit()) else 0
        buf = bytearray()
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > max_bytes:
                raise ValueError("response larger than %d bytes" % max_bytes)
            if progress and total_size > 0:
                progress(len(buf), total_size)
    return bytes(buf)


def _fetch_blob(rel_path, max_bytes, expected_sha=None, progress=None):
    """Tai du lieu tu cac candidate base URL (GHProxy, GitHub Raw, CDN mirror).

    Kiem tra ma bam sha256 neu duoc cung cap. Tu dong them anti-cache query
    de tranh bi Fastly / CDN cache giu trang 404 hoac file cu.

    Hash lech thi doi mirror ngay, khong thu lai chinh URL do: lech hash nghia
    la CDN dang giu ban cu (jsDelivr cache theo nhanh @main, query _t khong
    xuyen qua duoc cache), thu lai chi ton them mot lan tai nguyen file - voi
    kho game la 8,3 MB moi lan vo ich.
    """
    last_err = None
    quoted_rel_path = urllib.parse.quote(rel_path, safe="/:")
    for base in candidate_base_urls(rel_path):
        url = "%s/%s" % (base, quoted_rel_path)
        for attempt in range(2):
            try:
                # Luon gui kem query timestamp de bypass cache cua proxy/CDN
                sep = "&" if "?" in url else "?"
                fetch_url = "%s%s_t=%d" % (url, sep, int(time.time()))
                data = _get(fetch_url, max_bytes, progress=progress)
            except Exception as e:
                # Loi mang (timeout, 404, proxy chan...) moi dang thu lai.
                last_err = e
                time.sleep(0.3)
                continue
            if not expected_sha or hashlib.sha256(data).hexdigest() == expected_sha:
                return data
            # Mirror tra sai bytes (CDN con giu ban cu): doi mirror ngay.
            last_err = ValueError("hash mismatch for %s" % rel_path)
            break
    raise last_err or RuntimeError("fetch failed for %s" % rel_path)


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
    m = None
    for base in candidate_base_urls("manifest.json"):
        try:
            manifest_url = "%s/manifest.json?_t=%d" % (base, int(time.time()))
            raw = _get(manifest_url, MAX_MANIFEST_BYTES)
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict) and parsed.get("version") and isinstance(parsed.get("files"), list):
                valid = True
                for f in parsed["files"]:
                    if not isinstance(f, dict) or not _safe_rel(f.get("path", "")) or len(f.get("sha256", "")) != 64:
                        valid = False
                        break
                if valid:
                    m = parsed
                    break
        except (urllib.error.URLError, OSError, ValueError, UnicodeDecodeError) as e:
            print("Update check failed from %s: %s" % (base, e))
            continue

    if not m:
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


def catalog_pending(manifest, force=False):
    """True khi manifest mang catalogue khac thu dang nam tren may.

    So chuoi voi chuoi chu khong doc file: bam lai 33 MB tu the o duong kiem
    tra cap nhat se bien mot thao tac gan nhu tuc thi thanh vai giay.

    Cung khong the bam lai file de so hash: chinh app ghi vao DB nay
    (db.py UPDATE game_sources.is_alive / file_size_str), nen file tren may
    khong bao gio con khop sha cua ban phat hanh nua - do la ly do that su cua
    popup "cap nhat kho game" lap mai.

    Ngoai le duy nhat: may cai tu file zip co san kho game nhung settings.json
    khong duoc phat hanh nen khong co dau vet nao. Lan dau gap, neu file DB da
    lon hon hoac bang ban phat hanh thi coi kho dang co la ban dang dung va ghi
    lai dau (sqlite chi lon dan khi bi ghi them, khong tu nho lai). Kiem tra cap
    nhat bang tay (force) bo qua buoc nay, de nguoi dung van ep tai lai kho duoc."""
    c = catalog_entry(manifest)
    if not c:
        return False
    known = state.catalog_sha
    if not known and not force:
        try:
            local_size = os.path.getsize(os.path.join(APP_DIR, c["path"]))
        except OSError:
            local_size = -1
        if local_size >= c["size_plain"]:
            known = c["sha256_plain"]
            state.catalog_sha = known
            state.save_settings()
    if c["sha256_plain"] == known:
        return False
    return c["sha256_plain"] != state.skipped_catalog_sha


class RuntimeUpdateError(Exception):
    """That bai khi lay bo gia lap, kem mot key dich duoc va so lieu di kem."""

    def __init__(self, key, detail=""):
        super().__init__(f"{key}: {detail}" if detail else key)
        self.key = key
        self.detail = detail


def runtime_entry(manifest):
    """Khoa "runtime" cua manifest khi no dung dinh dang, None khi khong.

    Manifest den tu mang nen khong tin gi ca. Ban truoc 1.46 khong co khoa nay
    va do la truong hop binh thuong chu khong phai loi.
    """
    r = (manifest or {}).get("runtime")
    if not isinstance(r, dict):
        return None
    files = r.get("files")
    if not isinstance(files, list) or not files:
        return None
    for f in files:
        if not isinstance(f, dict):
            return None
        path, url, sha = f.get("path"), f.get("url"), f.get("sha256")
        if not isinstance(path, str) or not isinstance(url, str) or not isinstance(sha, str):
            return None
        if not _safe_rel(path) or not _safe_rel(url):
            return None
        if len(sha) != 64 or not isinstance(f.get("size"), int):
            return None
        if f["size"] < 0 or f["size"] > MAX_RUNTIME_BYTES:
            return None
    return r


def runtime_pending(manifest):
    """Tep cua bo gia lap khac voi thu dang nam tren the.

    Rong khi chua cai gia lap: luc do khong co gi de nang cap, ban cai day du
    moi la duong dung. Cung rong khi manifest khong mang khoa runtime.
    """
    r = runtime_entry(manifest)
    if not r:
        return []
    sig = runtime_sig(r)
    if sig and sig == state.skipped_runtime_sig:
        return []
    # Chua co gia lap thi khong tu dung tao ra mot cai nua tep.
    if not os.path.exists(os.path.join(RUNTIME_ROOT, "zulu17", "bin", "java")):
        return []
    out = []
    for f in r["files"]:
        target_path = os.path.join(RUNTIME_ROOT, f["path"])
        if not os.path.exists(target_path) or sha256_of(target_path) != f["sha256"]:
            out.append(f)
    return out


def runtime_sig(runtime):
    """Dau van tay cua danh sach bo gia lap: sha256 cua "path=sha256" tung dong.

    Chi doc manifest chu khong doc file tren the, nen dung duoc o duong kiem tra
    cap nhat (xem runtime_pending)."""
    if not isinstance(runtime, dict) or not isinstance(runtime.get("files"), list):
        return ""
    h = hashlib.sha256()
    for f in sorted(runtime["files"], key=lambda x: str(x.get("path", ""))):
        h.update(("%s=%s\n" % (f.get("path", ""), f.get("sha256", ""))).encode("utf-8"))
    return h.hexdigest()


def download_runtime(pending, progress=None, cancel=None):
    """Tai va kiem tung tep vao staging. Tra duong dan thu muc staging.

    Nem RuntimeUpdateError o moi loi, va don sach staging - mot ban tai do
    dang de lai chi lam lan sau kho doan hon.
    """
    total = sum(f["size"] for f in pending)
    try:
        free = _free_space(RUNTIME_ROOT)
    except OSError:
        free = None
    if free is not None and free < total * 2:
        raise RuntimeUpdateError(
            RUNTIME_NO_SPACE, "can %s, con %s" % (_human(total * 2), _human(free)))

    shutil.rmtree(RUNTIME_STAGING_DIR, ignore_errors=True)
    try:
        os.makedirs(RUNTIME_STAGING_DIR, exist_ok=True)
        for i, f in enumerate(pending, 1):
            if cancel and cancel():
                raise UpdateCancelled()
            if progress:
                progress(i, len(pending), f["path"])
            try:
                blob = _fetch_blob(f["url"], MAX_RUNTIME_BYTES, expected_sha=f["sha256"])
            except ValueError:
                raise RuntimeUpdateError(RUNTIME_BAD_HASH, f["path"])
            except Exception as e:
                raise RuntimeUpdateError(RUNTIME_FAILED, "%s: %s" % (f["path"], e))
            dst = os.path.join(RUNTIME_STAGING_DIR, f["path"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as out:
                out.write(blob)
    except RuntimeUpdateError:
        shutil.rmtree(RUNTIME_STAGING_DIR, ignore_errors=True)
        raise
    except UpdateCancelled:
        shutil.rmtree(RUNTIME_STAGING_DIR, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(RUNTIME_STAGING_DIR, ignore_errors=True)
        raise RuntimeUpdateError(RUNTIME_FAILED, str(e))
    return RUNTIME_STAGING_DIR


def apply_runtime(pending):
    """Doi cac tep da kiem sang cho that. True khi xong.

    Chi chay sau khi tat ca da tai va kiem xong, nen khong co canh nua cu nua
    moi. Sau buoc nay, phep so kich thuoc trong rh.j2me se thay runtime da
    khop voi payload va thoi bao la ban cu.
    """
    try:
        for f in pending:
            src = os.path.join(RUNTIME_STAGING_DIR, f["path"])
            dst = os.path.join(RUNTIME_ROOT, f["path"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)
            if f["path"] in RUNTIME_EXECUTABLE:
                try:
                    os.chmod(dst, 0o755)
                except OSError:
                    pass
    except OSError as e:
        print("Runtime update failed: %s" % e)
        return False
    finally:
        shutil.rmtree(RUNTIME_STAGING_DIR, ignore_errors=True)
    return True


def pending_files(manifest):
    """Files whose on-disk hash differs from the manifest.

    settings.json la state cua may (device_id, catalog_sha, skipped_versions) va
    apply_update() co y khong ghi de no, nen neu dem vao day thi lan nao cung con
    "1 file can tai" va modal cap nhat lap lai mai."""
    out = []
    for f in manifest["files"]:
        if f["path"] == "settings.json":
            continue
        local = os.path.join(APP_DIR, f["path"])
        if sha256_of(local) != f["sha256"]:
            out.append(f)
    return out


def download_catalog(manifest, free_space=None, on_phase=None, progress=None, cancel=None):
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

        def dl_prog(cur, tot):
            if cancel and cancel():
                raise UpdateCancelled()
            if progress:
                progress(cur, tot, "catalog.gz")

        try:
            blob = _fetch_blob(c["url"], MAX_CATALOG_BYTES, expected_sha=c["sha256"], progress=dl_prog)
        except ValueError:
            raise CatalogError(CATALOG_BAD_HASH, "ban nen")
        except UpdateCancelled:
            raise
        except Exception as e:
            raise CatalogError(CATALOG_FAILED, str(e)[:40])
        with open(gz_path, "wb") as f:
            f.write(blob)

        if on_phase:
            on_phase()

        h = hashlib.sha256()
        total_plain = c.get("size_plain", 0)
        unpacked_bytes = 0
        with gzip.open(gz_path, "rb") as src, open(out_path, "wb") as dst:
            while True:
                if cancel and cancel():
                    raise UpdateCancelled()
                chunk = src.read(CATALOG_CHUNK)
                if not chunk:
                    break
                dst.write(chunk)
                h.update(chunk)
                unpacked_bytes += len(chunk)
                if progress and total_plain > 0:
                    progress(unpacked_bytes, total_plain, "roms_store.sqlite3")
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
    except UpdateCancelled:
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
    version_newer = is_newer(m["version"], APP_VERSION)
    cat_pending = bool(catalog_pending(m, force=force))
    rt_pending = bool(runtime_pending(m))
    if not version_newer and not cat_pending and not rt_pending:
        return None
    # skipped_versions nham vao BAN CAP NHAT PHIEN BAN. Kho game va bo chay van
    # phai ve du nguoi dung da bo qua ban do: bo qua 2.38 khong co nghia la mai
    # mai khong co kho game, ma may cai tu file zip thi kho game chi den duoc
    # bang duong nay.
    if not force and version_newer and m["version"] in (state.skipped_versions or []):
        return None
    files = pending_files(m)
    if version_newer and not files and not cat_pending and not rt_pending:
        # Tep tren dia da dung ban moi, chi con tien trinh dang chay la code cu:
        # vua cap nhat xong ma chua khoi dong lai, hoac nguoi dung chep tay code
        # moi len may. Truoc day truong hop nay van mo popup "So tep can tai: 0"
        # - trong nhu loi, bam vao khong thay doi gi, va lan mo app sau lai hoi
        # tiep. Ghi nho de lan khoi dong ke tiep bao "da cap nhat" roi thoi hoi
        # (rh/env.py doc state.pending_update luc mo app).
        state.pending_update = m["version"]
        state.save_settings()
        return None
    return m, files


def download_update(manifest, files, progress=None, cancel=None):
    """Fetch every pending file into staging and verify it. True on success.

    A failed attempt takes its half-written staging tree with it, so nothing
    partial is left sitting inside the app directory. Bam B giua luc tai thi
    nem UpdateCancelled, staging cung duoc don."""
    try:
        ok = _stage_files(manifest, files, progress, cancel)
    except UpdateCancelled:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        raise
    if not ok:
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
    return ok


def _stage_files(manifest, files, progress=None, cancel=None):
    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    try:
        os.makedirs(STAGING_DIR, exist_ok=True)
    except OSError as e:
        print("Update staging failed: %s" % e)
        return False

    total = len(files)
    for i, f in enumerate(files):
        if cancel and cancel():
            raise UpdateCancelled()
        if progress:
            progress(i, total, f["path"])
        rel_path = "files/%s" % f["path"]
        try:
            data = _fetch_blob(rel_path, MAX_FILE_BYTES, expected_sha=f["sha256"])
        except ValueError:
            print("Update hash mismatch for %s" % f["path"])
            return False
        except Exception as e:
            print("Update download failed for %s: %s" % (f["path"], e))
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
        # Khong ghi de settings.json neu da ton tai tren may de bao toan cau hinh nguoi dung
        if f["path"] == "settings.json" and os.path.exists(dst):
            try:
                os.remove(src)
            except OSError:
                pass
            continue
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

    # Dung daemon cu de lan khoi dong ke tiep nap code va hieu ung moi
    try:
        from . import ledctl
        if ledctl.is_running():
            ledctl.stop()
    except Exception:
        pass

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


def skip_version(manifest):
    """Nguoi dung chon "Bo qua": dung hoi lai ve dung thu dang co.

    Bo qua mot phien ban app khong co nghia la bo qua luon kho game: lan sau kho
    doi (sha khac) thi van phai hoi, vi may cai tu file zip chi co duong nay de
    lay catalogue. Vi vay nho ca sha cua kho va dau van tay cua bo gia lap dang
    bi tu choi, chu khong chi nho so phien ban - neu khong, may dang o ban moi
    nhat bam Bo qua xong popup van quay lai mai.
    """
    version = manifest.get("version") if isinstance(manifest, dict) else manifest
    if version and version not in state.skipped_versions:
        state.skipped_versions.append(version)
    if isinstance(manifest, dict):
        c = catalog_entry(manifest)
        if c:
            state.skipped_catalog_sha = c["sha256_plain"]
        sig = runtime_sig(manifest.get("runtime"))
        if sig:
            state.skipped_runtime_sig = sig
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
