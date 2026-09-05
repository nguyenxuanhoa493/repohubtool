# -*- coding: utf-8 -*-
"""Bang theme dung san cho den LED.

Mot theme la mot goi: hieu ung nao, mau nao, nhanh cham the nao, sang bao
nhieu. Them theme moi la them mot dict o day - khong dung toi engine, khong
dung toi giao dien, khong dung toi daemon.

`speed` va `brightness` trong theme la gia tri KHOI DIEM. Nguoi dung chinh tay
thi gia tri chinh tay ghi de va luu vao led.json, cho toi khi doi theme lan
nua. Xem ledconf.apply_theme."""

DEFAULT_ID = "retrohub"

THEMES = [
    {"id": "retrohub", "vi": "Tím RetroHub", "en": "RetroHub Purple",
     "effect": "breathe", "colors": [(0x88, 0x00, 0xCC)],
     "speed": 1.0, "brightness": 60},

    {"id": "rave", "vi": "Vũ trường EDM", "en": "EDM Rave",
     "effect": "strobe", "colors": [(0xFF, 0x00, 0x80), (0x00, 0xE5, 0xFF)],
     "speed": 1.3, "brightness": 85},

    {"id": "bass_drop", "vi": "Bass Drop", "en": "Bass Drop",
     "effect": "pulse_bass", "colors": [(0x39, 0xFF, 0x14), (0x4B, 0x00, 0x82)],
     "speed": 1.2, "brightness": 80},

    {"id": "thunder", "vi": "Bão sấm sét", "en": "Thunderstorm",
     "effect": "lightning", "colors": [(0xE0, 0xF0, 0xFF), (0x2A, 0x00, 0x60)],
     "speed": 1.1, "brightness": 85},

    {"id": "glitch", "vi": "Cyber Glitch", "en": "Cyber Glitch",
     "effect": "chaos", "colors": [(0x00, 0xFF, 0xCC), (0xFF, 0x00, 0x7F),
                                   (0xFF, 0xEE, 0x00)],
     "speed": 1.2, "brightness": 85},

    {"id": "drift", "vi": "Đua xe Drift", "en": "Night Drift",
     "effect": "hyper_chase", "colors": [(0xFF, 0xD7, 0x00), (0xFF, 0x22, 0x00)],
     "speed": 1.3, "brightness": 85},

    {"id": "red_alert", "vi": "Báo động đỏ", "en": "Red Alert",
     "effect": "strobe", "colors": [(0xFF, 0x00, 0x00), (0x40, 0x00, 0x00)],
     "speed": 1.4, "brightness": 90},

    {"id": "supernova", "vi": "Siêu tân tinh", "en": "Supernova",
     "effect": "pulse_bass", "colors": [(0xFF, 0x55, 0x00), (0xFF, 0xFF, 0xE0)],
     "speed": 1.3, "brightness": 90},

    {"id": "cyber", "vi": "Cyberpunk", "en": "Cyberpunk",
     "effect": "wave", "colors": [(0xFF, 0x00, 0x66), (0x00, 0xE5, 0xFF)],
     "speed": 1.0, "brightness": 70},

    {"id": "wave_ocean", "vi": "Đại dương", "en": "Ocean",
     "effect": "wave", "colors": [(0x00, 0x66, 0xFF), (0x00, 0x20, 0x60)],
     "speed": 0.7, "brightness": 55},

    {"id": "forest", "vi": "Rừng sâu", "en": "Deep Forest",
     "effect": "fade", "colors": [(0x0A, 0x60, 0x20), (0x40, 0xC0, 0x30),
                                  (0x00, 0x40, 0x40)],
     "speed": 0.6, "brightness": 50},

    {"id": "sunset", "vi": "Hoàng hôn", "en": "Sunset",
     "effect": "fade", "colors": [(0xFF, 0x50, 0x00), (0xFF, 0x00, 0x60),
                                  (0x60, 0x00, 0x90)],
     "speed": 0.5, "brightness": 65},

    {"id": "fire", "vi": "Lửa trại", "en": "Campfire",
     "effect": "fire", "colors": [(0xFF, 0x90, 0x00), (0x50, 0x08, 0x00)],
     "speed": 1.0, "brightness": 70},

    {"id": "matrix", "vi": "Ma trận", "en": "Matrix",
     "effect": "twinkle", "colors": [(0x00, 0xFF, 0x41)],
     "speed": 1.2, "brightness": 60},

    {"id": "rainbow", "vi": "Cầu vồng", "en": "Rainbow",
     "effect": "rainbow", "colors": [(0xFF, 0xFF, 0xFF)],
     "speed": 1.0, "brightness": 65},

    {"id": "police", "vi": "Cảnh sát", "en": "Police",
     "effect": "police", "colors": [(0xFF, 0x00, 0x00), (0x00, 0x40, 0xFF)],
     "speed": 1.0, "brightness": 85},

    {"id": "knight", "vi": "Quét đỏ", "en": "Red Scanner",
     "effect": "scanner", "colors": [(0xFF, 0x10, 0x00)],
     "speed": 1.0, "brightness": 80},

    {"id": "gameboy", "vi": "Game Boy", "en": "Game Boy",
     "effect": "heartbeat", "colors": [(0x9B, 0xBC, 0x0F)],
     "speed": 0.8, "brightness": 55},

    {"id": "soft", "vi": "Trắng dịu", "en": "Soft White",
     "effect": "solid", "colors": [(0xFF, 0xE8, 0xC0)],
     "speed": 1.0, "brightness": 35},
]

_BY_ID = dict((th["id"], th) for th in THEMES)


def get(theme_id):
    # theme_id den tu file led.json tren the nho - bat ky thu gi cung co the
    # ghi vao do (list, dict, so...). dict.get() doc thi "toan" nhung khong
    # phai: key khong hashable (list, dict) lam no nem TypeError chu khong
    # tra ve None. Bat lai o day, noi duy nhat can biet chuyen tra cuu nay,
    # de get() luon la mot ham an toan cho moi noi goi no.
    try:
        return _BY_ID.get(theme_id)
    except TypeError:
        return None


def name(theme_id, lang="VI"):
    th = get(theme_id)
    if not th:
        return str(theme_id)
    return th["vi"] if lang == "VI" else th["en"]
