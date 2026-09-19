# -*- coding: utf-8 -*-
"""Selftest cho changelogs.json - nguon duy nhat cua changelog.

    python _src/selftest_changelog.py

Kiem: file JSON hop le va du truong, version khong trung va xep giam dan, phien
ban dang phat hanh (files/rh/version.py) phai co muc day du, manifest.note phai
khop headline (chong lech giua popup OTA va trang changelog), thong bao Telegram
sinh ra tu chinh muc do va khong vuot gioi han 4096 ky tu, va script Telegram
khong con noi dung hardcode cua ban cu.
"""

import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "files"))
sys.path.insert(0, os.path.join(ROOT, "_src"))
sys.modules.setdefault("db", None)
sys.modules.setdefault("sdl2", None)

FAILED = []

def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  <- " + str(detail)) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)

def read_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)

def app_version():
    with io.open(os.path.join(ROOT, "files", "rh", "version.py"), encoding="utf-8") as f:
        return re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', f.read()).group(1).lstrip("v")

def vkey(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)

print("T1. changelogs.json: cau truc")
doc = read_json(os.path.join(ROOT, "changelogs.json"))
check("T1a. co schema", doc.get("schema") == 1, doc.get("schema"))
rels = doc.get("releases") or []
check("T1b. co it nhat 1 phien ban", len(rels) > 1, len(rels))

versions = [str(r.get("version", "")) for r in rels]
check("T1c. version khong trung", len(versions) == len(set(versions)),
      [v for v in versions if versions.count(v) > 1][:3])
check("T1d. xep tu moi den cu", versions == sorted(versions, key=vkey, reverse=True), versions[:3])
bad_head = [v for v, r in zip(versions, rels)
            if not (r.get("headline") or {}).get("vi") or not (r.get("headline") or {}).get("en")]
check("T1e. moi muc co headline vi+en", not bad_head, bad_head[:3])
bad_bullet = [(v, i) for v, r in zip(versions, rels) for i, b in enumerate(r.get("bullets") or [])
              if not b.get("vi") or not b.get("en")]
check("T1f. moi bullet co vi+en", not bad_bullet, bad_bullet[:3])
check("T1g. moi muc co ngay", all(r.get("date") for r in rels))

print("T2. Phien ban dang phat hanh phai co muc day du")
ver = app_version()
entry = next((r for r in rels if str(r.get("version")) == ver), None)
check("T2a. version.py co muc trong changelog", entry is not None, ver)
if entry:
    check("T2b. muc do co it nhat 1 bullet", len(entry.get("bullets") or []) >= 1,
          len(entry.get("bullets") or []))
    check("T2c. headline khac rong", bool((entry.get("headline") or {}).get("vi")))

print("T3. manifest.note phai khop changelog (chong lech)")
man = read_json(os.path.join(ROOT, "manifest.json"))
m_entry = next((r for r in rels if str(r.get("version")) == str(man.get("version"))), None)
if not m_entry:
    check("T3a. manifest version co muc changelog", False, man.get("version"))
else:
    head = m_entry.get("headline") or {}
    check("T3a. note en khop", (man.get("note") or {}).get("en") == head.get("en"),
          "manifest: %r" % ((man.get("note") or {}).get("en", "")[:60],))
    check("T3b. note vi khop", (man.get("note") or {}).get("vi") == head.get("vi"),
          "chay tools/make_release.py de dong bo")

print("T4. Thong bao Telegram sinh tu changelog")
import notify_ota_telegram as notify
msg = notify.build_message(ver, entry)
check("T4a. trong gioi han Telegram (4096)", len(msg) <= 4096, len(msg))
check("T4b. co headline cua ban dang phat hanh",
      not entry or head.get("vi", "x")[:25] in msg)
check("T4c. co it nhat 1 bullet cua ban dang phat hanh",
      not entry or any(b["vi"][:25] in msg for b in (entry.get("bullets") or [])))
check("T4d. khong vuot tran 4000 khi bullet rat dai",
      len(notify.build_message(ver, {"headline": {"vi": "x"},
                                     "bullets": [{"vi": "y" * 300} for _ in range(40)]})) <= 4096)
src = io.open(os.path.join(ROOT, "_src", "notify_ota_telegram.py"), encoding="utf-8").read()
check("T4e. script Telegram khong con noi dung hardcode cua ban cu",
      "time_elapsed" not in src and "Kho gi" + "ả lập" not in src)

print()
if FAILED:
    print("FAILED %d test: %s" % (len(FAILED), ", ".join(FAILED)))
    sys.exit(1)
print("OK: changelog + thong bao Telegram deu lay tu changelogs.json")
