# -*- coding: utf-8 -*-
"""Giai nen .rar/.7z bang 7-Zip. Leaf module - chi dung stdlib.

zipfile cua Python lo duoc 89% nguon trong kho, nhung .rar va .7z thi khong:
RAR3/RAR5 la thuat toan doc quyen, khong co ban giai nen thuan Python nao dung
duoc. Nen phan nay goi ra mot binary 7-Zip static di kem ban cap nhat.

Cac ban scene PSP con long them mot tang - archive ngoai kieu STORE chua mot BO
RAR volume, bo do moi chua ISO - nen giai nen phai lap, khong phai mot buoc."""

import os
import re
import shutil
import subprocess

from .paths import APP_DIR
from .romfiles import (GENERIC_ROM_EXTS, ROM_EXT_PRIORITY, SIDECAR_EXTS,
                       pick_primary_rom)
from .storage import free_space as _free_space, human_bytes as _human

# Ly do that bai, la key cua rh.i18n de nguoi goi tu dich.
NO_TOOL = "dl_err_no_extractor"
NO_SPACE = "dl_err_extract_space"
FAILED = "dl_err_extract_failed"
PATCH_ONLY = "dl_err_patch_only"
ARCHIVE_KEYS = frozenset([NO_TOOL, NO_SPACE, FAILED, PATCH_ONLY])

# Ban va ROM hack: khong phai ROM, va khong phai file hong. Muon choi thi phai
# va len ROM goc, viec ma RetroHub chua lam.
PATCH_EXTS = (".ips", ".bps", ".ups", ".xdelta", ".vcdiff", ".aps")

# Ban scene long nhau hai tang; 3 la du rong ma van chan duoc archive vong lap.
MAX_DEPTH = 3
# Bung sat rip the thi lan ghi ke tiep cua may cung chet. Chua lai mot khoang.
SPACE_MARGIN = 64 * 1024 * 1024

