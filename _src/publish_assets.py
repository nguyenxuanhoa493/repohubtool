#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload the large, non-source archives to a GitHub Release.

    GITHUB_TOKEN=... python3 _src/publish_assets.py

Theme zips, icon zips and emulator tarballs are *content*, not code. Keeping
them in git is what made every clone download a gigabyte. This script pushes
them to a single release (tag ``assets`` by default) and prints the base URL
that the catalog and the app should use.

Assets are skipped when a file of the same name already exists, so the script
is safe to re-run after a partial upload.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "nguyenxuanhoa493/repohubtool"
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"

SOURCES = [
    "Themes/zips/*.zip",
    "EmuIcons/zips/*.zip",
    "emus/*.tar.gz",
    "catalog/roms_store.sqlite3.gz",
]


def _request(method, url, token, data=None, content_type="application/json"):
    headers = {
        "Authorization": "Bearer %s" % token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repohubtool-publish-assets",
    }
    if data is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            body = json.loads(body)
        except Exception:
            body = {"message": body.decode("utf-8", "replace")}
        return e.code, body


def ensure_release(token, tag):
    status, data = _request("GET", "%s/repos/%s/releases/tags/%s" % (API, REPO, tag), token)
    if status == 200:
        return data["id"]
    payload = json.dumps({
        "tag_name": tag,
        "name": "Content assets",
        "body": "Large theme / icon / emulator archives served to the app. "
                "Managed by _src/publish_assets.py - do not edit by hand.",
    }).encode("utf-8")
    status, data = _request("POST", "%s/repos/%s/releases" % (API, REPO), token, payload)
    if status not in (200, 201):
        raise SystemExit("khong tao duoc release '%s': %s" % (tag, data))
    return data["id"]


def existing_assets(token, release_id):
    names = set()
    page = 1
    while True:
        status, data = _request(
            "GET", "%s/repos/%s/releases/%s/assets?per_page=100&page=%d"
            % (API, REPO, release_id, page), token)
        if status != 200 or not data:
            break
        for a in data:
            names.add(a["name"])
        if len(data) < 100:
            break
        page += 1
    return names


def upload(token, release_id, path):
    name = os.path.basename(path)
    with open(path, "rb") as f:
        blob = f.read()
    url = "%s/repos/%s/releases/%s/assets?name=%s" % (
        UPLOADS, REPO, release_id, urllib.parse.quote(name))
    status, data = _request("POST", url, token, blob, "application/octet-stream")
    return status, data


def main():
    import glob
    import urllib.parse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="assets")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("thieu GITHUB_TOKEN / GH_TOKEN")

    files = []
    for pattern in SOURCES:
        files.extend(sorted(glob.glob(os.path.join(ROOT, pattern))))
    if not files:
        raise SystemExit("khong tim thay archive nao de upload")

    base = "https://github.com/%s/releases/download/%s/" % (REPO, args.tag)
    print("Se upload %d file len %s" % (len(files), base))
    if args.dry_run:
        for f in files:
            print("  %s" % os.path.relpath(f, ROOT))
        return

    release_id = ensure_release(token, args.tag)
    have = existing_assets(token, release_id)
    print("Release id=%s, da co %d asset" % (release_id, len(have)))

    ok = skipped = failed = 0
    for path in files:
        name = os.path.basename(path)
        if name in have:
            skipped += 1
            continue
        status, data = upload(token, release_id, path)
        if status in (200, 201):
            ok += 1
            print("  OK   %s" % name)
        else:
            failed += 1
            print("  FAIL %s -> %s %s" % (name, status, data.get("message", "")))

    print("\nXong: %d moi, %d bo qua, %d loi" % (ok, skipped, failed))
    print("Base URL: %s" % base)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
