#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate catalog/themes_catalog.json, build preview thumbnails, and package zips from Themes/ folder."""

import os
import json
import zipfile
import shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_SRC_DIR = os.path.join(ROOT, "Themes")
ZIPS_DIR = os.path.join(THEMES_SRC_DIR, "zips")
PREVIEWS_DIR = os.path.join(ROOT, "files", "assets", "themes_preview")
CATALOG_DIR = os.path.join(ROOT, "catalog")
OUTPUT_JSON = os.path.join(CATALOG_DIR, "themes_catalog.json")
APP_CATALOG_JSON = os.path.join(ROOT, "files", "catalog", "themes_catalog.json")

CDN_BASE_URL = "https://retrohub.xuanhoa493.com/Themes/zips/"
RAW_GIT_BASE_URL = "https://raw.githubusercontent.com/nguyenxuanhoa493/repohubtool/main/Themes/zips/"


def clean_junk(directory: str):
    """Removes macOS / Windows artifact files recursively."""
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f in [".DS_Store", "Thumbs.db", "desktop.ini"] or f.startswith("._"):
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass


def generate_preview(theme_path: str, item_name: str) -> bool:
    """Generates an 800px-wide thumbnail preview if an original preview image exists."""
    candidates = ["preview.png", "preview.jpg", "theme-preview.png", "p.png"]
    src_preview = None
    for c in candidates:
        cp = os.path.join(theme_path, c)
        if os.path.isfile(cp):
            src_preview = cp
            break

    if not src_preview:
        return False

    os.makedirs(PREVIEWS_DIR, exist_ok=True)
    safe_name = item_name.replace(" ", "_")
    dst_preview = os.path.join(PREVIEWS_DIR, f"{safe_name}.png")

    # If destination already exists and is newer than source, skip regenerating
    if os.path.isfile(dst_preview) and os.path.getmtime(dst_preview) >= os.path.getmtime(src_preview):
        return True

    try:
        with Image.open(src_preview) as im:
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA")
            target_w = 800
            ratio = target_w / float(im.width)
            target_h = max(1, int(im.height * ratio))
            resized = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
            resized.save(dst_preview, "PNG", optimize=True)
        return True
    except Exception as e:
        print(f"  [!] Failed to generate preview for {item_name}: {e}")
        return False


def build_theme_zip(theme_path: str, item_name: str, force_rebuild: bool = False) -> str:
    """Zips the theme contents into Themes/zips/<ThemeName>.zip."""
    os.makedirs(ZIPS_DIR, exist_ok=True)
    zip_path = os.path.join(ZIPS_DIR, f"{item_name}.zip")

    # Check if rebuild is needed
    if not force_rebuild and os.path.isfile(zip_path):
        zip_mtime = os.path.getmtime(zip_path)
        needs_update = False
        for root, _, files in os.walk(theme_path):
            for f in files:
                if f.startswith("."):
                    continue
                fp = os.path.join(root, f)
                if os.path.getmtime(fp) > zip_mtime:
                    needs_update = True
                    break
            if needs_update:
                break
        if not needs_update:
            return zip_path

    # Build clean zip
    tmp_zip = zip_path + ".tmp"
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(theme_path):
            dirs.sort()
            for f in sorted(files):
                if f.startswith(".") or f in ["Thumbs.db", "desktop.ini"] or f.startswith("._"):
                    continue
                fp = os.path.join(root, f)
                arcname = os.path.relpath(fp, theme_path)
                zf.write(fp, arcname)

    if os.path.exists(zip_path):
        os.remove(zip_path)
    os.rename(tmp_zip, zip_path)
    return zip_path


def scan_and_build():
    if not os.path.isdir(THEMES_SRC_DIR):
        print(f"Directory not found: {THEMES_SRC_DIR}")
        return []

    clean_junk(THEMES_SRC_DIR)

    themes = []
    items = sorted(os.listdir(THEMES_SRC_DIR))

    for item in items:
        if item.startswith(".") or item == "zips":
            continue
        theme_path = os.path.join(THEMES_SRC_DIR, item)
        if not os.path.isdir(theme_path):
            continue

        config_path = os.path.join(theme_path, "config.json")
        name = item
        font = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    name = cfg.get("name", item) or item
                    font = cfg.get("font", "")
            except Exception:
                pass

        # 1. Preview generation
        safe_name = item.replace(" ", "_")
        has_preview = generate_preview(theme_path, item)
        preview_rel = f"assets/themes_preview/{safe_name}.png" if has_preview else ""

        # 2. Package Zip
        zip_path = build_theme_zip(theme_path, item)
        zip_size_bytes = os.path.getsize(zip_path) if os.path.exists(zip_path) else 0

        size_mb = round(zip_size_bytes / (1024 * 1024), 2)
        size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{zip_size_bytes // 1024} KB"

        themes.append({
            "id": item,
            "name": name,
            "folder": item,
            "font": font,
            "has_preview": has_preview,
            "zip_file": f"{item}.zip",
            "zip_size_bytes": zip_size_bytes,
            "size_str": size_str,
            "preview_rel": preview_rel,
            "download_url": f"{CDN_BASE_URL}{item}.zip",
            "raw_git_url": f"{RAW_GIT_BASE_URL}{item}.zip"
        })

    return themes


def main():
    os.makedirs(CATALOG_DIR, exist_ok=True)
    print("Scanning Themes, generating previews, packaging zips...")
    themes = scan_and_build()

    payload = {
        "version": "2.0",
        "total": len(themes),
        "base_cdn_url": CDN_BASE_URL,
        "themes": themes
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Generated {OUTPUT_JSON} with {len(themes)} themes.")

    os.makedirs(os.path.dirname(APP_CATALOG_JSON), exist_ok=True)
    with open(APP_CATALOG_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Synced into {APP_CATALOG_JSON}")


if __name__ == "__main__":
    main()

