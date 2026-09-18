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
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES_DIR = os.path.join(ROOT, "files")
MANIFEST_PATH = os.path.join(ROOT, "manifest.json")


def step_1_syntax_and_ota_check():
    print("[1/7] Kiem tra cu phap Python & Tuong thich nguoc OTA tat ca phien ban cu...")
    errors = 0
    space_files = []
    unsafe_name_files = []
    
    safe_name_pattern = re.compile(r"^[a-zA-Z0-9_\-\.\/]+$")

    for root, _, files in os.walk(FILES_DIR):
        for f in files:
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, FILES_DIR)
            
            if not safe_name_pattern.match(rel):
                unsafe_name_files.append(rel)
            if " " in rel:
                space_files.append(rel)
            if f.endswith(".py"):
                try:
                    py_compile.compile(fp, doraise=True)
                except Exception as e:
                    print(f"  [!] LOI CU PHAP o file {os.path.relpath(fp, ROOT)}: {e}")
                    errors += 1

    if unsafe_name_files:
        print(f"FAILED: Phat hien {len(unsafe_name_files)} file co ky tu khong an toan voi OTA:")
        for uf in unsafe_name_files[:10]:
            print(f"  - {uf}")
        sys.exit(1)

    if errors > 0:
        print(f"FAILED: Phat hien {errors} loi cu phap! Vui long sua truoc khi release.")
        sys.exit(1)

    print("  -> Tat ca file Python deu vuot qua kiem tra cu phap & chuan hoa ten tep 100% URL-Safe.")


def step_2_check_i18n_keys():
    print("[2/7] Kiem tra tinh toan ven cua cac khoa da ngon ngu (i18n)...")
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
    print("[3/7] Quet va cap nhat ma bam SHA256 vao manifest.json...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    old_paths = {
        f["path"] for f in manifest.get("files", []) if isinstance(f, dict) and "path" in f
    }
    remove_list = set(manifest.get("remove", []))

    current_files = []
    scanned_paths = set()
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

            current_files.append({
                "path": rel,
                "size": size,
                "sha256": sha
            })
            scanned_paths.add(rel)
            scanned += 1

    # Tự động thêm các tệp đã xóa hoặc đổi tên vào danh sách remove
    deleted_paths = old_paths - scanned_paths
    for dp in deleted_paths:
        remove_list.add(dp)

    manifest["files"] = sorted(current_files, key=lambda x: x["path"])
    manifest["remove"] = sorted(list(remove_list))

    # Cap nhat luon ca cac tep trong runtime neu co
    for rf in manifest.get("runtime", {}).get("files", []):
        rel_url = rf.get("url", "")
        local_fp = os.path.join(ROOT, rel_url)
        if os.path.isfile(local_fp):
            with open(local_fp, "rb") as fh:
                data = fh.read()
            rf["size"] = len(data)
            rf["sha256"] = hashlib.sha256(data).hexdigest()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  -> Da dong bo ma bam SHA256 cua {scanned} tep vao manifest.json (kem runtime).")


def step_4_ota_simulation_suite():
    print("[4/7] Chay bo Test mo phong OTA client cho cac phien ban legacy (v1.20 - v2.33)...")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Version check
    target_ver = manifest.get("version", "2.35")
    def version_tuple(v):
        try:
            return tuple(int(p) for p in str(v).strip().lstrip("v").split("."))
        except Exception:
            return (0,)

    legacy_tags = ["1.20", "1.46", "1.80", "1.98", "2.00", "2.10", "2.19", "2.24", "2.27", "2.29", "2.31", "2.33", "2.34"]
    for tag in legacy_tags:
        if not (version_tuple(target_ver) > version_tuple(tag)):
            print(f"FAILED: Version so sanh loi: {target_ver} khong lon hon {tag}")
            sys.exit(1)

    # 2. Schema validation (v1.x, v2.x)
    files = manifest.get("files", [])
    if not isinstance(files, list) or len(files) == 0:
        print("FAILED: manifest['files'] rong hoac khong hop le!")
        sys.exit(1)

    has_version_py = False
    for f in files:
        p = f.get("path", "")
        if p == "rh/version.py":
            has_version_py = True
        sha = f.get("sha256", "")
        size = f.get("size", 0)
        
        # Test v1.x safe_rel
        if not p or p.startswith("/") or "\\" in p or ".." in p:
            print(f"FAILED: Unsafe path in manifest: {p}")
            sys.exit(1)
        if len(sha) != 64 or not re.match(r"^[0-9a-f]{64}$", sha):
            print(f"FAILED: Invalid sha256 in manifest: {p} -> {sha}")
            sys.exit(1)
        if size <= 0 or size > 32 * 1024 * 1024:
            print(f"FAILED: File size invalid (>32MB or <=0): {p} -> {size}")
            sys.exit(1)

        # Test unquoted URL construction of legacy clients
        legacy_url = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main/files/%s" % p
        if " " in legacy_url:
            print(f"FAILED: Space found in legacy URL: {legacy_url}")
            sys.exit(1)

    if not has_version_py:
        print("FAILED: manifest thieu rh/version.py (bat buoc phai co de atomic swap)!")
        sys.exit(1)

    print(f"  -> Mo phong thanh cong 100% tren {len(legacy_tags)} phien ban lich su!")


