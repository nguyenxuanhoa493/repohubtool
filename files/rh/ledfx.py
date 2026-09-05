# -*- coding: utf-8 -*-
"""Engine hieu ung LED: ham thuan tinh mau tu thoi gian va vi tri vung.

Chu ky f(t, pos, colors, speed) -> (r, g, b). Khong doc dong ho, khong giu
trang thai, khong dung phan cung. Hai he qua: test duoc bang cach goi ham, va
them mot hieu ung moi chi la them mot ham cong mot dong trong EFFECTS.

`pos` la vi tri khong gian cua vung, 0.0 ben trai den 1.0 ben phai. No la thu
firmware khong co: firmware chi co 8 hieu ung dong dang (disable, linear,
breath, sniff, static, blink1-3), va moi vung chay hieu ung do doc lap voi
nhau, nen khong bao gio lech pha duoc. Hai hieu ung `wave` va `scanner` o day
ton tai chinh vi dieu do."""

import math


def _clamp8(v):
    return max(0, min(255, int(round(v))))


def _scale(rgb, k):
    return (_clamp8(rgb[0] * k), _clamp8(rgb[1] * k), _clamp8(rgb[2] * k))


def _lerp(a, b, k):
    return (_clamp8(a[0] + (b[0] - a[0]) * k),
            _clamp8(a[1] + (b[1] - a[1]) * k),
            _clamp8(a[2] + (b[2] - a[2]) * k))


def _second(colors, fallback):
    return colors[1] if len(colors) > 1 else fallback


def _noise(a, b):
    """Nhieu tat dinh trong [0, 1).

    Thay cho random() vi hai ly do. Test: cung dau vao phai cho cung mau. Va
    thi giac: mot seed dung chung se lam moi vung loe sang cung mot nhip, nhin
    nhu den hong chu khong nhu lap lanh."""
    x = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return x - math.floor(x)


