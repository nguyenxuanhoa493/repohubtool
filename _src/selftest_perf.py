# -*- coding: utf-8 -*-
"""Selftest hieu nang cho hai hot path da do trong plans/bao-cao-hieu-nang.md.

    python _src/selftest_perf.py

Khong can SDL2, khong can mang, khong can may cam tay:

  T1  image_path() khong duoc quet lai thu muc ROM cho moi lan goi. Man Library
      goi ham nay cho tung o anh bia, moi khung hinh, nen mot lan quet thu muc
      la mot lan stat toan bo file trong Roms/<he> - do tren may that la 25-28
      lan moi giay chi de tim ten file anh.

  T2  Nhan dien "man hinh da tat" phai doc du fb1/blank, bl_power va
      brightness, khong chi fb0/blank: co may TrimUI tat den bang node khac,
      va khi do vong lap chinh van ve 25-28 khung/giay trong khi nguoi dung
      da tat may (nong may, ton pin).
"""

import os
import sys
import tempfile
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SD = tempfile.mkdtemp(prefix="rh-perf-")
os.environ["SDCARD_PATH"] = SD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")
sys.path.insert(0, FILES)
sys.path.insert(0, os.path.join(FILES, "vendor"))

ok = True

def check(name, cond, detail=""):
    global ok
    print(("  PASS  " if cond else "  FAIL  ") + name + ((" | " + str(detail)) if detail else ""))
    if not cond:
        ok = False

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

# ---------------------------------------------------------------------------
# T1: khong quet thu muc trong image_path()
# ---------------------------------------------------------------------------
gba = os.path.join(SD, "Roms", "GBA")
os.makedirs(gba, exist_ok=True)
for i in range(300):
    write(os.path.join(gba, "Game_%04d.gba" % i), "")
os.makedirs(os.path.join(SD, "Imgs", "GBA"), exist_ok=True)

from rh import installed

names = ["Game_%04d.gba" % i for i in range(300)]
installed.image_path("GBA", names[0])          # lam nong cache

calls = {"listdir": 0, "scandir": 0, "isdir": 0, "exists": 0}
_ol, _os_, _oi, _oe = os.listdir, os.scandir, os.path.isdir, os.path.exists
def l(p, *a, **k):
    calls["listdir"] += 1; return _ol(p, *a, **k)
def s(p, *a, **k):
    calls["scandir"] += 1; return _os_(p, *a, **k)
def i(p):
    calls["isdir"] += 1; return _oi(p)
def e(p):
    calls["exists"] += 1; return _oe(p)
os.listdir, os.scandir, os.path.isdir, os.path.exists = l, s, i, e
try:
    N = 50
    t0 = time.perf_counter()
    for k in range(N):
        installed.image_path("GBA", names[k])
    dt = time.perf_counter() - t0
finally:
    os.listdir, os.scandir, os.path.isdir, os.path.exists = _ol, _os_, _oi, _oe

scans = calls["listdir"] + calls["scandir"] + calls["isdir"]
check("T1.1 image_path khong quet thu muc moi lan goi (<= 5 luot quet cho ca 50 goi)",
      scans <= 5, "quet=%d (listdir=%d scandir=%d isdir=%d) exists=%d, %.2f ms/goi"
      % (scans, calls["listdir"], calls["scandir"], calls["isdir"], calls["exists"],
         dt / N * 1000))
check("T1.2 moi goi chi con vai lan stat file anh", calls["exists"] / N <= 8,
      "%.1f exists/goi" % (calls["exists"] / N))

# Anh moi them vao Imgs/ phai duoc thay ngay (khong bi cache thu muc lam ket)
img = os.path.join(SD, "Imgs", "GBA", "Game_0007.png")
installed.image_path("GBA", names[7])          # truoc khi co anh
write(img, "x")
found = installed.image_path("GBA", names[7])
# base_key() ha ten file xuong chu thuong, nen so ten khong phan biet hoa thuong
# (the FAT cua may cam tay cung khong phan biet hoa thuong).
check("T1.3 anh bia moi them duoc thay ngay",
      found and os.path.basename(found).lower() == "game_0007.png", found)

