# -*- coding: utf-8 -*-
"""Bat tat daemon LED va cai go hook khoi dong.

Chi app goi module nay; daemon khong. Nen no duoc phep nang hon rh/leddaemon.py
- import paths, chay subprocess, doc /proc."""

import os
import signal
import subprocess
import time

from . import led, ledconf
from .paths import APP_DIR, SDCARD_PATH

HOOK_NAME = "retrohub-led.sh"
PROC_ROOT = "/proc"

# Firmware TrimUI goc chay moi *.sh trong thu muc nay luc khoi dong
# (runtrimui-original.sh, vong `for f in $SDCARD_START_SCRIPTS_DIR/*.sh`).
# Khong can dung toi NAND.
STOCK_STARTS_DIR = os.path.join(SDCARD_PATH, "System", "starts")

# Bao lau sau start() thi moi duoc ket luan "bat ma khong chay". Daemon phai
# qua launch.sh - tim Python, doi khi tai ve - roi moi ghi pidfile, nen ngay
# sau start() thi is_running() con la False mot cach hoan toan binh thuong.
# Khong co khoang an nay, chi can nguoi dung bam bat roi thoat va mo lai man
# hinh LED du nhanh la reconcile() se ket luan nham va tat dung cai vua bat.
START_GRACE = 8.0
_started_at = [None]


def userdata_dir():
    """Thu muc .userdata cua NextUI cho may nay.

    PLATFORM la tg5040 tren ca Brick lan Brick Pro - script boot cua NextUI
    dung chung mot ten cho ca ho may nay."""
    base = os.environ.get("USERDATA_PATH")
    if not base:
        plat = os.environ.get("PLATFORM", "tg5040")
        base = os.path.join(SDCARD_PATH, ".userdata", plat)
    return base


def hook_kind():
    """Co che hook may nay dung, hoac None neu khong co cai nao.

    NextUI duoc uu tien: neu may co ca hai thi no dang chay NextUI, va
    .hooks/boot.d la duong chinh chu.

    Ca hai co che chi quyet dinh GHI FILE HOOK VAO DAU, khong lien quan gi
    toi ai dang tranh sysfs voi daemon. Boot script cua NextUI tu tat
    lcservice (`/etc/init.d/lcservice disable`) va xoa `/etc/LedControl`,
    nen tren may NextUI khong con tien trinh nao dung sysfs ngoai daemon
    cua ta. Tren firmware goc thi khac: `lcservice` - dich vu LED goc cua
    firmware - van con song va se tranh (ghi de) sysfs voi daemon, dung
    nhu firmware tu gianh lai max_scale luc man hinh tat (xem
    rh/leddaemon.py). Day la ly do daemon phai LUI thay vi gianh khi thay
    mot gia tri la, thay vi gia dinh minh la nguoi ghi duy nhat."""
    if os.path.isdir(userdata_dir()):
        return "nextui"
    if os.path.isdir(STOCK_STARTS_DIR):
        return "stock"
    return None


def hook_dir():
    if hook_kind() == "stock":
        return STOCK_STARTS_DIR
    return os.path.join(userdata_dir(), ".hooks", "boot.d")


def hook_path():
    return os.path.join(hook_dir(), HOOK_NAME)


def hook_supported():
    return hook_kind() is not None


def hook_body(app_dir):
    """Than script dung chung cho ca hai co che.

    Firmware goc chay cac script nay DONG BO - khong co `&` trong vong lap
    cua no - nen script phai tu day xuong nen va tra quyen ngay. Mot script
    chay lau o day se chan boot, va nguoi dung chi thay may dung o man hinh
    khoi dong. NextUI thi chay nen san, nhung `&` o day cung khong hai gi,
    nen mot than script duy nhat phuc vu ca hai."""
    return (
        "#!/bin/sh\n"
        "# RetroHub - tu chay den LED sau khi khoi dong. Xoa file nay de tat.\n"
        'APP="%s"\n'
        '[ -f "$APP/led_daemon.py" ] || exit 0\n'
        '"$APP/launch.sh" --led-daemon </dev/null >/dev/null 2>&1 &\n'
        "exit 0\n"
    ) % app_dir


def hook_installed():
    return os.path.exists(hook_path())


def install_hook():
    p = hook_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(hook_body(APP_DIR))
    except OSError:
        return False
    # chmod tach rieng va nuot loi: exfat-fuse tu choi chmod - dieu nay duoc
    # ghi lai o bon cho khac trong kho (rh/storage.py:34, rh/neterrors.py:23,
    # rh/updater.py:68, rh/downloader.py:662). Gop no vao khoi tren nghia la
    # hook DA nam tren dia va se chay moi lan khoi dong, trong khi ham nay bao
    # that bai: cong tac tren man hinh o lai TAT, va lan bam sau lai goi
    # install_hook() mot lan nua chu khong phai remove_hook() - nguoi dung
    # khong bao gio tat duoc no.
    #
    # Su that ve "da cai hay chua" la file co ton tai khong, va do la thu
    # hook_installed() tra loi.
    try:
        os.chmod(p, 0o755)
    except OSError:
        pass
    return True


