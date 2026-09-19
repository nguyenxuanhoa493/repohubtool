# -*- coding: utf-8 -*-
"""Selftest cho daemon LED: man hinh tat thi den tat va khong ghi sysfs nua.

    python _src/selftest_led.py

Khong can may cam tay, khong can SDL2: dung mot cay sysfs gia giong
/sys/class/led_anim (xem rh/led.py) va mot led.json gia.

  T1  man hinh sang -> daemon ve khung hinh, mau khac den
  T2  tat man hinh  -> den tat (mau den + cac cong tran do sang = 0) va
      KHONG con ghi sysfs (tiet kiem pin toi da)
  T3  bat man hinh lai -> mo lai cong tran va ve tiep
  T4  khi daemon thoat -> tra lai cac cong tran cho firmware (ban chup luc dau)
  T5  daemon khoi dong luc man hinh dang tat -> khong ghi khung hinh nao
"""

import io
import os
import sys
import tempfile
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")
SD = tempfile.mkdtemp(prefix="rh-led-")
os.environ["SDCARD_PATH"] = SD
sys.path.insert(0, FILES)
sys.path.insert(0, os.path.join(FILES, "vendor"))

from rh import led, ledconf, leddaemon, ledthemes

ok = True

def check(name, cond, detail=""):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + name + ((" | " + str(detail)) if detail else ""))
    if not cond:
        ok = False

ZONES = ("f1", "f2")
SCALES = ("max_scale", "max_scale_f1f2")

def make_led_root():
    root = tempfile.mkdtemp(prefix="rh-ledsys-")
    for z in ZONES:
        for name in ("effect_rgb_hex_%s" % z, "effect_%s" % z):
            with io.open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write("0")
    for name in SCALES:                       # gia tri CUA NGUOI DUNG (do that: 21)
        with io.open(os.path.join(root, name), "w", encoding="utf-8") as f:
            f.write("21")
    return root

def read(root, name):
    with io.open(os.path.join(root, name), "r", encoding="utf-8") as f:
        return f.read().strip()

def make_config(enabled=True):
    path = os.path.join(tempfile.mkdtemp(prefix="rh-ledcfg-"), "led.json")
    ledconf.save({"enabled": enabled, "theme": ledthemes.DEFAULT_ID,
                  "brightness": 60, "speed": 1.0, "boot": False}, path)
    return path

def start_daemon(root, cfg, screen, go):
    writes = {"n": 0}
    real_write = led._write
    def counting(path, text):
        writes["n"] += 1
        return real_write(path, text)
    led._write = counting
    th = threading.Thread(target=leddaemon.run,
                          kwargs=dict(config_path=cfg, root=root, stop=lambda: not go[0],
                                      screen_off=lambda: screen["off"]),
                          daemon=True)
    th.start()
    return th, writes

def stop_daemon(th, writes):
    led._write = real_write_holder["fn"]
    th.join(timeout=5.0)

# luu lai de tra ve sau khi test xong
real_write_holder = {"fn": led._write}

# ---------------------------------------------------------------------------
# T1-T4: mot phien daemon, doi trang thai man hinh
# ---------------------------------------------------------------------------
root = make_led_root()
cfg = make_config(True)
screen = {"off": False}
go = [True]
th, writes = start_daemon(root, cfg, screen, go)

time.sleep(0.8)
colors_on = [read(root, "effect_rgb_hex_%s" % z) for z in ZONES]
check("T1. man hinh sang -> daemon ghi mau (khac den)", writes["n"] > 0 and any(c != "000000" for c in colors_on),
      "writes=%d mau=%s" % (writes["n"], colors_on))

screen["off"] = True
time.sleep(1.0)
colors_off = [read(root, "effect_rgb_hex_%s" % z) for z in ZONES]
scales_off = [read(root, s) for s in SCALES]
check("T2a. tat man hinh -> den tat het",
      all(c == "000000" for c in colors_off), "mau=%s" % colors_off)
check("T2b. tat man hinh -> cac cong tran do sang ve 0 (den khong an dong)",
      all(v == "0" for v in scales_off), "cong tran=%s" % scales_off)
writes["n"] = 0
time.sleep(1.2)
check("T2c. tat man hinh -> KHONG con ghi sysfs (tiet kiem pin)",
      writes["n"] == 0, "writes=%d trong 1.2s" % writes["n"])

screen["off"] = False
time.sleep(1.0)
colors_back = [read(root, "effect_rgb_hex_%s" % z) for z in ZONES]
scales_back = [read(root, s) for s in SCALES]
check("T3a. bat man hinh lai -> den sang lai", any(c != "000000" for c in colors_back),
      "mau=%s" % colors_back)
check("T3b. bat man hinh lai -> mo lai cong tran do sang",
      all(v != "0" for v in scales_back), "cong tran=%s" % scales_back)
check("T3c. bat man hinh lai -> ve tiep khung hinh", writes["n"] > 0, "writes=%d" % writes["n"])

go[0] = False
th.join(timeout=5.0)
led._write = real_write_holder["fn"]
check("T4. daemon thoat -> tra lai cong tran cho firmware (21) va tat den",
      read(root, "max_scale") == "21" and read(root, "max_scale_f1f2") == "21"
      and read(root, "effect_rgb_hex_f1") == "000000",
      "cong tran=%s" % [read(root, s) for s in SCALES])

# ---------------------------------------------------------------------------
# T5: khoi dong khi man hinh dang tat
# ---------------------------------------------------------------------------
root2 = make_led_root()
cfg2 = make_config(True)
screen2 = {"off": True}
go2 = [True]
th2, writes2 = start_daemon(root2, cfg2, screen2, go2)
time.sleep(1.0)
writes2["n"] = 0
time.sleep(1.0)
check("T5. khoi dong luc man hinh tat -> khong ve khung hinh nao",
      writes2["n"] == 0 and read(root2, "effect_rgb_hex_f1") == "000000",
      "writes=%d" % writes2["n"])
go2[0] = False
th2.join(timeout=5.0)
led._write = real_write_holder["fn"]

print("OK: het selftest LED" if ok else "CO LOI")
sys.exit(0 if ok else 1)
