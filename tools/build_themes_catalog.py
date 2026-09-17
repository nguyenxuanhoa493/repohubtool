#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate catalog/themes_catalog.json from Themes/ folder."""

import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_SRC_DIR = os.path.join(ROOT, "Themes")
CATALOG_DIR = os.path.join(ROOT, "catalog")
OUTPUT_JSON = os.path.join(CATALOG_DIR, "themes_catalog.json")
APP_CATALOG_JSON = os.path.join(ROOT, "files", "catalog", "themes_catalog.json")


def scan_themes():
    if not os.path.isdir(THEMES_SRC_DIR):
        print(f"Directory not found: {THEMES_SRC_DIR}")
        return []

    themes = []
    for item in sorted(os.listdir(THEMES_SRC_DIR)):
        if item.startswith("."):
            continue
        theme_path = os.path.join(THEMES_SRC_DIR, item)
        if not os.path.isdir(theme_path):
            continue

        config_path = os.path.join(theme_path, "config.json")
        preview_path = os.path.join(theme_path, "preview.png")

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

        total_size = 0
        file_count = 0
        has_skin = os.path.isdir(os.path.join(theme_path, "skin"))
        has_sound = os.path.isdir(os.path.join(theme_path, "sound"))

        for r, _, files in os.walk(theme_path):
            for f in files:
                if not f.startswith("."):
                    file_count += 1
                    fp = os.path.join(r, f)
                    total_size += os.path.getsize(fp)

        size_mb = round(total_size / (1024 * 1024), 2)
        size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{total_size // 1024} KB"

        themes.append({
            "id": item,
            "name": name,
            "folder": item,
            "font": font,
            "has_preview": os.path.exists(preview_path),
            "has_skin": has_skin,
            "has_sound": has_sound,
            "file_count": file_count,
            "size_bytes": total_size,
            "size_str": size_str,
            "preview_rel": f"Themes/{item}/preview.png" if os.path.exists(preview_path) else "",
        })

    return themes


def main():
    os.makedirs(CATALOG_DIR, exist_ok=True)
    themes = scan_themes()
    payload = {
        "version": "1.0",
        "total": len(themes),
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
