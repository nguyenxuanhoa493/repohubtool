#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate catalog/icons_catalog.json from EmuIcons/ folder and build zips."""

import os
import json
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_SRC_DIR = os.path.join(ROOT, "EmuIcons")
ICONS_ZIPS_DIR = os.path.join(ICONS_SRC_DIR, "zips")
CATALOG_DIR = os.path.join(ROOT, "catalog")
OUTPUT_JSON = os.path.join(CATALOG_DIR, "icons_catalog.json")
APP_CATALOG_JSON = os.path.join(ROOT, "files", "catalog", "icons_catalog.json")
APP_ASSETS_PREVIEW_DIR = os.path.join(ROOT, "files", "assets", "icons_preview")

BASE_CDN_URL = "https://retrohub.xuanhoa493.com/EmuIcons/zips/"
BASE_RAW_GIT_URL = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main/EmuIcons/zips/"


def build_icon_pack_zip(pack_name: str, pack_path: str) -> str:
    """Packs the Emu icon directory (containing Emus/) into a compact zip file."""
    os.makedirs(ICONS_ZIPS_DIR, exist_ok=True)
    zip_path = os.path.join(ICONS_ZIPS_DIR, f"{pack_name}.zip")
    
    emus_dir = os.path.join(pack_path, "Emus")
    if not os.path.isdir(emus_dir):
        emus_dir = pack_path

    # Clean up duplicate _themes folder locally to keep zip compact
    t1 = os.path.join(emus_dir, "_theme")
    t2 = os.path.join(emus_dir, "_themes")
    if os.path.isdir(t1) and os.path.isdir(t2):
        shutil.rmtree(t2)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(emus_dir):
            for file in files:
                if file.startswith(".") or file.endswith(".zip"):
                    continue
                abs_f = os.path.join(root, file)
                rel_f = os.path.relpath(abs_f, pack_path)
                zf.write(abs_f, rel_f)

    print(f"  [+] Created Zip: {zip_path} ({os.path.getsize(zip_path) // 1024} KB)")
    return zip_path


def scan_icons():
    if not os.path.isdir(ICONS_SRC_DIR):
        print(f"Directory not found: {ICONS_SRC_DIR}")
        return []

    os.makedirs(APP_ASSETS_PREVIEW_DIR, exist_ok=True)
    icon_packs = []

    for item in sorted(os.listdir(ICONS_SRC_DIR)):
        if item.startswith(".") or item == "zips":
            continue
        pack_path = os.path.join(ICONS_SRC_DIR, item)
        if not os.path.isdir(pack_path):
            continue

        config_path = os.path.join(pack_path, "config.json")
        preview_path = os.path.join(pack_path, "preview.png")

        name = item
        author = "Burst / Community"
        version = "1.1.0"
        desc = "Bộ icon và background hệ máy giả lập tối ưu cho TrimUI Smart Pro Stock OS 1.1.0"
        system = "TrimUI Smart Pro"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    name = cfg.get("name", item) or item
                    author = cfg.get("author", author)
                    version = cfg.get("version", version)
                    desc = cfg.get("description", desc)
                    system = cfg.get("system", system)
            except Exception as e:
                print(f"Error reading config {config_path}: {e}")

        zip_path = build_icon_pack_zip(item, pack_path)
        zip_size = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0
        size_mb = round(zip_size / (1024 * 1024), 2)
        size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{zip_size // 1024} KB"

        icon_count = 0
        bg_count = 0
        themes_dir = os.path.join(pack_path, "Emus", "_theme")
        if not os.path.isdir(themes_dir):
            themes_dir = os.path.join(pack_path, "Emus", "_themes")
        if os.path.isdir(themes_dir):
            for f in os.listdir(themes_dir):
                if f.startswith("ic-") and f.endswith(".png"):
                    icon_count += 1
                elif f.startswith("bg-") and f.endswith(".png"):
                    bg_count += 1

        has_preview = os.path.exists(preview_path)
        preview_rel = ""
        if has_preview:
            preview_dest = os.path.join(APP_ASSETS_PREVIEW_DIR, f"{item}.png")
            shutil.copy2(preview_path, preview_dest)
            preview_rel = f"assets/icons_preview/{item}.png"

        import urllib.parse
        zip_filename = f"{item}.zip"
        enc_zip_name = urllib.parse.quote(zip_filename)
        icon_packs.append({
            "id": item,
            "name": name,
            "folder": item,
            "author": author,
            "version": version,
            "system": system,
            "description": desc,
            "has_preview": has_preview,
            "icon_count": icon_count,
            "bg_count": bg_count,
            "zip_file": zip_filename,
            "zip_size_bytes": zip_size,
            "size_str": size_str,
            "preview_rel": preview_rel,
            "download_url": f"{BASE_CDN_URL}{enc_zip_name}",
            "raw_git_url": f"{BASE_RAW_GIT_URL}{enc_zip_name}",
        })

    return icon_packs


def main():
    os.makedirs(CATALOG_DIR, exist_ok=True)
    icons = scan_icons()
    payload = {
        "version": "1.0",
        "total": len(icons),
        "base_cdn_url": BASE_CDN_URL,
        "icons": icons
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generated {OUTPUT_JSON} with {len(icons)} icon packs.")

    os.makedirs(os.path.dirname(APP_CATALOG_JSON), exist_ok=True)
    with open(APP_CATALOG_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Synced into {APP_CATALOG_JSON}")


if __name__ == "__main__":
    main()
