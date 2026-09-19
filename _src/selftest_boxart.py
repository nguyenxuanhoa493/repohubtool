# -*- coding: utf-8 -*-
"""Selftest cho viec tai anh bia: han muc tong thoi gian & gioi han dung luong.

    python _src/selftest_boxart.py

Khong can mang that: test mo mot HTTP server cuc bo roi gia lap 3 tinh huong
  - anh nho, tra ve ngay            -> phai tai duoc;
  - server nho giot tung byte        -> phai bo sau ~1s, khong duoc treo mai;
  - body nhanh nhung qua nang        -> phai bo vi qua dung luong.
"""

import base64
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")
os.environ.setdefault("SDCARD_PATH", tempfile.mkdtemp(prefix="rh-boxart-"))
sys.path.insert(0, FILES)
sys.path.insert(0, os.path.join(FILES, "vendor"))
sys.modules.setdefault("db", None)

from rh import boxart_scraper as bs

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")

MODE = {"kind": "fast", "size": 0}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def do_GET(self):
        kind = MODE["kind"]
        if kind == "fast":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG_1PX)))
            self.end_headers()
            self.wfile.write(PNG_1PX)
        elif kind == "trickle":
            total = MODE["size"]
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(total))
            self.end_headers()
            sent = 0
            while sent < total:
                try:
                    self.wfile.write(b"\\x00")
                    self.wfile.flush()
                except Exception:
                    return
                sent += 1
                time.sleep(0.2)
        elif kind == "heavy":
            body = b"\\x00" * MODE["size"]
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

srv = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d/img.png" % srv.server_address[1]

ok = True
def check(name, cond, detail=""):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + name + ((" | " + str(detail)) if detail else ""))
    if not cond:
        ok = False

out = os.path.join(tempfile.gettempdir(), "rh-boxart-test.png")

# T0: mac dinh cho ca lan tai la 30s
check("T0. han muc mac dinh = 30s", bs.BOXART_TOTAL_TIMEOUT == 30, bs.BOXART_TOTAL_TIMEOUT)

# T1: anh binh thuong
MODE.update(kind="fast")
ok1, err1 = bs.download_image_to_file(BASE, out, timeout=5, total_timeout=10)
check("T1. tai duoc anh nho", ok1 is True, err1)

# T2: server nho giot -> phai bo theo han muc tong, khong treo
MODE.update(kind="trickle", size=10000)
t0 = time.time()
ok2, err2 = bs.download_image_to_file(BASE, out, timeout=5, total_timeout=1)
dt = time.time() - t0
check("T2. bo khi qua han muc tong (1s)", ok2 is False and dt < 3.5 and "thoi gian" in str(err2),
      "%.2fs | %s" % (dt, err2))

# T3: body nhanh nhung vuot gioi han dung luong
old_max = bs.BOXART_MAX_BYTES
bs.BOXART_MAX_BYTES = 4096
MODE.update(kind="heavy", size=20000)
t0 = time.time()
ok3, err3 = bs.download_image_to_file(BASE, out, timeout=5, total_timeout=10)
dt3 = time.time() - t0
bs.BOXART_MAX_BYTES = old_max
check("T3. bo khi anh qua nang", ok3 is False and "nang" in str(err3), "%.2fs | %s" % (dt3, err3))

# T4: URL rong
ok4, err4 = bs.download_image_to_file("", out)
check("T4. URL rong tra ve False", ok4 is False, err4)

srv.shutdown()
print("OK: het test timeout anh bia" if ok else "CO LOI")
sys.exit(0 if ok else 1)