def hsv_to_rgb(h, s, v):
    h = h - math.floor(h)
    i = int(h * 6.0) % 6
    f = h * 6.0 - int(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    u = v * (1.0 - (1.0 - f) * s)
    r, g, b = ((v, u, p), (q, v, p), (p, v, u),
               (p, q, v), (u, p, v), (v, p, q))[i]
    return (_clamp8(r * 255), _clamp8(g * 255), _clamp8(b * 255))


def solid(t, pos, colors, speed):
    return colors[0]


def breathe(t, pos, colors, speed):
    # Cosin chu khong phai sin: t=0 la sang nhat. Bat den len ma toi thui trong
    # nua giay dau doc nhu den hong.
    k = 0.12 + 0.88 * (0.5 + 0.5 * math.cos(2.0 * math.pi * 0.25 * speed * t))
    return _scale(colors[0], k)


def _beat(ph, center, width=0.09):
    d = abs(ph - center)
    return max(0.0, 1.0 - d / width)


def heartbeat(t, pos, colors, speed):
    period = 1.2 / speed
    ph = (t % period) / period
    k = min(1.0, 0.06 + _beat(ph, 0.0) + _beat(ph, 0.20))
    return _scale(colors[0], k)


def rainbow(t, pos, colors, speed):
    return hsv_to_rgb(0.1 * speed * t, 1.0, 1.0)


def wave(t, pos, colors, speed):
    # pos vao thang trong pha: song di tu trai sang phai qua than may.
    k = 0.5 + 0.5 * math.cos(2.0 * math.pi * (0.3 * speed * t - pos))
    return _lerp(_second(colors, (0, 0, 0)), colors[0], k)


def fade(t, pos, colors, speed):
    n = len(colors)
    if n < 2:
        return colors[0]
    x = (0.2 * speed * t) % n
    i = int(x)
    return _lerp(colors[i], colors[(i + 1) % n], x - i)


def twinkle(t, pos, colors, speed):
    step = 0.25 / speed
    slot = math.floor(t / step)
    frac = (t / step) - slot
    k = _noise(slot, pos * 7.0 + 1.0) * max(0.0, 1.0 - frac)
    return _scale(colors[0], 0.04 + 0.96 * k)


def fire(t, pos, colors, speed):
    # Lay mau nhieu theo buoc 1/8 giay roi noi mem, de ngon lua bap bung chu
    # khong ru rau tung khung hinh.
    x = t * 8.0 * speed
    lo = math.floor(x)
    a = _noise(lo, pos * 3.0 + 2.0)
    b = _noise(lo + 1, pos * 3.0 + 2.0)
    k = 0.40 + 0.60 * (a + (b - a) * (x - lo))
    return _lerp(_second(colors, (40, 0, 0)), colors[0], k)


def police(t, pos, colors, speed):
    period = 0.6 / speed
    left_turn = (t % period) < (period / 2.0)
    if pos > 0.5:
        left_turn = not left_turn
    col = colors[0] if left_turn else _second(colors, (0, 0, 255))
    # Nhay hai nhip trong moi nua chu ky, giong den canh sat that.
    half = period / 2.0
    on = ((t % half) / half) < 0.65
    return _scale(col, 1.0 if on else 0.0)


def scanner(t, pos, colors, speed):
    # Diem sang chay tu trai sang phai roi quay ve. Binh phuong k de dinh sang
    # gon lai thanh mot diem thay vi mot vung mo.
    period = 2.0 / speed
    x = (t % period) / period
    head = 1.0 - abs(2.0 * x - 1.0)
    k = max(0.0, 1.0 - abs(pos - head) / 0.45)
    return _scale(colors[0], 0.03 + 0.97 * k * k)


def strobe(t, pos, colors, speed):
    # Chop giat vu truong (Rave Strobe): xung chop ruc sang, doi mau luan phien
    # giua trai va phai, kem nen nang luong de khong bao gio toi han.
    period = 0.38 / speed
    cycle = (t % period) / period
    is_left = pos < 0.5
    # May 1 vung hoac vung giua (pos == 0.5) doi nhip theo chu ky
    side_active = (cycle < 0.5) if (pos < 0.45) else ((cycle >= 0.5) if (pos > 0.55) else True)
    sub = (cycle * 2.0) % 1.0
    # Xung chop kep ro rang, du rong de 30 FPS luon bat duoc (khoang 70ms moi xung)
    flash = (sub < 0.36) or (0.52 <= sub < 0.88)

    c1 = colors[0]
    c2 = _second(colors, colors[0])
    base_col = c1 if (cycle < 0.5) else c2
    if not side_active:
        return _scale(base_col, 0.15)
    col = c1 if is_left else c2
    if flash:
        return _lerp(col, (255, 255, 255), 0.55)
    return _scale(col, 0.18)


def lightning(t, pos, colors, speed):
    # Sam set giong bao: nen may giang van vu (20-30% sang) bat ngo no chum tia chop xe toac.
    period = 1.3 / speed
    cycle_idx = math.floor(t / period)
    local_t = t - cycle_idx * period

    # Nen may giong bao luon sang nhe, bop nhip tho dien tu
    cloud_k = 0.20 + 0.10 * (0.5 + 0.5 * math.sin(t * 3.5 + pos * 2.0))
    bg_col = _second(colors, (50, 10, 100))
    bg = _scale(bg_col, cloud_k)

    # Thoi diem set danh trong chu ky
    strike_at = 0.25 + 0.65 * _noise(cycle_idx, 19.0)
    sweep_dir = _noise(cycle_idx, 7.0) > 0.5
    p = pos if sweep_dir else (1.0 - pos)
    dt = local_t - (strike_at + p * 0.08)

    # Chum 3 tia chop sang trang gat keo dai ~300ms
    flash = 0.0
    if 0.0 <= dt < 0.35:
        if dt < 0.08:
            flash = 0.95
        elif 0.10 <= dt < 0.17:
            flash = 0.75
        elif 0.19 <= dt < 0.32:
            flash = 1.0

    if flash > 0.0:
        bolt_col = _lerp(colors[0], (255, 255, 255), 0.85 if flash > 0.8 else 0.5)
        return _lerp(bg, bolt_col, flash)
    return bg


def pulse_bass(t, pos, colors, speed):
    # Dap Bass EDM: soc dien loa sieu tram tu tam lan toa ra hai mep, nen bass am luon dap.
    bpm_period = 0.48 / speed
    phase = (t % bpm_period) / bpm_period

    dist = abs(pos - 0.5) * 2.0
    shock_pos = phase * 1.4
    hit = max(0.0, 1.0 - abs(dist - shock_pos) / 0.4)

    # Luc dap bass dan hoi (dan deu ~250ms)
    punch = max(0.0, 1.0 - phase * 1.8) ** 1.5
    k = min(1.0, punch * 0.75 + hit * 0.65)

    # Nen bass tram khong tat
    bg_k = 0.18 + 0.08 * (0.5 + 0.5 * math.cos(2.0 * math.pi * phase))
    bg = _scale(_second(colors, (30, 0, 60)), bg_k)

    kick_col = colors[0]
    if punch > 0.6 and hit > 0.5:
        kick_col = _lerp(kick_col, (255, 255, 255), 0.35)
    return _lerp(bg, kick_col, k)


def hyper_chase(t, pos, colors, speed):
    # Vet duoi sieu toc: sao bang ruc lua quet qua than may voi duoi lua ruc chay.
    period = 0.58 / speed
    head = (t % period) / period

    dist = (head - pos) % 1.0
    tail = max(0.0, 1.0 - dist / 0.75) ** 1.6
    head_burst = 1.0 if dist < 0.10 else 0.0

    col_tail = _second(colors, (255, 40, 0))
    col_head = colors[0]
    c = _lerp(col_tail, col_head, tail)
    if head_burst:
        c = _lerp(c, (255, 255, 255), 0.70)
    k = max(0.15, tail)
    return _scale(c, k)


def chaos(t, pos, colors, speed):
    # Cyber Glitch: loan nhip cyberpunk toc do cao, phoi mau da sac ruc ro khong bao gio toi.
    fps = 9.0 * speed
    slot = math.floor(t * fps)
    sub = (t * fps) - slot

    n1 = _noise(slot, pos * 13.0 + 2.7)
    n2 = _noise(slot + 31, pos * 7.0 + 5.1)

    n_col = len(colors)
    col_idx = int((n1 * n_col + pos * 1.5) % n_col)
    c = colors[col_idx]

    # Nhip glitch giat cuc bo
    stutter = 1.0 if (sub < 0.45 or n2 > 0.6) else 0.45
    if n1 > 0.82:
        c = _lerp(c, (255, 255, 255), 0.75)

    brightness = max(0.25, 0.45 + 0.55 * stutter)
    return _scale(c, brightness)


EFFECTS = {
    "solid": solid,
    "breathe": breathe,
    "heartbeat": heartbeat,
    "rainbow": rainbow,
    "wave": wave,
    "fade": fade,
    "twinkle": twinkle,
    "fire": fire,
    "police": police,
    "scanner": scanner,
    "strobe": strobe,
    "lightning": lightning,
    "pulse_bass": pulse_bass,
    "hyper_chase": hyper_chase,
    "chaos": chaos,
}

# Suy ra chu khong chep tay: hai danh sach nhac lai cung mot thu, va chi can
# them mot hieu ung vao mot ben roi quen ben kia thi khong bai test nao do -
# hieu ung moi don gian la khong bao gio duoc kiem tra. dict giu nguyen thu tu
# them tu Python 3.7, va thu tu o day la thu tu hien thi.
EFFECT_IDS = list(EFFECTS)


def render(effect_id, t, pos, colors, speed=1.0, brightness=100):
    """Mau cua mot vung tai mot thoi diem, da ap do sang.

    Do sang ap bang phan mem chu khong qua max_scale cua kernel: mot cho chinh
    do sang thay vi hai, va brightness=0 chac chan ra den tuyet doi."""
    fn = EFFECTS.get(effect_id, solid)
    if not colors:
        colors = [(255, 255, 255)]
    rgb = fn(float(t), float(pos), colors, max(0.05, float(speed)))
    b = max(0, min(100, int(brightness)))
    if b >= 100:
        return (_clamp8(rgb[0]), _clamp8(rgb[1]), _clamp8(rgb[2]))
    return _scale(rgb, b / 100.0)
