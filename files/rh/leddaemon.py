# -*- coding: utf-8 -*-
"""Vong lap ve khung hinh cua den LED.

Chay nen, doc led.json, ghi mau vao sysfs 30 lan moi giay. Logic nam o day chu
khong o led_daemon.py de test import duoc nhu moi module khac.

Doc lai file cau hinh moi 1/10 giay. Do la toan bo co che live preview - man
hinh chon theme ghi led.json khi con tro di chuyen, va den doi trong khoang
mot phan muoi giay. Khong can IPC rieng.

Man hinh tat thi den cung tat: nguoi dung tat man hinh la de tiet kiem pin toi
da, den sang luc do chi lam nong may vo ich. Trong luc do daemon khong ghi
sysfs mot dong nao, chi con mot nhip thuc moi DARK_POLL giay de biet luc nao
man hinh bat lai."""

import os
import signal
import time

from . import backlight, led, ledconf, ledfx

FPS = 30
_CONFIG_POLL = 0.1

# Bao lau hoi lai trang thai man hinh mot lan. Khong the hoi moi khung hinh
# (them mot lan doc sysfs 30 lan moi giay chi de biet man hinh van dang sang),
# va cung khong the hoi thua: do tre nay la thoi gian den con sang sau khi
# nguoi dung tat man hinh.
DARK_POLL = 0.4

# Do tren Brick Pro that (buoc 0): effect_rgb_hex_<zone> mot minh KHONG lam gi.
# Phai ghi effect_<zone>=4 ngay sau de kich hoat - dung nhu dong
# "(effect_x for a trigger of effect start)" trong file help cua driver.
# 14 luot ghi moi khung hinh tren 7 vung, do duoc 3.35 ms, tuc 10% ngan sach
# cua mot khung 33 ms. Dat False thi den dung yen mot mau.
WRITE_EFFECT_EVERY_FRAME = True


def frame(zones, t, p):
    """Mau cua tung vung tai thoi diem t. Ham thuan, khong dung phan cung."""
    return dict((z, ledfx.render(p["effect"], t, led.zone_pos(z), p["colors"],
                                 p["speed"], p["brightness"]))
                for z in zones)


def _wake(zones, root):
    """Mo lai cong tran do sang va chot effect cho tung vung.

    Goi khi man hinh bat lai sau khi da tat den: all_off() da ha cac cong tran
    do sang xuong 0, khong keo len lai thi den khong sang du mau da ghi (tren
    phan cung that, mau mot minh khong co tac dung - xem led.all_off)."""
    for z in zones:
        led.set_effect(z, led.EFFECT_STATIC, root=root)
    led.set_max_scale(255, root=root)

class Watcher:
    """Giu config hien tai, nap lai khi noi dung doi.

    Doc thang file moi lan hoi chu KHONG so mtime. The nho la FAT hoac exFAT
    (rh/storage.py:4) va mtime tren vfat chi min toi HAI GIAY: hai lan ghi roi
    vao cung mot o hai giay la khong phan biet duoc, ma man hinh chon bo mau
    ghi lai moi lan con tro nhich - tuc gan nhu moi lan ghi deu roi vao cung
    mot o. So (mtime, size) cung khong du: doi tu "fire" sang "soft" khong
    doi mot byte nao ve kich thuoc.

    Cai gia that su cua viec doc: ~120 byte, 10 lan moi giay. Vai chuc micro
    giay, re hon nhieu so voi mot bo mau bi bo qua ma khong ai hieu tai sao."""

    def __init__(self, path):
        self.path = path
        self.cfg = ledconf.load(path)

    def changed(self):
        cfg = ledconf.load(self.path)
        if cfg == self.cfg:
            return False
        self.cfg = cfg
        return True