def _both_hook_paths():
    # hook_path() dua vao hook_dir(), noi install_hook() thuc su ghi file -
    # ke ca khi mot cai goi da tu thay hook_dir() (test, hay mot co che khac
    # trong tuong lai). Neu remove_hook chi tinh thang tu userdata_dir()/
    # STOCK_STARTS_DIR ma bo qua duong nay thi no co the khong xoa duoc dung
    # cho ma install_hook() vua ghi. Loai trung de khong thu xoa mot duong
    # dan hai lan mot cach vo ich.
    paths = [os.path.join(userdata_dir(), ".hooks", "boot.d", HOOK_NAME),
             os.path.join(STOCK_STARTS_DIR, HOOK_NAME),
             hook_path()]
    return list(dict.fromkeys(paths))


def remove_hook():
    """Xoa o CA HAI cho. Doi firmware khong duoc de lai mot hook mo coi van
    chay moi lan khoi dong ma giao dien khong con nhin thay de tat."""
    ok = True
    for p in _both_hook_paths():
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
        except OSError:
            ok = False
    return ok


def _pid_is_ours(pid):
    # Logic that nam o ledconf.pid_alive: daemon cung phai hoi cau nay de tu
    # choi chay ban thu hai, ma daemon khong duoc import module nay.
    return ledconf.pid_alive(pid)


def is_running(pid_path=ledconf.PID_PATH):
    pid = ledconf.read_pid(pid_path)
    return pid is not None and _pid_is_ours(pid)


def start():
    if is_running():
        return True
    launcher = os.path.join(APP_DIR, "launch.sh")
    _started_at[0] = time.monotonic()
    try:
        # stdin/stdout/stderr deu DEVNULL va close_fds=True: giong het cach
        # rh/services.py:104 tha streamer.py, de daemon khong giu ria mot fd
        # ke thua tu app ma song lau hon app.
        subprocess.Popen(["sh", launcher, "--led-daemon"],
                         cwd=APP_DIR,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         close_fds=True,
                         start_new_session=True)
        return True
    except OSError:
        return False


def stop():
    """Tat daemon, va tat den bang duoc.

    Duong khong-co-daemon (pidfile mat, file rac, hay pid gio la cua tien trinh
    khac) khong duoc phep chi tra ve True roi thoi: app se ghi enabled=False,
    man hinh noi TAT, con den van sang - va tu trong app khong con nut nao tat
    duoc no nua, vi lan bam sau se la BAT. Xay ra that moi khi daemon bi
    kill -9, hay khi no chua kip ghi pidfile.

    Nen o duong do ta tu tat lay. all_off() ha ca cac cong tran do sang xuong
    0, ma do la gia tri cua nguoi dung (21 tren firmware goc), nen dung ban
    off_and_restore() de tra lai."""
    # Tat roi thi khoang an sau start() khong con nghia gi: khong xoa thi bam
    # bat roi bam tat trong vong 8 giay se lam reconcile() tuong daemon dang
    # len va bat lai cong tac.
    _started_at[0] = None
    pid = ledconf.read_pid(ledconf.PID_PATH)
    if pid is None or not _pid_is_ours(pid):
        led.off_and_restore()
        return True
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    return True


def restart():
    """Khoi dong lai daemon de chac chan nap code va hieu ung moi nhat."""
    stop()
    time.sleep(0.15)
    return start()


def conflicting_daemon(root=PROC_ROOT):
    """LedControl.pak cua NextUI dang chay se tranh sysfs, den nhay loan.

    Tham so root de test tro vao mot cay /proc gia, giong root=SYSFS o
    rh/led.py - khong dung toi /proc that trong unit test."""
    try:
        entries = os.listdir(root)
    except OSError:
        return False
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(os.path.join(root, entry, "cmdline"), "rb") as f:
                if b"ledcontrol.elf" in f.read():
                    return True
        except OSError:
            continue
    return False


def reconcile(cfg, path=ledconf.CONFIG_PATH):
    """Cho cai file noi khop voi cai dang that su xay ra, truoc khi ve man hinh.

    Ba kieu lech, ca ba deu ket thuc bang mot cong tac noi doi:

    - File noi BAT ma khong co daemon. Tren firmware goc khong he co tu chay
      khi khoi dong (co y nhu vay), nen sau moi lan khoi dong lai may thi day
      la trang thai binh thuong: cong tac hien BAT, den tat, bam mot cai thanh
      TAT va khong co gi xay ra. Ta tat den cho sach roi ghi enabled=False.
    - File noi TAT ma daemon van chay (ai do chay tay, hay hook da chay).
    - File noi boot=True/False khong khop voi viec hook co that su nam tren dia
      hay khong - de xay ra vi exfat-fuse tu choi chmod, xem install_hook().

    Tra ve cfg da sua. Ghi lai file neu co gi doi, va lang le neu ghi hong:
    day la buoc dong bo luc mo man hinh, khong phai mot hanh dong nguoi dung
    yeu cau, nen mot toast o day chi lam nguoi ta hoang mang."""
    cfg = dict(cfg or {})
    dirty = False

    running = is_running()
    if (not running and cfg.get("enabled") and _started_at[0] is not None
            and time.monotonic() - _started_at[0] < START_GRACE):
        # Vua tha daemon xong, no chua kip ghi pidfile. Chua ket luan duoc gi.
        # Chi noi rong theo mot chieu - giu nguyen cai dang BAT - chu khong bao
        # gio tu bat len, de khoang an nay khong the tu no sinh ra trang thai.
        running = True
    if bool(cfg.get("enabled")) != running:
        cfg["enabled"] = running
        dirty = True
        if not running:
            led.off_and_restore()

    if hook_supported():
        installed = hook_installed()
        if bool(cfg.get("boot")) != installed:
            cfg["boot"] = installed
            dirty = True

    if dirty:
        ledconf.save(cfg, path)
    return cfg