installed.invalidate()
t0 = time.perf_counter()
installed.image_path("GBA", names[8])
dt = time.perf_counter() - t0
check("T1.4 invalidate() lam moi lai (khong tra cache cu)", dt < 0.5, "%.1f ms" % (dt * 1000))

# ---------------------------------------------------------------------------
# T2: nhan dien man hinh da tat
# ---------------------------------------------------------------------------
from rh import backlight

def fake_sysfs(fb0="0", fb1=None, bl_power=None, brightness=None, max_brightness="255"):
    root = tempfile.mkdtemp(prefix="rh-sysfs-")
    if fb0 is not None:
        write(os.path.join(root, "sys", "class", "graphics", "fb0", "blank"), fb0)
    if fb1 is not None:
        write(os.path.join(root, "sys", "class", "graphics", "fb1", "blank"), fb1)
    if bl_power is not None:
        write(os.path.join(root, "sys", "class", "backlight", "pwm", "bl_power"), bl_power)
    if brightness is not None:
        write(os.path.join(root, "sys", "class", "backlight", "pwm", "brightness"), brightness)
        write(os.path.join(root, "sys", "class", "backlight", "pwm", "max_brightness"), max_brightness)
    return root

check("T2.1 fb0/blank=1 -> tat",
      backlight.screen_is_off(fake_sysfs(fb0="1")) is True)
check("T2.2 fb0=0, fb1/blank=1 -> tat (node fb1 bi bo qua truoc day)",
      backlight.screen_is_off(fake_sysfs(fb0="0", fb1="1")) is True)
check("T2.3 bl_power=1, khong co blank -> tat (nhieu may TrimUI tat den kieu nay)",
      backlight.screen_is_off(fake_sysfs(fb0=None, bl_power="1")) is True)
check("T2.4 brightness=0 (max 255) -> tat",
      backlight.screen_is_off(fake_sysfs(fb0=None, brightness="0")) is True)
check("T2.5 brightness=120 -> van sang",
      backlight.screen_is_off(fake_sysfs(fb0="0", brightness="120")) is False)
check("T2.6 khong co node nao -> coi nhu dang sang (khong tu ngu sai)",
      backlight.screen_is_off(tempfile.mkdtemp(prefix="rh-sysfs-none-")) is False)
check("T2.7 fb0=4 (blank khac 0) -> tat",
      backlight.screen_is_off(fake_sysfs(fb0="4")) is True)

# T2.8+: may TrimUI Brick that (do tren 192.168.1.12, Allwinner sun50iw10) KHONG
# co /sys/class/backlight va fb0/blank rong; tin hieu nam o fb0/state va
# /sys/class/disp/disp/attr/sys ("unblank"/"blank" + "backlight( 72)").
def fake_disp(text, fb_state=None):
    root = tempfile.mkdtemp(prefix="rh-sysfs-disp-")
    write(os.path.join(root, "sys", "class", "disp", "disp", "attr", "sys"), text)
    if fb_state is not None:
        write(os.path.join(root, "sys", "class", "graphics", "fb0", "state"), fb_state)
        write(os.path.join(root, "sys", "class", "graphics", "fb0", "blank"), "")
    return root

SYS_ON = ("screen 0:\nde_rate 300000000 hz, ref_fps:60\n"
          "\tmgr0: 1024x768 fmt[rgb] unblank direct_show[false]\n"
          "\tlcd output\tbacklight( 72)\tfps:60.6\t1024x 768\n")
SYS_BLANK = SYS_ON.replace("unblank", "blank")
SYS_BL_ZERO = SYS_ON.replace("backlight( 72)", "backlight(  0)")

check("T2.8 fb0/state=1 (man hinh tat tren driver moi) -> tat",
      backlight.screen_is_off(fake_disp(SYS_ON, fb_state="1")) is True)
check("T2.9 disp attr bao blank -> tat",
      backlight.screen_is_off(fake_disp(SYS_BLANK)) is True)
check("T2.10 disp attr bao unblank + backlight 72 -> dang sang",
      backlight.screen_is_off(fake_disp(SYS_ON)) is False)
