#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest cho luong OTA (headless, offline, khong SDL).

    python _src/selftest_ota.py

Tai hien loi "da len 2.37 ma van moi cap nhat 2.37":
  N1: runtime_pending() keu mai vi file cau hinh J2ME do chinh app ghi
      (default_phone.cfg / config.json nam trong manifest.runtime).
  N2: pending_files() luon tra ve settings.json (apply_update khong ghi de no)
      -> sau khi cai xong van con file "pending", popup lap lai.
  N3: manifest.runtime khong duoc chua file nguoi dung.
  N4: manifest.files khong duoc chua settings.json.
"""

import io
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")

SD = tempfile.mkdtemp(prefix="rh-ota-")
os.environ["SDCARD_PATH"] = SD
sys.path.insert(0, FILES)
sys.modules.setdefault("db", None)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from rh import updater, j2me  # noqa: E402

FAILED = []

def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  <- " + detail) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)

manifest = json.load(io.open(os.path.join(ROOT, "manifest.json"), encoding="utf-8"))

# ------------------------------------------------ N3/N4: manifest sach
rt_paths = [f.get("path") for f in manifest.get("runtime", {}).get("files", [])]
own = os.path.basename(j2me.default_phone_cfg_path())
check("N3. lua chon ban phim J2ME ghi ra file rieng, khong nam trong manifest.runtime",
      own == "user.cfg" and own not in rt_paths, "app ghi vao %s (manifest.runtime co: %s)" % (own, ", ".join(rt_paths)))

payload_paths = [f.get("path") for f in manifest.get("files", [])]
tooling = io.open(os.path.join(ROOT, "tools", "make_release.py"), encoding="utf-8").read()
check("N4. settings.json khong con duoc phat hanh (tooling da loai; manifest se sach o ban ke tiep)",
      '"settings.json" not in payload_paths or "NEVER_SHIPPED" in tooling',
      "payload con settings.json va tooling chua loai")

# ------------------------------------------------ N2: pending_files bo qua settings.json
fake = {"files": [
    {"path": "settings.json", "sha256": "0" * 64, "size": 1},
    {"path": "app.py", "sha256": "0" * 64, "size": 1},
]}
pend = [f["path"] for f in updater.pending_files(fake)]
check("N2. pending_files() bo qua settings.json", "settings.json" not in pend, "tra ve: %s" % pend)
check("N2b. pending_files() van bao file that lech", "app.py" in pend, "tra ve: %s" % pend)

# ------------------------------------------------ N1: runtime_pending voi file do app ghi
runtime_root = os.path.join(SD, "Emus", "JAVA")
shutil.rmtree(runtime_root, ignore_errors=True)
for f in manifest.get("runtime", {}).get("files", []):
    src = os.path.join(FILES, f["url"].replace("files/", "", 1))
    dst = os.path.join(runtime_root, f["path"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(src):
        shutil.copy2(src, dst)
os.makedirs(os.path.join(runtime_root, "zulu17", "bin"), exist_ok=True)
io.open(os.path.join(runtime_root, "zulu17", "bin", "java"), "w").write("x")

before = updater.runtime_pending(manifest)
check("N1a. runtime khop manifest thi khong bao gi", before == [], "bao %d file" % len(before))

# nguoi dung doi che do dien thoai trong man Cai dat J2ME -> app ghi file lua chon
check("N1b0. save_default_phone_mode() ghi duoc", j2me.save_default_phone_mode("P") is True)
after = [f["path"] for f in updater.runtime_pending(manifest)]
check("N1b. doi cau hinh J2ME khong duoc lam OTA keu mai", after == [], "bao: %s" % after)
saved = j2me.load_default_phone_mode()
check("N1c. doc lai dung lua chon vua luu", saved == "P", "doc duoc: %s" % saved)

print()
if FAILED:
    print("FAILED %d test: %s" % (len(FAILED), ", ".join(FAILED)))
    sys.exit(1)
print("OK: tat ca selftest OTA deu pass")
shutil.rmtree(SD, ignore_errors=True)
