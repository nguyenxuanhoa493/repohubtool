#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script chuẩn hóa toàn bộ quy trình Release cho RetroHub:
1. Kiểm tra cú pháp (syntax check) toàn bộ file Python.
2. Kiểm tra tính hợp lệ của các chuỗi tr(...) trong UI so với i18n.py.
3. Tự động quét và tính mã băm SHA256 + kích thước tệp vào manifest.json.
4. Đóng gói các tệp phát hành zip trong dist/.
5. Tự động biên dịch lại HTML landing page và changelog.
"""

import os
import sys
import json
import hashlib
import py_compile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_DIR = os.path.join(ROOT, "files")
MANIFEST_PATH = os.path.join(ROOT, "manifest.json")


def step_1_syntax_check():
    print("[1/5] Kiem tra cu phap cac file Python...")
    errors = 0
    for root, _, files in os.walk(FILES_DIR):
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(root, f)
                try:
                    py_compile.compile(fp, doraise=True)
                except Exception as e:
                    print(f"  [!] LOI CU PHAP o file {os.path.relpath(fp, ROOT)}: {e}")
                    errors += 1
    if errors > 0:
        print(f"FAILED: Phat hien {errors} loi cu phap! Vui long sua truoc khi release.")
        sys.exit(1)
    print("  -> Tat ca file Python deu vuot qua kiem tra cu phap.")


def step_2_check_i18n_keys():
    print("[2/5] Kiem tra tinh toan ven cua cac khoa da ngon ngu (i18n)...")
    sys.path.insert(0, FILES_DIR)
    try:
        from rh.i18n import TEXTS
        valid_keys = set(TEXTS.get("VI", {}).keys()) | set(TEXTS.get("EN", {}).keys())
    except Exception as e:
        print(f"  [!] Khong the import rh.i18n: {e}")
        return

    import re
    tr_pattern = re.compile(r'\btr\(["\']([a-zA-Z0-9_]+)["\']\)')
    missing = set()
    for root, _, files in os.walk(FILES_DIR):
        for f in files:
            if f.endswith(".py"):
                fp = os.path.join(root, f)
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for key in tr_pattern.findall(content):
                    if key not in valid_keys:
                        missing.add((os.path.relpath(fp, ROOT), key))

    if missing:
        print("  [!] Canh bao: Phat hien cac key tr(...) chua co trong i18n.py:")
        for fp, k in sorted(missing):
            print(f"      - {fp}: tr('{k}')")
    else:
        print("  -> Tat ca cac key tr(...) deu co trong tu dien i18n.py.")


def step_3_update_manifest():
    print("[3/5] Quet va cap nhat ma bam SHA256 vao manifest.json...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest_files_by_path = {
        f["path"]: f for f in manifest.get("files", []) if isinstance(f, dict) and "path" in f
    }

    scanned = 0
    for root, _, files in os.walk(FILES_DIR):
        for fn in sorted(files):
            if fn.startswith(".") or fn.endswith(".pyc") or fn == "desktop.ini":
                continue
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, FILES_DIR)
            with open(fp, "rb") as fh:
                data = fh.read()
            sha = hashlib.sha256(data).hexdigest()
            size = len(data)

            if rel in manifest_files_by_path:
                manifest_files_by_path[rel]["sha256"] = sha
                manifest_files_by_path[rel]["size"] = size
            else:
                manifest_files_by_path[rel] = {
                    "path": rel,
                    "size": size,
                    "sha256": sha
                }
            scanned += 1

    manifest["files"] = sorted(list(manifest_files_by_path.values()), key=lambda x: x["path"])

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  -> Da dong bo ma bam SHA256 cua {scanned} tep vao manifest.json.")


def step_4_package_dist():
    print("[4/5] Dong goi cac tap tin phat hanh trong dist/...")
    dist_dir = os.path.join(ROOT, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        ver = json.load(f).get("version", "2.27")

    def make_zip(out_path, prefix="Apps/RetroHub"):
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(FILES_DIR):
                for fn in files:
                    if fn.startswith(".") or fn.endswith(".pyc"):
                        continue
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, FILES_DIR)
                    arcname = f"{prefix}/{rel}" if prefix else rel
                    z.write(fp, arcname)

    make_zip(os.path.join(dist_dir, f"RetroHub-{ver}-full.zip"), "Apps/RetroHub")
    make_zip(os.path.join(dist_dir, f"RetroHub-{ver}.zip"), "Apps/RetroHub")
    make_zip(os.path.join(dist_dir, "RetroHub-HOTFIX.zip"), "Apps/RetroHub")
    make_zip(os.path.join(dist_dir, f"RetroHub-{ver}-NextUI.zip"), "Tools/tg5040/RetroHub.pak")
    make_zip(os.path.join(dist_dir, "RetroHub.pak.zip"), "Tools/tg5040/RetroHub.pak")
    print("  -> Da tao day du cac goi zip: full, NextUI, HOTFIX.")


def step_5_build_site():
    print("[5/5] Cap nhat HTML landing page & changelog...")
    os.system(f"python3 {os.path.join(ROOT, '_src', 'build.py')}")
    os.system(f"python3 {os.path.join(ROOT, '_src', 'build_changelog.py')}")
    print("  -> Hoan tat build site HTML!")


if __name__ == "__main__":
    print("==================================================")
    print("      QUY TRINH KIEM CHUAN & RELEASE RETROHUB     ")
    print("==================================================")
    step_1_syntax_check()
    step_2_check_i18n_keys()
    step_3_update_manifest()
    step_4_package_dist()
    step_5_build_site()
    print("==================================================")
    print("  SUCCESS: San pham da san sang de commit & push!")
    print("==================================================")