check("T2.11 disp attr bao unblank nhung backlight 0 -> tat",
      backlight.screen_is_off(fake_disp(SYS_BL_ZERO)) is True)

# ---------------------------------------------------------------------------
# T3: engine dung chung phep kiem tra do va khong doc sysfs moi khung hinh
# ---------------------------------------------------------------------------
try:
    from rh import engine as rh_engine
except Exception as exc:                                    # thieu SDL2 thi bo qua
    print("  SKIP  T3. khong import duoc rh.engine (%s)" % exc)
else:
    seen = {"n": 0}
    real = rh_engine.backlight.screen_is_off
    def spy(root="/"):
        seen["n"] += 1
        return True
    rh_engine.backlight.screen_is_off = spy
    try:
        got = [rh_engine.is_screen_blanked() for _ in range(50)]
    finally:
        rh_engine.backlight.screen_is_off = real
    check("T3.1 is_screen_blanked() uy quyen cho backlight.screen_is_off",
          got and all(g is True for g in got))
    check("T3.2 doc sysfs co cache (50 vong lap -> <= 2 lan doc)",
          seen["n"] <= 2, "doc=%d lan" % seen["n"])

    # T5: chi ve khi co gi doi
    def rd(**kw):
        base = dict(has_input=False, since_activity=5.0, modal_active=False,
                    toast_active=False, download_active=False,
                    screen_name="home", since_redraw=0.05)
        base.update(kw)
        return rh_engine.needs_redraw(**base)

    check("T5.1 man hinh tinh, vua ve xong -> khong ve lai", rd() is False)
    check("T5.2 qua nhip ranh -> ve lai dinh ky", rd(since_redraw=0.3) is True)
    check("T5.3 co input -> ve", rd(has_input=True) is True)
    check("T5.4 vua co input (0.2s) -> con ve cho kip trang thai", rd(since_activity=0.2) is True)
    check("T5.5 modal dang mo -> ve", rd(modal_active=True) is True)
    check("T5.6 toast dang hien -> ve", rd(toast_active=True) is True)
    check("T5.7 dang tai -> ve", rd(download_active=True) is True)
    check("T5.8 keyboard nhay con tro -> luon ve", rd(screen_name="keyboard") is True)
    check("T5.9 emu_store nhip thanh tien trinh -> luon ve", rd(screen_name="emu_store") is True)
    check("T5.10 library ranh -> khong ve", rd(screen_name="library") is False)

# ---------------------------------------------------------------------------
# T4: vong render cua man Library khong doc the (nho cache anh bia)
# ---------------------------------------------------------------------------
try:
    from rh.screens.library import LibraryScreen
except Exception as exc:
    print("  SKIP  T4. khong import duoc LibraryScreen (%s)" % exc)
