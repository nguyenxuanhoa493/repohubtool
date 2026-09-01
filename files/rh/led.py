# -*- coding: utf-8 -*-
"""Tang phan cung cua den LED: boc /sys/class/led_anim.

Module la - khong import gi tu rh. Day la noi duy nhat trong ca tien ich biet
duong dan sysfs ton tai, nen thay doi ve phan cung chi cham vao mot file.

Hai dieu de sai va sai thi im lang:

- Mau ghi vao sysfs la sau chu so hex VIET HOA, KHONG co tien to 0x. File
  ledsettings.txt cua NextUI viet color1=0x440044 nhung do la format cua file
  cau hinh, khong phai cua kernel; chuoi format that nam trong ledcontrol.elf
  la "%06X".
- Moi thao tac ghi nuot loi. May thieu mot vung, the hong, hay chay test tren
  macOS deu phai thanh khong-lam-gi chu khong duoc nem.
- Do sang khong phai mot cong ma NHIEU: ngoai `max_scale` toan cuc con co cong
  theo nhom vung. Chi mo mot cai la ba phan tu may sang o muc khac han phan
  con lai, va khong co gi tren man hinh giai thich."""

import os

SYSFS = "/sys/class/led_anim"

# So hieu ung firmware. Ta dat Static roi tu ve tung khung hinh bang cach ghi
# mau; cac so con lai (Breathe, Rainbow...) la animation do firmware chay, tien
# ich nay khong dung toi.
EFFECT_STATIC = 4

_PREFIX = "effect_rgb_hex_"

# Cong tran do sang. Co mot file toan cuc `max_scale` va - do duoc tren Brick
# Pro that - them cac cong theo NHOM vung: max_scale_f1f2, max_scale_lr,
# max_scale_rear. Ten nhom khong trung ten vung, nen khong suy ra duoc tu
# detect_zones(); phai liet ke bang sysfs giong het cach detect_zones() lam.
_SCALE = "max_scale"

# Vi tri khong gian 0.0 (trai) -> 1.0 (phai). Hieu ung song va quet doc so nay
# de cac vung lech pha nhau. Firmware khong co khai niem tuong duong: moi vung
# chay animation doc lap, nen khong bao gio co song chay qua than may.
ZONE_POS = {
    "f1": 0.0,
    "l": 0.15,
    "m": 0.5, "lr": 0.5, "rear": 0.5,
    "r": 0.85,
    "f2": 1.0,
}
DEFAULT_POS = 0.5


def zone_pos(zone):
    """Vi tri 0.0..1.0 cua mot vung. Vung la roi vao giua."""
    return ZONE_POS.get(zone, DEFAULT_POS)


def detect_zones(root=SYSFS):
    """Danh sach vung LED may nay that su co, sap trai sang phai.

    Do bang sysfs chu khong doan theo ten may: script boot cua NextUI phai
    parse `strings /usr/trimui/bin/MainUI` de biet Brick hay Brick Pro, con
    cach nay dung tren ca ba may va may doi sau moc them vung thi tu nhan."""
    try:
        names = os.listdir(root)
    except OSError:
        return []
    zones = [n[len(_PREFIX):] for n in names if n.startswith(_PREFIX)]
    return sorted(zones, key=lambda z: (zone_pos(z), z))


def _write(path, text):
    # sysfs khong cho tao file moi bang open() - cac file thuoc tinh la co san
    # do kernel bay ra. Kiem tra ton tai truoc khi ghi de mo phong dung dieu
    # do tren mot thu muc gia (vd tmp_path trong test), noi open() se am tham
    # tao file thay vi bao loi nhu sysfs that.
    if not os.path.exists(path):
        return False
    try:
        with open(path, "w") as f:
            f.write(text)
        return True
    except OSError:
        return False


def set_effect(zone, n, root=SYSFS):
    return _write(os.path.join(root, "effect_%s" % zone), str(int(n)))


def set_color(zone, rgb, root=SYSFS):
    r, g, b = (max(0, min(255, int(c))) for c in rgb)
    return _write(os.path.join(root, _PREFIX + zone),
                  "%06X" % ((r << 16) | (g << 8) | b))


