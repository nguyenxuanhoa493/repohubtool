#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit luong OTA (headless, offline, khong SDL).

    python _src/selftest_ota_audit.py

Moi check mo ta HANH VI DUNG cua luong cap nhat. Check FAIL = bug dang co.
Day la bo check da lam FAIL 7 lan truoc khi sua (2.41); sau khi sua phai PASS het.
"""

import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import ast
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")
RH = os.path.join(FILES, "rh")
MODAL = os.path.join(RH, "modals", "update.py")
JAVA_LAUNCH = os.path.join(FILES, "emus", "JAVA", "launch.sh")

SD = tempfile.mkdtemp(prefix="rh-ota-audit-")
os.environ["SDCARD_PATH"] = SD
sys.path.insert(0, FILES)
sys.modules.setdefault("db", None)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from rh import updater as up  # noqa: E402
from rh import state  # noqa: E402
from rh.version import APP_VERSION  # noqa: E402

FAILED = []
# Khong duoc ghi vao settings.json cua chinh repo nay khi chay audit.
state.SETTINGS_FILE = os.path.join(SD, "settings.json")

# Nap thang rh/modals/update.py, khong di qua rh.modals/__init__.py: goi __init__
# keo theo game_action -> ui/boxart -> sdl2, ma may build khong co SDL2.
import importlib.util
import types

_MODALS = os.path.join(FILES, "rh", "modals")
_pkg = types.ModuleType("rh.modals")
_pkg.__path__ = [_MODALS]
sys.modules["rh.modals"] = _pkg
_spec = importlib.util.spec_from_file_location("rh.modals.update", os.path.join(_MODALS, "update.py"))
um = importlib.util.module_from_spec(_spec)
sys.modules["rh.modals.update"] = um
_spec.loader.exec_module(um)


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  <- " + detail) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def catalog_manifest(sha_plain="b" * 64, size=8, size_plain=32):
    return {"version": APP_VERSION, "files": [],
            "catalog": {"path": "catalog/roms_store.sqlite3",
                        "url": "catalog/roms_store.sqlite3.gz",
                        "sha256": "a" * 64, "sha256_plain": sha_plain,
                        "size": size, "size_plain": size_plain}}


real_manifest = json.load(io.open(os.path.join(ROOT, "manifest.json"), encoding="utf-8"))

# Kho game ma may cai tu file zip da co san (gitignore: khong phai nguon).
db_path = os.path.join(FILES, "catalog", "roms_store.sqlite3")
made_db = not os.path.exists(db_path)
if made_db:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(db_path, "wb") as f:
        f.write(b"sqlite" * 1024)
db_size = os.path.getsize(db_path)
db_sha = sha256(open(db_path, "rb").read())

orig_fetch = up.fetch_manifest
orig_state = (state.catalog_sha, state.skipped_catalog_sha, state.skipped_runtime_sig,
              list(state.skipped_versions))
try:
    print("A. May da co kho game (cai tu file zip) khong bi moi cap nhat lai")
    up.fetch_manifest = lambda: dict(catalog_manifest(sha_plain="e" * 64, size_plain=32))
    state.catalog_sha = ""
    state.skipped_versions = []
    found = up.check_for_update(force=False)
    check("A1. kho game tren may dung ban phat hanh -> khong hien popup",
          found is None,
          "van moi cap nhat (files=%d)" % (len(found[1]) if found else 0))
    check("A2. da ghi lai dau kho dang dung (khong bam lai file: app ghi vao DB)",
          state.catalog_sha == "e" * 64, "state.catalog_sha=%r" % state.catalog_sha)
    # DB nho hon ban phat hanh => kho tren may la ban cu, phai hoi.
    up.fetch_manifest = lambda: dict(catalog_manifest(sha_plain="f" * 64, size_plain=db_size + 1))
    state.catalog_sha = ""
    check("A3. kho tren may nho hon ban phat hanh -> van phai hoi",
          up.check_for_update(force=False) is not None)
    check("A4. kiem tra cap nhat bang tay (force) van ep duoc tai lai kho",
          up.check_for_update(force=True) is not None
          or up.catalog_pending(dict(catalog_manifest(sha_plain="f" * 64, size_plain=db_size + 1)), force=True))

    print("B. Nut 'Bo qua' phai tat duoc loi moi")
    state.catalog_sha = db_sha
    state.skipped_catalog_sha = ""
    up.fetch_manifest = lambda: dict(catalog_manifest(sha_plain="c" * 64))
    check("B1. co kho game MOI thi van phai hoi", up.check_for_update(force=False) is not None)
    up.skip_version(dict(catalog_manifest(sha_plain="c" * 64)))
    check("B2. bam 'Bo qua' xong khong hoi lai nua", up.check_for_update(force=False) is None)
    up.fetch_manifest = lambda: dict(catalog_manifest(sha_plain="d" * 64))
    check("B3. kho game moi hon nua thi hoi lai (bo qua khong tat vinh vien)",
          up.check_for_update(force=False) is not None)

    java = os.path.join(SD, "Emus", "JAVA", "zulu17", "bin")
    os.makedirs(java, exist_ok=True)
    with open(os.path.join(java, "java"), "w") as f:
        f.write("x")
    man_rt = {"version": APP_VERSION, "files": [], "runtime": dict(real_manifest["runtime"])}
    up.fetch_manifest = lambda: dict(man_rt)
    check("B4. bo gia lap lech thi phai hoi", up.check_for_update(force=False) is not None)
    up.skip_version(dict(man_rt))
    check("B5. bam 'Bo qua' xong khong hoi lai ve bo gia lap do",
          up.check_for_update(force=False) is None)
finally:
    up.fetch_manifest = orig_fetch
    (state.catalog_sha, state.skipped_catalog_sha, state.skipped_runtime_sig,
     state.skipped_versions) = orig_state


print("C. Loi cap nhat phai hien duoc cho nguoi dung")
readers = []
for dirpath, _dirs, names in os.walk(FILES):
    if "__pycache__" in dirpath:
        continue
    for n in names:
        if not n.endswith(".py"):
            continue
        path = os.path.join(dirpath, n)
        if os.path.normpath(path) in (os.path.normpath(os.path.join(RH, "state.py")),
                                      os.path.normpath(MODAL)):
            continue
        text = io.open(path, encoding="utf-8", errors="ignore").read()
        if "pending_catalog_notice" in text:
            readers.append(os.path.relpath(path, ROOT))
check("C1. co man hinh doc pending_catalog_notice de bao nguoi dung",
      readers != [], "khong noi nao doc; loi bi nuot im lang")

from rh import env as envmod  # noqa: E402

state.pending_catalog_notice = ""
state.pending_update = "9.99"
first = envmod.pop_startup_notice()
second = envmod.pop_startup_notice()
check("C2. ban vua cap nhat xong duoc bao cho nguoi dung mot lan",
      bool(first) and "9.99" in str(first), "tra ve: %r" % (first,))
check("C3. thong bao do khong lap lai o lan mo app sau", second is None, repr(second))


print("D. Tai lai file khi hash lech")
calls = {"n": 0}
orig_get = up._get
try:
    up._get = lambda url, max_bytes, timeout=15, progress=None: (calls.__setitem__("n", calls["n"] + 1), b"x" * 4096)[1]
    try:
        up._fetch_blob("files/rh/version.py", 1024 * 1024, expected_sha="0" * 64)
    except Exception:
        pass
    mirrors = len(up.candidate_base_urls("files/rh/version.py"))
    check("D1. mirror tra sai hash chi bi goi mot lan roi sang mirror ke tiep",
          calls["n"] <= mirrors,
          "da goi %d lan cho %d mirror (tai lai ca file tren cung mot URL)" % (calls["n"], mirrors))
finally:
    up._get = orig_get


print("E. Do cho trong cho kho game")
plain = b"p" * 40000
gz = gzip.compress(plain)
real_cat = real_manifest.get("catalog") or {}
man2 = catalog_manifest(size=real_cat.get("size", 8), size_plain=real_cat.get("size_plain", 32),
                        sha_plain=sha256(plain))
orig_blob = up._fetch_blob
orig_staging = up.CATALOG_STAGING_DIR
try:
    up._fetch_blob = lambda rel, mx, expected_sha=None, progress=None: gz
    up.CATALOG_STAGING_DIR = os.path.join(SD, ".catalog_staging")
    try:
        staged = up.download_catalog(man2, free_space=lambda p: 90 * 1024 * 1024)
        ok, err = bool(staged) and os.path.exists(staged), ""
    except up.CatalogError as e:
        ok, err = False, str(e)
    peak = man2["catalog"]["size"] + man2["catalog"]["size_plain"]
    check("E1. con 90MB trong -> cap nhat duoc kho game",
          ok, "%s (dinh that su %s MB + %s MB du phong)"
              % (err, round(peak / 1024.0 / 1024.0, 1), round(up.CATALOG_SPACE_MARGIN / 1024.0 / 1024.0, 1)))
finally:
    up._fetch_blob = orig_blob
    up.CATALOG_STAGING_DIR = orig_staging


print("F. Tien do hien thi va huy giua luc tai")
order = ["files", "install", "runtime", "catalog", "unpack"]
ends = [up.phase_pct(n, 1.0) for n in order]
check("F1. cac pha tien do noi tiep nhau, khong pha nao quay lui",
      ends == sorted(ends) and ends[-1] <= 1.0, "cac moc: %s" % ends)
check("F2. chi kho game thi dung ca dai tien do",
      up.phase_pct("unpack", 1.0, True) <= 1.0
      and up.phase_pct("catalog", 1.0, True) <= up.phase_pct("unpack", 1.0, True),
      "%s / %s" % (up.phase_pct("catalog", 1.0, True), up.phase_pct("unpack", 1.0, True)))
src = io.open(MODAL, encoding="utf-8").read()
check("F3. modal dung bang pha chung va khong de tien do tut lai",
      "phase_pct(" in src and "def _pct(" in src, "magic number roi rac trong modal")
files = [{"path": "rh/version.py", "sha256": "0" * 64, "size": 1}]
cancelled = False
try:
    up.download_update({"version": APP_VERSION, "files": files}, files, cancel=lambda: True)
except up.UpdateCancelled:
    cancelled = True
check("F4. bam B giua luc tai thi dung ngay, khong tai tiep", cancelled)
body = src.split("def handle_input", 1)[1][:2500]
check("F5. handle_input nghe duoc nut B khi dang tai",
      'btn_b' in body and "cancel_requested" in body, "khong huy duoc khi busy")
_fm = um.UpdateModal(None)
_fm.busy = True
_acts = _fm.get_footer_actions()
check("F6. thanh duoi noi ro B de huy trong luc dang tai",
      len(_acts) == 1 and _acts[0][0] == "B" and bool(_acts[0][1]), "footer: %s" % (_acts,))
_fm.applying = True
_acts2 = _fm.get_footer_actions()
check("F7. trong luc ghi tep thi noi ro la khong huy duoc",
      bool(_acts2) and _acts2[0][1] != _acts[0][1], "footer: %s" % (_acts2,))


print("G. Bo gia lap doc dung lua chon ban phim cua nguoi dung")
sh = io.open(JAVA_LAUNCH, encoding="utf-8", errors="ignore").read()
blk = sh.split("DEF_PHONE", 1)[1][:600] if "DEF_PHONE" in sh else ""
check("G1. launch.sh doc user.cfg truoc default_phone.cfg",
      blk.find("user.cfg") != -1 and (blk.find("user.cfg") < blk.find("default_phone.cfg") or blk.find("default_phone.cfg") == -1),
      "thu tu doc con sai")


print("H. Lint: trong mot ham, khong duoc dung ten roi moi import ten do")


def early_local_import_uses(path):
    """Ten vua duoc import trong than ham vua duoc dung o dong TRUOC lenh import.

    Do la UnboundLocalError. Ban 2.40 chinh vi the ma chet trong
    run_update_thread (runtime_pending / catalog_pending): thread cap nhat chet
    giua duong, busy khong bao gio duoc tra ve False, nguoi dung thay man hinh
    dung im o 95% va moi phim deu khong an."""
    try:
        tree = ast.parse(io.open(path, encoding="utf-8", errors="ignore").read())
    except SyntaxError:
        return []
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        imported = {}
        for sub in ast.walk(node):
            if isinstance(sub, ast.Import):
                names = [a.asname or a.name.split(".")[0] for a in sub.names]
            elif isinstance(sub, ast.ImportFrom):
                names = [a.asname or a.name for a in sub.names]
            else:
                continue
            for name in names:
                imported.setdefault(name, []).append(sub.lineno)
        for name, lines in imported.items():
            if len(lines) != 1:
                continue
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load)
                        and sub.id == name and sub.lineno < lines[0]):
                    bad.append((os.path.relpath(path, ROOT), node.name, name, sub.lineno, lines[0]))
    return bad


hops = []
for dirpath, dirs, names in os.walk(FILES):
    if "__pycache__" in dirpath:
        continue
    for n in names:
        if n.endswith(".py"):
            hops += early_local_import_uses(os.path.join(dirpath, n))
check("H1. khong ham nao dung ten truoc khi import (UnboundLocalError)",
      hops == [], str(hops[:3]))


print("I. Chay tron luong cap nhat trong thread (khong SDL)")


def run_flow(runtime_files, cancel_mid_runtime=False, payload_files=None, cancel_mid_catalog=False):
    """Chay that UpdateModal.run_update_thread voi cac buoc tai duoc gia lap."""
    calls, marks = [], []
    modal = um.UpdateModal(None)
    modal.manifest = {"version": APP_VERSION, "files": [],
                      "catalog": {"path": "catalog/roms_store.sqlite3", "url": "catalog/x.gz",
                                  "sha256": "a" * 64, "sha256_plain": "b" * 64,
                                  "size": 1, "size_plain": 1},
                      "runtime": {"files": []}}
    modal.files = list(payload_files or [])
    modal.cat_only = False

    def dl_rt(pending, progress=None, cancel=None):
        calls.append("dl_rt")
        if progress:
            progress(1, 2, "freej2me-sdl.jar")
        marks.append(modal.progress_pct)
        if cancel_mid_runtime:
            modal.cancel_requested = True
        if cancel and cancel():
            raise um.UpdateCancelled()
        if progress:
            progress(2, 2, "freej2me-sdl.jar")
        marks.append(modal.progress_pct)
        return "/tmp/rt"

    def dl_cat(m, progress=None, on_phase=None, cancel=None):
        calls.append("dl_cat")
        if progress:
            progress(1, 2, "catalog.gz")
        marks.append(modal.progress_pct)
        if cancel_mid_catalog:
            modal.cancel_requested = True
        if cancel and cancel():
            raise um.UpdateCancelled()
        if on_phase:
            on_phase()
        if progress:
            progress(2, 2, "roms_store.sqlite3")
        marks.append(modal.progress_pct)
        return "/tmp/cat"

    stubs = {
        "catalog_pending": lambda m, force=False: True,
        "runtime_pending": lambda m: list(runtime_files),
        "pending_files": lambda m: [],
        "download_update": lambda m, f, progress=None, cancel=None: True,
        "apply_update": lambda m, f: True,
        "download_runtime": dl_rt,
        "apply_runtime": lambda p: (calls.append("apply_rt"), True)[1],
        "download_catalog": dl_cat,
        "apply_catalog": lambda m, staged: (calls.append("apply_cat"), True)[1],
        "request_restart": lambda: calls.append("restart"),
    }
    saved = {k: getattr(um, k) for k in stubs}
    for k, v in stubs.items():
        setattr(um, k, v)
    try:
        modal.busy = True
        th = threading.Thread(target=modal.run_update_thread, daemon=True)
        th.start()
        th.join(30)
        alive = th.is_alive()
    finally:
        for k, v in saved.items():
            setattr(um, k, v)
    return modal, calls, marks, alive


modal, calls, marks, alive = run_flow([{"path": "zulu17/bin/freej2me-sdl.jar", "url": "u",
                                        "sha256": "0" * 64, "size": 1}])
check("I1. thread cap nhat chay het, khong chet giua duong", not alive)
check("I2. busy duoc tra ve False (khong dung im mai)", modal.busy is False)
check("I3. bo gia lap va kho game deu duoc chay",
      "apply_rt" in calls and "dl_cat" in calls and "apply_cat" in calls, str(calls))
check("I3b. modal khong tu chay buoc J2ME nua (viec do la cua luc khoi dong, chay nen)",
      "j2me" not in calls, str(calls))
check("I4. tien do khong bao gio tut va ket thuc o 100%",
      marks == sorted(marks) and modal.progress_pct == 1.0,
      "moc: %s -> %.2f" % (marks, modal.progress_pct))

modal2, calls2, _m2, alive2 = run_flow([{"path": "zulu17/bin/freej2me-sdl.jar", "url": "u",
                                        "sha256": "0" * 64, "size": 1}], cancel_mid_runtime=True)
check("I5. bam B giua luc tai thi dung ngay, khong cai gi ca",
      not alive2 and modal2.busy is False and modal2.cancelled is True
      and "apply_rt" not in calls2 and "dl_cat" not in calls2, str(calls2))

modal3, calls3, _m3, alive3 = run_flow([], payload_files=[{"path": "rh/version.py", "sha256": "0" * 64, "size": 1}],
                                      cancel_mid_catalog=True)
check("I6. huy sau khi da cai .py: khong cai kho game, nhung van khoi dong lai",
      not alive3 and modal3.busy is False and modal3.cancelled is True
      and "apply_cat" not in calls3 and modal3.restart is True and "restart" in calls3,
      str(calls3))


if made_db:
    os.remove(db_path)
shutil.rmtree(SD, ignore_errors=True)
shutil.rmtree(os.path.join(FILES, ".update_staging"), ignore_errors=True)
print()
if FAILED:
    print("FAILED %d check: %s" % (len(FAILED), ", ".join(FAILED)))
    sys.exit(1)
print("OK: luong OTA khong con bug nao trong audit")