else:
    names4 = ["Game_%04d.gba" % i for i in range(6)]
    for nm in names4:
        write(os.path.join(SD, "Imgs", "GBA", os.path.splitext(nm)[0] + ".png"), "x")

    class StubEngine:
        active_modal = None
        def __getattr__(self, name):        # moi font_* deu la None
            if name.startswith("font_"):
                return None
            raise AttributeError(name)
        def fill_rect(self, *a, **k): pass
        def draw_rect(self, *a, **k): pass
        def draw_text(self, *a, **k): return 0
        def measure_text(self, *a, **k): return 10
        def wrap_text_to_width(self, *a, **k): return ["x"]
        def draw_proportional_boxart(self, *a, **k): return True
        def draw_default_boxart_avatar(self, *a, **k): return True

    screen = LibraryScreen(None)
    screen.system_tabs = ["ALL"]
    screen.current_tab_idx = 0
    screen.selected_idx = 0
    screen.scroll_row = 0
    screen.filtered_games = [{"sys_code": "GBA", "filename": nm, "title": "G%d" % i}
                             for i, nm in enumerate(names4)]

    fs = {"n": 0}
    _oe4, _ol4, _os4, _oi4, _ostat = os.path.exists, os.listdir, os.scandir, os.path.isdir, os.stat
    def e4(p):
        fs["n"] += 1; return _oe4(p)
    def l4(p, *a, **k):
        fs["n"] += 1; return _ol4(p, *a, **k)
    def s4(p, *a, **k):
        fs["n"] += 1; return _os4(p, *a, **k)
    def i4(p):
        fs["n"] += 1; return _oi4(p)
    def st4(*a, **k):
        fs["n"] += 1; return _ostat(*a, **k)
    os.path.exists, os.listdir, os.scandir, os.path.isdir, os.stat = e4, l4, s4, i4, st4
    try:
        screen.render(StubEngine())              # lan dau: nap cache anh bia
        fs["n"] = 0
        for _ in range(10):
            screen.render(StubEngine())
        warm = fs["n"]
        open_modal_engine = StubEngine()
        open_modal_engine.active_modal = object()   # modal dang mo
        screen.render(open_modal_engine)
        fs["n"] = 0
        screen.render(StubEngine())                 # modal vua dong: phai tim lai anh
        after_close = fs["n"]
        fs["n"] = 0
        screen.render(StubEngine())                 # khung tiep theo: lai khong doc the
        steady = fs["n"]
    finally:
        os.path.exists, os.listdir, os.scandir, os.path.isdir, os.stat = _oe4, _ol4, _os4, _oi4, _ostat

    check("T4.1 10 khung render Library khong doc the (0 syscall FS)", warm == 0,
          "syscall=%d" % warm)
    check("T4.2 khung dau sau khi dong modal co tim lai anh (thay anh vua tai)",
          after_close > 0, "syscall=%d" % after_close)
    check("T4.3 khung tiep theo lai khong doc the", steady == 0, "syscall=%d" % steady)

# ---------------------------------------------------------------------------
# T6: vong lap that (SDL dummy) - ranh thi it ve, co viec thi ve ngay
# ---------------------------------------------------------------------------
try:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import ctypes
    import threading
    import sdl2
    from rh import state as rh_state
    from rh import engine as rh_engine2
    from rh.screens.base import BaseScreen
except Exception as exc:
    print("  SKIP  T6. khong dung duoc SDL2 (%s)" % exc)
