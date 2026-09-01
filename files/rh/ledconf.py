# -*- coding: utf-8 -*-
"""File cau hinh led.json: duong day duy nhat giua man hinh cai dat va daemon.

Nam o $SDCARD/.retrohub/, ngoai thu muc app, cung cho voi ban chay Python ma
launch.sh tai ve - va cung mot ly do: cai lai hay cap nhat RetroHub khong duoc
xoa mat lua chon cua nguoi dung.

Khong co IPC nao khac. App ghi file, daemon theo doi mtime va nap lai. Nen ghi
phai nguyen tu (.tmp roi rename), va doc phai chiu duoc file hong: daemon hoan
toan co the doc trung luc app dang ghi do, va mot file cut duoi khong duoc bien
thanh cai may co den chet."""

import json
import os

from . import ledthemes

CONFIG_DIR = "/mnt/SDCARD/.retrohub"
CONFIG_PATH = os.path.join(CONFIG_DIR, "led.json")
PID_PATH = os.path.join(CONFIG_DIR, "led.pid")
PROC_ROOT = "/proc"

DEFAULTS = {
    "enabled": False,
    "theme": ledthemes.DEFAULT_ID,
    "brightness": 60,
    "speed": 1.0,
    "boot": False,
}

# Toc do luu dang HE SO NHAN voi toc do goc cua theme, khong phai gia tri tuyet
# doi. Nho vay "Nhanh" co nghia nhu nhau o moi theme.
SPEEDS = [0.5, 1.0, 2.0]
_SPEED_NAMES = {0.5: "slow", 1.0: "normal", 2.0: "fast"}


def speed_name(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 1.0
    nearest = min(SPEEDS, key=lambda s: abs(s - v))
    return _SPEED_NAMES[nearest]


def cycle_speed(v, step):
    """Sang buoc toc do ke tiep. Dung o hai bien chu khong vong lai."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 1.0
    nearest = min(SPEEDS, key=lambda s: abs(s - v))
    i = SPEEDS.index(nearest) + (1 if step > 0 else -1)
    return SPEEDS[max(0, min(len(SPEEDS) - 1, i))]


def load(path=CONFIG_PATH):
    cfg = dict(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return cfg
    if not isinstance(raw, dict):
        return cfg

    cfg["enabled"] = bool(raw.get("enabled", cfg["enabled"]))
    cfg["boot"] = bool(raw.get("boot", cfg["boot"]))

    theme = raw.get("theme", cfg["theme"])
    cfg["theme"] = theme if ledthemes.get(theme) else ledthemes.DEFAULT_ID

    try:
        cfg["brightness"] = max(0, min(100, int(raw.get("brightness", cfg["brightness"]))))
    except (TypeError, ValueError):
        pass
    try:
        s = float(raw.get("speed", cfg["speed"]))
        cfg["speed"] = s if s > 0 else DEFAULTS["speed"]
    except (TypeError, ValueError):
        pass
    return cfg


def save(cfg, path=CONFIG_PATH):
    tmp = path + ".tmp"
    try:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def params(cfg):
    """Tham so ve mot khung hinh: hieu ung, mau, toc do, do sang."""
    cfg = cfg or {}
    th = ledthemes.get(cfg.get("theme")) or ledthemes.get(ledthemes.DEFAULT_ID)
    try:
        mult = float(cfg.get("speed", 1.0))
    except (TypeError, ValueError):
        mult = 1.0
    if mult <= 0:
        mult = 1.0
    try:
        bright = max(0, min(100, int(cfg.get("brightness", th["brightness"]))))
    except (TypeError, ValueError):
        bright = th["brightness"]
    return {"effect": th["effect"], "colors": th["colors"],
            "speed": th["speed"] * mult, "brightness": bright}


def apply_theme(cfg, theme_id):
    """Doi theme, keo theo toc do va do sang ve gia tri goc cua theme moi.

    Giu lai do sang 10% tu theme truoc se lam theme moi trong nhu khong chay,
    va nguoi dung khong noi duoc tai sao."""
    th = ledthemes.get(theme_id)
    out = dict(cfg or DEFAULTS)
    if not th:
        return out
    out["theme"] = theme_id
    out["brightness"] = th["brightness"]
    out["speed"] = 1.0
    return out


# --- Nhan dang tien trinh daemon -------------------------------------------
#
# Ba ham duoi day nam o module nay chu khong o rh/ledctl.py vi CA HAI phia deu
# can chung: app hoi de ve cong tac bat/tat, con chinh daemon hoi de tu choi
# chay ban thu hai. ledconf la la chung ma ca hai da import; nguoc lai thi
# daemon se phai keo theo ledctl - tuc keo theo subprocess va duong dan app -
# vao mot tien trinh nen dang le chi can doc ghi mot file va mot thu muc sysfs.


def pid_alive(pid, proc_root=PROC_ROOT):
    """Pid nay co dang la mot daemon LED khong.

    HAI dieu kien chu khong mot: /proc/<pid> ton tai VA cmdline co chuoi
    "led_daemon". Pid quay vong tren Linux, nen chi kiem tra su ton tai la du
    de mot pidfile cu tro nham vao mot tien trinh khong lien quan - va tu do
    tien ich tu choi khoi dong vi tuong daemon con song, mai mai.

    proc_root de test tro vao mot cay /proc gia, giong root=SYSFS o rh/led.py."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    d = os.path.join(proc_root, str(pid))
    if not os.path.isdir(d):
        return False
    try:
        with open(os.path.join(d, "cmdline"), "rb") as f:
            return b"led_daemon" in f.read()
    except OSError:
        return False


def read_pid(path=PID_PATH):
    """So trong pidfile, hay None neu khong co file / file rac."""
    try:
        with open(path, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def running_pid(path=PID_PATH, proc_root=PROC_ROOT):
    """Pid cua daemon dang song, hay None. Khong bao gio nem."""
    pid = read_pid(path)
    if pid is not None and pid_alive(pid, proc_root):
        return pid
    return None