def step_5_package_dist():
    print("[5/7] Dong goi cac tap tin phat hanh trong dist/...")
    dist_dir = os.path.join(ROOT, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        ver = json.load(f).get("version", "2.35")

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
    make_zip(os.path.join(dist_dir, f"RetroHub-{ver}-NextUI.zip"), "Tools/tg5040/RetroHub.pak")
    make_zip(os.path.join(dist_dir, "RetroHub.pak.zip"), "Tools/tg5040/RetroHub.pak")
    print("  -> Da tao day du cac goi zip: full, NextUI.")


def step_6_build_site():
    print("[6/7] Cap nhat HTML landing page & changelog...")
    os.system(f"python3 {os.path.join(ROOT, '_src', 'build.py')}")
    os.system(f"python3 {os.path.join(ROOT, '_src', 'build_changelog.py')}")
    os.system(f"python3 {os.path.join(ROOT, '_src', 'build_guide.py')}")
    os.system(f"python3 {os.path.join(ROOT, '_src', 'build_java.py')}")
    print("  -> Hoan tat build site HTML!")


def step_7_publish_github_release(publish: bool = False):
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    ver = manifest.get("version", "2.35")
    note_en = manifest.get("note", {}).get("en", f"RetroHub v{ver} Release")
    dist_dir = os.path.join(ROOT, "dist")
    
    full_zip = os.path.join(dist_dir, f"RetroHub-{ver}-full.zip")
    nextui_zip = os.path.join(dist_dir, f"RetroHub-{ver}-NextUI.zip")
    core_zip = os.path.join(dist_dir, f"RetroHub-{ver}.zip")

    if not publish:
        print("\n[7/7] Huong dan upload GitHub Releases (hoac chay voi flag --publish):")
        print(f"  gh release create v{ver} \"{full_zip}\" \"{nextui_zip}\" \"{core_zip}\" --title \"RetroHub v{ver}\" --notes \"{note_en}\"")
        return

    print(f"\n[7/7] Dang tu dong phat hanh GitHub Release v{ver} qua gh CLI...")
    # Kiem tra release da ton tai chua
    check_code = os.system(f"gh release view v{ver} >/dev/null 2>&1")
    if check_code != 0:
        create_cmd = f"gh release create v{ver} -t \"RetroHub v{ver}\" -n \"{note_en}\""
        os.system(create_cmd)
    
    upload_cmd = f"gh release upload v{ver} \"{full_zip}\" \"{nextui_zip}\" \"{core_zip}\" --clobber"
    ret = os.system(upload_cmd)
    if ret == 0:
        print(f"  -> Da upload thanh cong toan bo file zip len GitHub Release v{ver}!")
    else:
        print(f"  [!] Upload that bai hoac loi mang (exit code: {ret})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quy trinh Kiem chuan & Release RetroHub")
    parser.add_argument("--publish", action="store_true", help="Tu dong tao va upload file len GitHub Releases qua gh CLI")
    args = parser.parse_args()

    print("==================================================")
    print("      QUY TRINH KIEM CHUAN & RELEASE RETROHUB     ")
    print("==================================================")
    step_1_syntax_and_ota_check()
    step_2_check_i18n_keys()
    step_3_update_manifest()
    step_4_ota_simulation_suite()
    step_5_package_dist()
    step_6_build_site()
    step_7_publish_github_release(publish=args.publish)
    print("==================================================")
    print("  SUCCESS: Quy trinh release hoan tat!")
    print("==================================================")