else:
    class CountingScreen(BaseScreen):
        def __init__(self):
            super().__init__(None)
            self.renders = 0
            self.last_render_at = 0.0
            self.dts = []
            self.lock = threading.Lock()
        def update(self, dt):
            with self.lock:
                self.dts.append(dt)
        def get_header_title(self):
            return "Test"
        def get_footer_actions(self):
            return []
        def render(self, engine):
            with self.lock:
                self.renders += 1
                self.last_render_at = time.time()

    class StubModal:
        def __init__(self):
            self.active = True
            self.engine = None
        def open(self, data=None):
            self.active = True
        def close(self):
            self.active = False
        def is_active(self):
            return self.active
        def handle_input(self, inputs):
            return True
        def update(self, dt):
            pass
        def render(self, engine):
            pass

    rh_state.auto_update = False
    eng = rh_engine2.RetroHubEngine()
    eng.init_sdl()
    if not eng.init_fonts():
        print("  SKIP  T6. khong nap duoc font")
    else:
        screen = CountingScreen()
        eng.register_screen("home", screen)
        th = threading.Thread(target=eng.run, daemon=True)
        th.start()
        time.sleep(2.0)                     # on dinh sau khi khoi dong
        with screen.lock:
            idle_start = screen.renders
        t0 = time.time()
        time.sleep(1.5)
        idle = screen.renders - idle_start
        idle_rate = idle / (time.time() - t0)

        # 1. Ranh: vai khung/giay, khong phai 25-28
        check("T6.1 man hinh tinh khi ranh chi ve vai khung/giay (<= 12)",
              idle_rate <= 12, "%.1f khung/giay (%d khung/1.5s)" % (idle_rate, idle))

        # 1b. dt phai la thoi gian that giua hai vong lap. Ban cu truyen cung
        # 0.016 trong khi che do ranh ngu 0.035s, nen moi thu tich luy theo dt
        # (hoat anh, dong ho) chay sai nhip khoang 2 lan.
        with screen.lock:
            dts = list(screen.dts)
        check("T6.5 dt la thoi gian that (co nhip ranh ~0.035s, khong phai 0.016 co dinh)",
              dts and max(dts) >= 0.02 and min(dts) > 0 and max(dts) <= 0.3,
              "min=%.3f max=%.3f (%d mau)" % (min(dts), max(dts), len(dts)))

        # 2. Toast dang hien thi phai ve lai lien tuc
        with screen.lock:
            n0 = screen.renders
        eng.toast("test", duration=1.2)
        time.sleep(1.0)
        with screen.lock:
            toast_renders = screen.renders - n0
        check("T6.2 co toast -> ve lai lien tuc (>= 15 khung/giay)",
              toast_renders / 1.0 >= 15, "%d khung/1.0s" % toast_renders)

        # 3. Modal dang mo phai ve lai lien tuc (tien trinh, spinner)
        time.sleep(1.0)
        with screen.lock:
            n1 = screen.renders
        eng.open_modal(StubModal())
        time.sleep(1.0)
        with screen.lock:
            modal_renders = screen.renders - n1
        check("T6.3 modal dang mo -> ve lai lien tuc (>= 15 khung/giay)",
              modal_renders / 1.0 >= 15, "%d khung/1.0s" % modal_renders)
        eng.close_modal()

        # 4. Bam nut phai ve lai NGAY, khong doi nhip ve dinh ky cua che do ranh.
        #    SDL dummy khong nhan su kien ban phim that (SDL loc key event theo
        #    focus cua cua so), nen gia lap dung cho ma vong lap thuc su doc:
        #    input_mgr.poll() tra ve mot nut bam. Do so khung ve trong 0.15s ngay
        #    sau do: co input thi vong lap ve lai (ACTIVE_WINDOW_S), con che do
        #    ranh chi ve ~4 khung/giay.
        real_poll = eng.input_mgr.poll
        counts = []
        for _ in range(3):
            time.sleep(0.6)
            fired = {"n": 0}
            def fake_poll(*a, **k):
                fired["n"] += 1
                if fired["n"] == 1:
                    return {"btn_down": True}
                return real_poll(*a, **k)
            with screen.lock:
                n0 = screen.renders
            eng.input_mgr.poll = fake_poll
            time.sleep(0.15)
            eng.input_mgr.poll = real_poll
            with screen.lock:
                counts.append(screen.renders - n0)
        check("T6.4 bam nut -> ve lai ngay (>= 3 khung trong 0.15s, ranh chi ~0.6)",
              min(counts) >= 3, "3 lan: %s khung/0.15s" % counts)

        eng.running = False
        th.join(timeout=5.0)          # run() tu goi cleanup() khi thoat

# ---------------------------------------------------------------------------
# T7/T8: cache texture (chu va anh) khong phinh, va khong sort lai toan bo
# ---------------------------------------------------------------------------
try:
    import sdl2
    import sdl2.sdlttf as sdlttf
    from rh.ui import primitives as prim
    from rh import engine as rh_engine3
except Exception as exc:
    print("  SKIP  T7/T8. khong dung duoc SDL2 (%s)" % exc)
