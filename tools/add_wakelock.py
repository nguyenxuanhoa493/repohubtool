with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add imports at the top
old_imports = """import os
import sys
import re
import time
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
import threading"""

new_imports = """import os
import sys
import re
import time
import json
import shutil
import signal
import atexit
import subprocess
import urllib.request
import urllib.parse
import threading"""

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    print("Added signal/atexit imports!")

# 2. Add Wakelock helper functions before run_server
old_run = """def run_server():
  server_address = ("0.0.0.0", PORT)
  httpd = ThreadedHTTPServer(server_address, GameWebHandler)
  print(f"[*] RetroHub Web Game Manager running at http://0.0.0.0:{PORT}")
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    httpd.server_close()"""

wakelock_code = """# ==================== TRIMUI SMART PRO WAKELOCK ====================
ORIG_DIMTIME = None

def get_current_dimtime():
    try:
        res = subprocess.run(["/usr/trimui/bin/systemval", "dimtime"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            val = res.stdout.strip()
            if val.isdigit() and int(val) > 0:
                return int(val)
    except Exception:
        pass
    return 300

def set_dimtime(val):
    try:
        subprocess.run(["/usr/trimui/bin/systemval", "dimtime", str(val)], timeout=2)
    except Exception:
        pass

def enable_wakelock():
    global ORIG_DIMTIME
    ORIG_DIMTIME = get_current_dimtime()
    set_dimtime(0)
    print(f"[*] [Wakelock] Disabled auto-sleep (saved original dimtime: {ORIG_DIMTIME}s)")

def disable_wakelock():
    global ORIG_DIMTIME
    val = ORIG_DIMTIME if (ORIG_DIMTIME and ORIG_DIMTIME > 0) else 300
    set_dimtime(val)
    print(f"[*] [Wakelock] Restored original dimtime: {val}s")

atexit.register(disable_wakelock)

def _sig_handler(sig, frame):
    disable_wakelock()
    sys.exit(0)

signal.signal(signal.SIGTERM, _sig_handler)
signal.signal(signal.SIGINT, _sig_handler)

def _keepalive_daemon():
    while True:
        try:
            set_dimtime(0)
            time.sleep(60)
        except Exception:
            time.sleep(60)

_keepalive_thread = threading.Thread(target=_keepalive_daemon, daemon=True)
_keepalive_thread.start()


def run_server():
  enable_wakelock()
  server_address = ("0.0.0.0", PORT)
  httpd = ThreadedHTTPServer(server_address, GameWebHandler)
  print(f"[*] RetroHub Web Game Manager running at http://0.0.0.0:{PORT}")
  try:
    httpd.serve_forever()
  except (KeyboardInterrupt, SystemExit):
    pass
  finally:
    disable_wakelock()
    httpd.server_close()"""

if old_run in content:
    content = content.replace(old_run, wakelock_code)
    print("Added Wakelock code and updated run_server!")
else:
    print("Could not find old_run!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Finished wakelock injection!")