_MAGIC = (b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01", b"7z\xbc\xaf\x27\x1c")
_SNIFF_BYTES = 4096


class ArchiveError(Exception):
    """Giai nen hong, kem san key i18n de man hinh noi dung ly do."""

    def __init__(self, key, detail=""):
        super().__init__(f"{key}: {detail}" if detail else key)
        self.key = key
        self.detail = detail


def sevenzip(app_dir=None):
    """Duong dan mot bo giai nen dung duoc, hoac None.

    Ban di kem app duoc uu tien, nhung co the chua co co thuc thi: file nay do
    updater cua ban CU cai vao, ma updater do chi chmod cho .sh. Tu bat co day,
    dung cach launch.sh lam voi Python runtime."""
    own = os.path.join(app_dir or APP_DIR, "bin", "7zzs")
    if os.path.isfile(own):
        if not os.access(own, os.X_OK):
            try:
                os.chmod(own, os.stat(own).st_mode | 0o111)
            except OSError:
                pass
        if os.access(own, os.X_OK):
            return own
    for name in ("7zz", "7za", "7z"):
        found = shutil.which(name)
        if found:
            return found
    return None


def strip_http_prefix(path):
    """Cat khoi header HTTP dinh o dau file tai ve. True neu co cat.

    Moi file duoi /romhacks/ cua retrostic deu dinh nguyen mot phan hoi HTTP
    ~340 byte truoc phan archive that, tu mot lan mirror hong nam 2020. zipfile
    cua Python bo qua duoc nen kho ROM Hacks van chay, nhung 7-Zip tu choi
    thang: "Cannot open the file as archive". Doi vai byte doc them o day de
    khong mat ca mot kho game."""
    try:
        with open(path, "rb") as f:
            head = f.read(_SNIFF_BYTES)
    except OSError:
        return False
    if not head.startswith(b"HTTP/"):
        return False
    end = head.find(b"\r\n\r\n")
    if end < 0:
        return False

    tmp = path + ".cat-dau"
    try:
        with open(path, "rb") as src, open(tmp, "wb") as dst:
            src.seek(end + 4)
            shutil.copyfileobj(src, dst, 1024 * 1024)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def looks_like_archive(path):
    """File nay co phai .rar/.7z khong - doc dau file chu khong tin cai duoi ten.

    Doc han 4 KB dau vi file duoi /romhacks/ cua retrostic dinh nguyen mot khoi
    header HTTP truoc phan archive that; 7-Zip van mo duoc chung."""
    try:
        with open(path, "rb") as f:
            head = f.read(_SNIFF_BYTES)
    except OSError:
        return False
    return any(m in head for m in _MAGIC)


def _run(args, timeout=None):
    """Chay 7zz, tra (returncode, stdout). Khong bao gio nem ra OSError."""
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        raise ArchiveError(FAILED, str(e)[:60])
    return p.returncode, p.stdout.decode("utf-8", "replace")


def list_entries(archive_path, exe):
    """(tong byte bung ra, [ten file]) doc tu 7zz, da bo thu muc.

    Doc header chu khong bung, nen goi truoc moi tang deu gan nhu mien phi."""
    rc, out = _run([exe, "l", "-slt", archive_path], timeout=120)
    if rc != 0:
        tail = out.strip().splitlines()
        raise ArchiveError(FAILED, tail[-1][:60] if tail else "")

    # Khoi dau tien sau dau "--" la mo ta chinh cai archive (cung co dong
    # "Path = "), danh sach file that chi bat dau sau dong "----------".
    body = out.split("\n----------\n", 1)
    if len(body) < 2:
        return 0, []

    total = 0
    names = []
    path = None
    is_folder = False
    size = 0
    for line in body[1].splitlines() + [""]:
        if line.startswith("Path = "):
            path, is_folder, size = line[7:].strip(), False, 0
        elif line.startswith("Folder = "):
            is_folder = line[9:].strip() == "+"
        elif line.startswith("Size = "):
            try:
                size = int(line[7:].strip() or 0)
            except ValueError:
                size = 0
        elif not line.strip() and path is not None:
            if not is_folder:
                names.append(path)
                total += size
            path = None
    return total, names


_PCT = re.compile(r"(\d{1,3})%")


def extract_to(archive_path, dest_dir, exe, progress=None):
    """Bung *archive_path* vao *dest_dir*, tra ve moi file da bung.

    -bso0 tat danh sach file, -bsp1 day tien trinh ra stdout. 7-Zip ve tien
    trinh bang backspace chu khong xuong dong, nen phai doc theo khoi byte."""
    shutil.rmtree(dest_dir, ignore_errors=True)
    os.makedirs(dest_dir, exist_ok=True)
    args = [exe, "x", archive_path, "-o" + dest_dir, "-y", "-bso0", "-bsp1"]
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except (OSError, subprocess.SubprocessError) as e:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise ArchiveError(FAILED, str(e)[:60])

    last = -1
    tail = ""
    while True:
        chunk = proc.stdout.read(256)
        if not chunk:
            break
        tail = (tail + chunk.decode("utf-8", "replace"))[-256:]
        if progress:
            for token in _PCT.findall(tail):
                pct = int(token)
                if pct != last and 0 <= pct <= 100:
                    last = pct
                    progress(pct)
    rc = proc.wait()
    if rc != 0:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise ArchiveError(FAILED, "7z rc=%d" % rc)

    root = os.path.realpath(dest_dir)
    out = []
    for base, dirs, files in os.walk(dest_dir):
        # Duyet ca dirs: mot symlink tro toi thu muc duoc os.walk xep vao dirs
        # chu khong phai files, nen chi soi files la bo lot dung truong hop
        # nguy hiem nhat.
        for name in dirs:
            full = os.path.realpath(os.path.join(base, name))
            if not full.startswith(root + os.sep):
                shutil.rmtree(dest_dir, ignore_errors=True)
                raise ArchiveError(FAILED, "duong dan thoat ra ngoai")
        for name in files:
            full = os.path.realpath(os.path.join(base, name))
            if not full.startswith(root + os.sep):
                # Bat symlink trong archive tro ra ngoai thu muc dich: lan ghi
                # sau se di theo no ma ghi de len he thong. Duong dan kieu "../"
                # thi chinh 7-Zip da cat truoc khi ghi.
                shutil.rmtree(dest_dir, ignore_errors=True)
                raise ArchiveError(FAILED, "duong dan thoat ra ngoai")
            out.append(full)
    return out


# Thu tu uu tien khi phai chui vao mot tang nua. Ban scene dat ten hai kieu:
# ".rar + .r00 + .r01" va ".001 + .002"; ca hai deu phai bat dau tu volume dau.
_VOLUME_RANK = ((".001", 0), (".part01.rar", 1), (".part1.rar", 1), (".rar", 2),
                (".r00", 3), (".7z", 4), (".zip", 5))


def next_volume(paths):
    """File nao trong dong vua bung ra la archive de chui vao tiep, hoac None."""
    best = None
    for p in sorted(paths):
        low = p.lower()
        if low.endswith(SIDECAR_EXTS):
            continue
        for suffix, rank in _VOLUME_RANK:
            if low.endswith(suffix):
                if best is None or rank < best[0]:
                    best = (rank, p)
                break
    return best[1] if best else None


def unpack_to_rom(archive_path, rom_dir, sys_code, exe=None, work_dir=None,
                  progress=None, free_space=None, prefer_name=None):
    """Bung *archive_path* cho toi khi ra ROM, tra ve duong dan ROM trong rom_dir.

    Lap tung tang chu khong doan truoc ca chuoi: chi sau khi bung xong vo ngoai
    moi biet ISO ben trong nang bao nhieu.

    *prefer_name* la ten (khong duoi) ma kho game da hien cho nguoi dung. Ban
    scene dat ten file kieu "a-nfsmwu.iso"; giu nguyen thi trong launcher game
    hien la "a-nfsmwu" va nguoi dung mo thu muc ra khong nhan ra game vua tai.
    Chi doi ten khi archive nha ra dung mot file: doi ten mot .cue se lam no
    tro nham ten .bin ghi ben trong."""
    if not exe:
        raise ArchiveError(NO_TOOL)
    free_space = free_space or _free_space
    work_dir = work_dir or (archive_path + ".giai-nen")

    current = archive_path
    try:
        for depth in range(MAX_DEPTH):
            need, _ = list_entries(current, exe)
            have = free_space(os.path.dirname(rom_dir) or ".")
            if need + SPACE_MARGIN > have:
                raise ArchiveError(NO_SPACE, "can %s, con %s" % (_human(need), _human(have)))

            stage = os.path.join(work_dir, "tang%d" % depth)
            files = extract_to(current, stage, exe, progress=progress)

            # Chi nhan file co duoi that su la ROM. pick_primary_rom xep duoi la
            # o hang tren sidecar, nen tha ca dong vao no thi mot volume
            # "a-nfsmwu.001" se duoc cham la ROM va vong lap dung ngay o tang 1,
            # chep dung mot manh 20 MB vao Roms/.
            known = set(ROM_EXT_PRIORITY.get(sys_code, [])) | set(GENERIC_ROM_EXTS)
            rom = pick_primary_rom(
                [f for f in files if os.path.splitext(f)[1].lower() in known], sys_code)
            if rom:
                # Chuyen ca file di kem trong cung tang: mot .cue khong co .bin
                # ben canh la mot file tro vao khoang khong, ma cay tam thi bi
                # xoa ngay sau day.
                companions = [f for f in files
                              if f != rom and not f.lower().endswith(SIDECAR_EXTS)]
                dest = None
                for src in [rom] + companions:
                    name = os.path.basename(src)
                    if src == rom and prefer_name and not companions:
                        name = prefer_name + os.path.splitext(src)[1].lower()
                    target = os.path.join(rom_dir, name)
                    os.replace(src, target)
                    if src == rom:
                        dest = target
                return dest

            nxt = next_volume(files)
            if not nxt:
                if any(f.lower().endswith(PATCH_EXTS) for f in files):
                    raise ArchiveError(PATCH_ONLY)
                raise ArchiveError(FAILED, "khong tim thay ROM trong archive")
            current = nxt
        raise ArchiveError(FAILED, "long qua %d tang" % MAX_DEPTH)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