def run(config_path=ledconf.CONFIG_PATH, root=led.SYSFS, stop=None, screen_off=None):
    """Vong lap chinh. `stop` la callable tra ve True de ket thuc.

    `screen_off` la callable tra ve True khi man hinh dang tat; mac dinh la
    backlight.screen_is_off, truyen vao de test duoc tren cay sysfs gia
    (_src/selftest_led.py).

    Tra quyen dung lai cho nguoi goi de test chay duoc mot so khung hinh huu
    han; ban that truyen vao mot co do trinh xu ly SIGTERM dat."""
    if stop is None:
        stop = lambda: False
    if screen_off is None:
        screen_off = backlight.screen_is_off

    w = Watcher(config_path)

    # Doc cau hinh TRUOC khi cham vao phan cung. Ban cu dat effect cho moi vung
    # roi keo max_scale len 255 roi moi hoi enabled, nen tren mot may da tat
    # tien ich, hook khoi dong lam den cua firmware sang HON muc nguoi dung dat,
    # sau do daemon ngoi quay vong lap ghi mau den vinh vien - ma mau den khong
    # kem chot effect thi khong toi duoc phan cung, tuc no cham ma khong lam gi.
    if not w.cfg.get("enabled"):
        led.off_and_restore(root=root)
        return

    zones = led.detect_zones(root)
    # Chup lai cac cong tran do sang truoc khi mo het: chung la gia tri cua
    # nguoi dung (do duoc 21 tren firmware goc) va phai duoc tra lai luc thoat.
    saved_scales = led.read_scales(root)
    for z in zones:
        led.set_effect(z, led.EFFECT_STATIC, root=root)
    # Do sang xu ly bang phan mem trong ledfx.render, nen phan cung mo het co.
    # 255 chu khong phai 100: tran max_scale khac nhau theo may (110 tren Brick
    # Pro, 60 tren tg5040 theo file help), de kernel tu kep ve tran cua no.
    led.set_max_scale(255, root=root)

    t0 = time.monotonic()
    last_poll = 0.0
    last_screen = 0.0
    screen_dark = False          # luc khoi dong da mo het den (xem phia tren)
    period = 1.0 / FPS

    try:
        while not stop():
            now = time.monotonic()

            # Man hinh tat => tat den va khong ghi sysfs nua.
            if now - last_screen >= DARK_POLL:
                last_screen = now
                dark = bool(screen_off())
                if dark != screen_dark:
                    if dark:
                        led.all_off(root=root)
                    else:
                        _wake(zones, root)
                    screen_dark = dark
            if screen_dark:
                # Chi con mot viec: nguoi dung tat tinh nang trong app thi phai
                # thoat, chu khong ngu mai o day.
                if w.changed() and not w.cfg.get("enabled"):
                    break
                time.sleep(DARK_POLL)
                continue

            if now - last_poll >= _CONFIG_POLL:
                last_poll = now
                if w.changed() and not w.cfg.get("enabled"):
                    # Tat trong luc dang chay: thoat han thay vi quay vong lap
                    # ghi mau den. App bat lai bang ledctl.start(), va mot
                    # daemon khong con viec gi thi khong nen con song.
                    break
                # Dat lai tran do sang moi lan hoi. May cam tay ngu roi thuc
                # lien tuc; neu co gi do (firmware, mot .pak khac) dat lai cac
                # cong nay ve 0 thi ban cu se ghi mau vao mot do sang bang
                # khong mai mai ma khong he biet. Bay lan ghi moi 1/10 giay.
                led.set_max_scale(255, root=root)

            p = ledconf.params(w.cfg)
            for z, rgb in frame(zones, now - t0, p).items():
                led.set_color(z, rgb, root=root)
                if WRITE_EFFECT_EVERY_FRAME:
                    led.set_effect(z, led.EFFECT_STATIC, root=root)

            slack = period - (time.monotonic() - now)
            if slack > 0:
                time.sleep(slack)
    finally:
        led.all_off(root=root)
        # Tra lai cac cong tran cho firmware. Khong dung off_and_restore() o
        # day: luc nay gia tri dang co la 255 do chinh vong lap tren vua ghi,
        # nen phai la ban chup lay TU TRUOC khi mo het.
        led.write_scales(saved_scales, root=root)


def main():
    # Mot ban duy nhat. Hai daemon cung ve se ghi cung mot sysfs 30 lan moi
    # giay voi hai moc t0 khac nhau: den giat, va hieu ung quet co hai cham
    # chay lech pha. Ban thu hai con khong tat duoc tu giao dien, vi pidfile
    # chi giu duoc mot pid - nguoi dung phai khoi dong lai may.
    #
    # Kiem tra o day chu khong chi o phia app: hook khoi dong la duong vao thu
    # hai va no khong hoi gi ca, nen mo mot .pak roi bam bat trong app la du
    # de co hai ban chay.
    if ledconf.running_pid(ledconf.PID_PATH) is not None:
        return 0

    running = {"go": True}

    def bye(_sig, _frm):
        running["go"] = False

    signal.signal(signal.SIGTERM, bye)
    signal.signal(signal.SIGINT, bye)

    try:
        with open(ledconf.PID_PATH, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass

    try:
        run(stop=lambda: not running["go"])
    finally:
        try:
            os.remove(ledconf.PID_PATH)
        except OSError:
            pass
    return 0