else:
    import base64
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
    sdlttf.TTF_Init()
    win = sdl2.SDL_CreateWindow(b"cache-test", 0, 0, 64, 64, sdl2.SDL_WINDOW_SHOWN)
    ren = sdl2.SDL_CreateRenderer(win, -1, 0)
    font_path = os.path.join(FILES, "assets", "fallback.ttf")
    try:
        font = sdlttf.TTF_OpenFont(font_path.encode("utf-8"), 16)
        # T7: vong lap UI that (20 nhan tinh + 1 chuoi dong moi khung hinh).
        # Ban cu sort toan bo cache va huy 50 texture moi lan cache day, nen moi
        # chuoi dong keo theo hang chuc nhan tinh bi ve lai. Do bang so texture
        # bi huy / tao lai, khong do bang thoi gian (may CI nhanh cham khac nhau).
        churn = {"d": 0, "c": 0}
        real_destroy = sdl2.SDL_DestroyTexture
        real_create = sdl2.SDL_CreateTextureFromSurface
        def counting_destroy(tex):
            churn["d"] += 1
            return real_destroy(tex)
        def counting_create(r, surf):
            churn["c"] += 1
            return real_create(r, surf)
        static_labels = ["label %d" % i for i in range(20)]
        try:
            sdl2.SDL_DestroyTexture = counting_destroy
            sdl2.SDL_CreateTextureFromSurface = counting_create
            cache = {}
            for label in static_labels:
                prim.draw_text(ren, label, font, 0, 0, 255, 255, 255,
                               text_texture_cache=cache, max_cache=32)
            churn["d"] = churn["c"] = 0
            for i in range(100):
                for label in static_labels:
                    prim.draw_text(ren, label, font, 0, 0, 255, 255, 255,
                                   text_texture_cache=cache, max_cache=32)
                prim.draw_text(ren, "vol %d" % i, font, 0, 0, 255, 255, 255,
                               text_texture_cache=cache, max_cache=32)
        finally:
            sdl2.SDL_DestroyTexture = real_destroy
            sdl2.SDL_CreateTextureFromSurface = real_create
        check("T7.1 nhan tinh khong bi ve lai khi co chuoi dong (huy <= 140 texture)",
              churn["d"] <= 140, "%d texture bi huy" % churn["d"])
        check("T7.2 khong tao lai texture lien tuc (tao <= 140 texture)",
              churn["c"] <= 140, "%d texture tao moi" % churn["c"])
        check("T7.3 cache van bi chan tren", len(cache) <= 32 + 32 // 4 + 1,
              "len=%d" % len(cache))

        # T8: cache anh bia co tran thap cho may 1GB, va cache anh thieu cung co tran
        eng = rh_engine3.RetroHubEngine()
        png_1px = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")
        eng.renderer = ren
        for i in range(30):
            fp = os.path.join(SD, "px%d.png" % i)
            with open(fp, "wb") as f:
                f.write(png_1px)
            eng.get_texture_and_size(fp)
        check("T8.1 cache anh bia co tran (<= %d)" % eng.MAX_IMG_CACHE,
              len(eng.img_texture_cache) <= eng.MAX_IMG_CACHE,
              "len=%d" % len(eng.img_texture_cache))
        check("T8.2 tran anh bia du nho cho may 1GB (<= 24)", eng.MAX_IMG_CACHE <= 24,
              "MAX_IMG_CACHE=%d" % eng.MAX_IMG_CACHE)
        for i in range(600):
            eng.get_texture_and_size(os.path.join(SD, "thieu", "x%d.png" % i))
        check("T8.3 cache anh thieu co tran", len(eng.missing_img_cache) <= rh_engine3.MAX_MISSING_IMG,
              "len=%d (tran %d)" % (len(eng.missing_img_cache), rh_engine3.MAX_MISSING_IMG))
    finally:
        sdlttf.TTF_Quit()
        sdl2.SDL_DestroyRenderer(ren)
        sdl2.SDL_DestroyWindow(win)

# ---------------------------------------------------------------------------
# T9: cac cache khong co tran (danh sach file libretro, token phan trang YouTube)
# ---------------------------------------------------------------------------
from rh import boxart_scraper as rh_bs
from rh import yt as rh_yt

for i in range(40):
    rh_bs._remember_index("SYS%02d#Named_Boxarts" % i, ["abc.png"] * 10)
check("T9.1 cache danh sach file libretro co tran",
      len(rh_bs._LIBRETRO_INDEX_CACHE) <= rh_bs.INDEX_CACHE_MAX,
      "len=%d tran=%d" % (len(rh_bs._LIBRETRO_INDEX_CACHE), rh_bs.INDEX_CACHE_MAX))

for i in range(80):
    rh_yt.set_continuation_token("query %d" % i, "tok%d" % i)
check("T9.2 cache token phan trang co tran",
      len(rh_yt._CONTINUATION_TOKENS) <= rh_yt.CONTINUATION_CACHE_MAX,
      "len=%d tran=%d" % (len(rh_yt._CONTINUATION_TOKENS), rh_yt.CONTINUATION_CACHE_MAX))