def detect_scales(root=SYSFS):
    """Moi cong tran do sang may nay that su co, ke ca cong theo nhom.

    Do bang sysfs chu khong hard-code danh sach, cung ly do voi detect_zones():
    may doi sau chia nhom khac di thi tu nhan.

    Vi sao khong chi mo mot file `max_scale`: do bang tay tren Brick Pro that,
    ba cong nhom dung o 21 trong khi cong toan cuc la 80, nen den truoc, cum
    vai va den sau chi sang khoang 19% con moi dai giua sang het. Ghi 255 vao
    tung cong moi keo tat ca len cung mot muc (doc lai ra 110)."""
    try:
        names = os.listdir(root)
    except OSError:
        return []
    return sorted(n for n in names
                  if n == _SCALE or n.startswith(_SCALE + "_"))


def read_scales(root=SYSFS):
    """Gia tri hien tai cua tung cong tran, de con tra lai duoc.

    Nhung gia tri nay la CUA NGUOI DUNG, khong phai cua ta: tren firmware goc
    do duoc la 21. Daemon mo het len 255 luc chay va all_off() ha ve 0 luc
    thoat; khong ai chep lai truoc thi den cua chinh firmware toi han cho toi
    lan khoi dong lai may, va khong co gi tren man hinh giai thich tai sao.

    Bo qua file doc khong ra so: sysfs that luon tra ve mot so, con thu muc
    gia trong test thi co the rong."""
    out = {}
    for name in detect_scales(root):
        try:
            with open(os.path.join(root, name), "r") as f:
                raw = f.read().strip()
        except OSError:
            continue
        if raw.isdigit():
            out[name] = raw
    return out


def write_scales(values, root=SYSFS):
    """Ghi tra lai nhung gi read_scales() da chep."""
    for name, raw in (values or {}).items():
        _write(os.path.join(root, name), str(raw))


def set_max_scale(raw, root=SYSFS):
    """Dat MOI cong tran do sang. `raw` la gia tri THO cua kernel, khong phai %.

    Thang khong phai 0..100: do tren Brick Pro that thi ghi 255 doc lai ra 110,
    va file `help` cua driver ghi "[0 ~ tg5040 limit brightness 60]" - tran khac
    nhau theo may. Nen ta ghi 255 va de kernel tu kep ve tran cua no, thay vi
    hard-code mot con so se sai tren mot nua so may.

    Do sang nguoi dung chinh duoc xu ly bang phan mem trong ledfx.render()."""
    text = str(max(0, min(255, int(raw))))
    ok = False
    for name in detect_scales(root):
        if _write(os.path.join(root, name), text):
            ok = True
    return ok


def all_off(root=SYSFS):
    """Tat sach. Goi khi tat tien ich va khi daemon nhan SIGTERM.

    Mau den mot minh khong du: ghi effect_rgb_hex_<zone> ma khong chot bang
    effect_<zone>=4 la mot lenh khong-lam-gi tren phan cung that, du thu muc
    sysfs gia trong test co ghi nhan du. Nen moi vung deu duoc chot lai sau
    khi to den, roi ha het cac cong tran xuong 0 lam lop chan thu hai.

    Cac cong tran o lai 0 sau khi ham nay chay: nguoi goi phai tra lai gia tri
    cu (xem read_scales/write_scales) neu may con dung den sau do."""
    for z in detect_zones(root):
        set_color(z, (0, 0, 0), root=root)
        set_effect(z, EFFECT_STATIC, root=root)
    set_max_scale(0, root=root)


def off_and_restore(root=SYSFS):
    """Tat den nhung tra lai cac cong tran cho firmware.

    Danh cho phia app, noi khong co ban chup luc khoi dong de ma khoi phuc:
    doc gia tri dang co, tat, roi ghi lai chinh no. Daemon KHONG dung ham nay
    - luc no thoat, gia tri dang co la 255 do chinh no ghi, nen no phai dung
    ban chup lay tu truoc khi mo het."""
    saved = read_scales(root)
    all_off(root=root)
    write_scales(saved, root=root)
