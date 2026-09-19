#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test API endpoints cho GameWeb Google Drive integration."""

import os
import sys
import json
import time
import urllib.request
import threading
import tempfile
import shutil
from http.server import HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")

SD = tempfile.mkdtemp(prefix="rh-gw-")
os.environ["SDCARD_PATH"] = SD
sys.path.insert(0, FILES)
sys.modules.setdefault("db", None)

from gameweb import GameWebHandler

def run_test_server():
    server = HTTPServer(("127.0.0.1", 18889), GameWebHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    time.sleep(0.5)

    base = "http://127.0.0.1:18889"

    # 1. Test GET /api/gdrive/library
    req = urllib.request.Request(f"{base}/api/gdrive/library")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True
        assert isinstance(data.get("items"), list)
    print("[PASS] GET /api/gdrive/library")

    # 2. Test GET /api/gdrive/systems
    req = urllib.request.Request(f"{base}/api/gdrive/systems")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True
        assert isinstance(data.get("systems"), list)
    print("[PASS] GET /api/gdrive/systems")

    # 3. Test POST /api/gdrive/library/add
    payload = json.dumps({
        "file_id": "test_id_999",
        "title": "Super Mario World",
        "filename": "smw.sfc",
        "file_size": "2.0 MB",
        "direct_link": "https://example.com/smw.sfc",
        "suggested_sys": "SFC"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/api/gdrive/library/add", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True
        assert data["item"]["id"] == "gdrive_test_id_999"
    print("[PASS] POST /api/gdrive/library/add")

    # 4. Test GET /api/gdrive/library has item
    req = urllib.request.Request(f"{base}/api/gdrive/library")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Super Mario World"
    print("[PASS] GET /api/gdrive/library verify added item")

    # 5. Test POST /api/gdrive/library/delete
    del_payload = json.dumps({"id": "gdrive_test_id_999"}).encode("utf-8")
    req = urllib.request.Request(f"{base}/api/gdrive/library/delete", data=del_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("ok") is True
    print("[PASS] POST /api/gdrive/library/delete")

    # 6. Verify empty again
    req = urllib.request.Request(f"{base}/api/gdrive/library")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["items"]) == 0
    print("[PASS] GET /api/gdrive/library verify empty")

    server.shutdown()
    server.server_close()

if __name__ == "__main__":
    try:
        run_test_server()
        print("\nALL GAMEWEB GDRIVE API TESTS PASSED!")
    finally:
        shutil.rmtree(SD, ignore_errors=True)