check("T9.3 token vua luu van dung duoc",
      rh_yt.get_continuation_token("query 79") == "tok79",
      rh_yt.get_continuation_token("query 79"))
rh_yt.set_continuation_token("query 79", "")
check("T9.4 xoa token (chuoi rong) van dung", rh_yt.get_continuation_token("query 79") == "")

# ---------------------------------------------------------------------------
# T10: khong de ket qua cu ghi de ket qua moi (doi tab nhanh / doi video nhanh)
# ---------------------------------------------------------------------------
try:
    import threading as _th
    import rh.yt as yt_mod
    from rh.screens.youtube import YoutubeScreen
    from rh.screens.watch import WatchScreen
except Exception as exc:
    print("  SKIP  T10. khong import duoc man hinh YouTube (%s)" % exc)
else:
    class StubEngine:
        def toast(self, *a, **k):
            pass

    real_search = yt_mod.search_youtube
    real_feed = yt_mod.load_feed_cache
    real_more = yt_mod.fetch_more_youtube
    real_token = yt_mod.get_continuation_token
    real_thumb = yt_mod.fetch_thumbnail
    real_meta = yt_mod.fetch_watch_metadata
    gate = _th.Event()
    thumbs = []

    def slow_search(q):
        if q == "tab-cu":
            gate.wait(3.0)
            return [{"id": "CU1", "title": "cu", "thumb": ""}]
        return [{"id": "MOI1", "title": "moi", "thumb": ""}]

    try:
        yt_mod.load_feed_cache = lambda q: (None, None)
        yt_mod.search_youtube = slow_search
        yt_mod.fetch_more_youtube = lambda q: ([], "")
        yt_mod.get_continuation_token = lambda q: ""
        yt_mod.fetch_thumbnail = lambda url, d, vid: thumbs.append(vid)
        yt_mod.fetch_watch_metadata = lambda vid: {"title": "meta " + vid, "related": []}

        screen = YoutubeScreen(StubEngine())
        screen.recent_queries = ["tab-cu", "tab-moi"]
        screen.active_query_idx = 0
        screen.load_current_tab()          # tab cu: bi chan trong search
        screen.active_query_idx = 1
        screen.load_current_tab()          # tab moi: xong truoc
        time.sleep(0.4)
        gate.set()                         # tab cu xong sau
        time.sleep(0.5)
        ids = [v.get("id") for v in screen.videos]
        check("T10.1 ket qua tab cu khong ghi de tab moi", ids == ["MOI1"], "videos=%s" % ids)
        check("T10.2 thread cu khong tai thumbnail", thumbs == ["MOI1"], "thumbs=%s" % thumbs)
        check("T10.3 trang thai loading dung", screen.loading is False)

        # Doi video nhanh trong man Watch: chi video moi duoc ap metadata
        gate2 = _th.Event()
        meta_calls = []
        def slow_meta(vid):
            meta_calls.append(vid)
            if vid == "V1":
                gate2.wait(3.0)
            return {"title": "meta " + vid, "related": []}
        yt_mod.fetch_watch_metadata = slow_meta
        watch = WatchScreen(StubEngine())
        os.environ["SDCARD_PATH"] = SD
        watch.on_enter({"video": {"id": "V1", "title": "v1"}})
        watch.on_enter({"video": {"id": "V2", "title": "v2"}})
        time.sleep(0.4)
        gate2.set()
        time.sleep(0.5)
        meta_title = (watch.meta or {}).get("title", "")
        check("T10.4 doi video nhanh -> metadata cua video cu khong ghi de",
              meta_title == "meta V2", "meta=%r" % meta_title)
        check("T10.5 thread cu hoi dung video cu (khong doc lai self.video_id)",
              "V1" in meta_calls, "calls=%s" % meta_calls)
    finally:
        yt_mod.search_youtube = real_search
        yt_mod.load_feed_cache = real_feed
        yt_mod.fetch_more_youtube = real_more
        yt_mod.get_continuation_token = real_token
        yt_mod.fetch_thumbnail = real_thumb
        yt_mod.fetch_watch_metadata = real_meta

print("OK: het selftest hieu nang" if ok else "CO LOI")
sys.exit(0 if ok else 1)
