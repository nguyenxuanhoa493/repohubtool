#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Point the catalogs at the GitHub Release that holds the large archives.

    GITHUB_TOKEN=... python3 _src/migrate_assets_urls.py

GitHub rewrites asset filenames on upload (spaces become dots, '&' is dropped),
so the URL cannot be derived from the local filename. This reads the release
back, matches assets to catalog entries by a normalised key, and writes the
canonical browser_download_url into every catalog copy.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "nguyenxuanhoa493/repohubtool"
TAG = "assets"
API = "https://api.github.com"
ASSET_BASE = "https://github.com/%s/releases/download/%s/" % (REPO, TAG)

CATALOGS = [
    "catalog/themes_catalog.json",
    "files/catalog/themes_catalog.json",
    "catalog/icons_catalog.json",
    "files/catalog/icons_catalog.json",
]


def norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def fetch_assets(token):
    headers = {"Authorization": "Bearer %s" % token,
               "Accept": "application/vnd.github+json",
               "User-Agent": "repohubtool-migrate"}
    req = urllib.request.Request(
        "%s/repos/%s/releases/tags/%s" % (API, REPO, TAG), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        release = json.load(resp)
    assets = {}
    page = 1
    while True:
        req = urllib.request.Request(
            "%s/repos/%s/releases/%s/assets?per_page=100&page=%d"
            % (API, REPO, release["id"], page), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            batch = json.load(resp)
        if not batch:
            break
        for a in batch:
            assets[norm(a["name"])] = a["browser_download_url"]
        if len(batch) < 100:
            break
        page += 1
    return assets


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("thieu GITHUB_TOKEN / GH_TOKEN")

    assets = fetch_assets(token)
    print("Doc duoc %d asset tu release '%s'" % (len(assets), TAG))

    missing = []
    changed = 0
    for rel in CATALOGS:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        data["base_cdn_url"] = ASSET_BASE
        items = data.get("themes") or data.get("icons") or []
        for item in items:
            fn = item.get("zip_file")
            if not fn:
                continue
            url = assets.get(norm(fn))
            if not url:
                missing.append(fn)
                continue
            if item.get("download_url") != url:
                changed += 1
            item["download_url"] = url
            item["raw_git_url"] = url

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("  cap nhat %s (%d muc)" % (rel, len(items)))

    print("Da doi %d URL" % changed)
    if missing:
        print("!! %d muc khong tim thay asset:" % len(missing))
        for m in missing[:20]:
            print("   - %s" % m)
        sys.exit(1)


if __name__ == "__main__":
    main()
