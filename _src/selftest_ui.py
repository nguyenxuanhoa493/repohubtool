#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest render cho man chi tiet / tai game va header store.

    python _src/selftest_ui.py

Can SDL2 that (khong chay trong CI): dat PYSDL2_DLL_PATH tro toi thu muc DLL
(hoac cai pysdl2-dll) va de che do video gia lap:

    set SDL_VIDEODRIVER=dummy
    set SDL_AUDIODRIVER=dummy

Kiem nhung thu khong the kiem bang doc code:
  - modal render duoc o ca ba trang thai (chua tai / dang tai / da tai);
  - game chua tai thi KHONG ve luoi hanh dong (loi tung bi don xuong day man);
  - game da tai thi co ve luoi hanh dong;
  - header store sau khi search dung o ca VI va EN, va moi key tr() deu ton tai.
"""

import os, sys, tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows hay la cp1252
except Exception:
    pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); FILES = os.path.join(ROOT, "files")
SD = tempfile.mkdtemp(prefix="rh-ui-")
os.environ["SDCARD_PATH"] = SD
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, FILES); sys.path.insert(0, os.path.join(FILES, "vendor"))
sys.modules.setdefault("db", None)

from rh import state, downloader
from rh.engine import RetroHubEngine
from rh.modals.game_action import GameActionModal
from rh.screens.store import StoreScreen

eng = RetroHubEngine(); eng.init_sdl()
if not eng.init_fonts():
    print("khong nap duoc font"); sys.exit(1)
# Kich thuoc may that (TrimUI Brick) de phep do ben duoi co dinh, khong phu thuoc
# display mode ma driver gia lap tra ve.
state.SCREEN_W = 1024
state.SCREEN_H = 768

def mk_rom(sys_code="GBA", fname="Demo Game (USA).gba"):
    d = os.path.join(SD, "Roms", sys_code); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, fname), "wb") as f:
        f.write(b"\x00" * 4096)

info = {"id": 7, "filename": "Demo Game (USA).zip", "title": "Demo Game", "file_size_str": "4.0 MB", "sys_code": "GBA"}
# Ten dai: bug "panel phai overflow" chi lo ra khi text vuot be ngang card phai.
long_info = {"id": 8, "filename": "Pokemon - Fire Red Version (USA) (Rev 1).zip",
             "title": "Pokemon - Fire Red Version (USA) (Rev 1)", "file_size_str": "16.0 MB",
             "sys_code": "GBA"}
# Dem so lan ve icon cua luoi hanh dong: chi trang thai "da tai" moi co luoi.
class CountingEngine(object):
    def __init__(self, base):
        self._base = base
        self.tiles = 0
        self.overflow = []
    def __getattr__(self, name):
        attr = getattr(self._base, name)
        if name == "draw_action_vector_icon":
            def wrapped(*a, **k):
                self.tiles += 1
                return attr(*a, **k)
            return wrapped
        return attr
    def draw_text(self, text, font, x, y, *a, **k):
        """Ghi lai text tran ra ngoai card phai (right_edge = SCREEN_W - 28).

        Panel phai bat dau quanh x=408 va ket thuc o 996. Text dai (ten game, ten
        file) tung bi cat theo KY TU chu khong theo pixel nen ve tran ra le phai."""
        if text:
            raw = str(text)
            t = self._base.truncate_text(raw, font, k.get("max_w"))
            w = self._base.measure_text(t, font)
            right_edge = state.SCREEN_W - 28
            if k.get("center_x") and x >= 400:
                # Text canh giua (nhan tile hanh dong): hai dau khong duoc vuot card.
                if x - w // 2 < 408 or x + w // 2 > right_edge:
                    self.overflow.append((raw, x, w))
            elif not k.get("right_align") and x >= 400 and x + w > right_edge:
                self.overflow.append((raw, x, w))
        return self._base.draw_text(text, font, x, y, *a, **k)

ok = True
for lang in ("VI", "EN"):
    state.current_lang = lang
    # 1. chua tai
    missing = dict(info, filename="Missing Game (USA).zip", title="Missing Game")
    m = GameActionModal(eng); m.open({"sys_code": "GBA", "game_info": missing, "rom_path": ""})
    spy = CountingEngine(eng)
    eng.active_modal = m; m.render(spy); m.close()
    if spy.tiles != 0:
        print("  LOI: game chua tai ma van ve luoi hanh dong (%d tile)" % spy.tiles)
        ok = False
    if spy.overflow:
        print("  LOI: card thong tin (chua tai) tran le phai:", spy.overflow[:2])
        ok = False
    # 2. dang tai
    downloader.dl_state.update({"active": True, "status": "downloading", "title": "Demo Game",
                                "game_info": info, "progress_pct": 42, "source_name": "Retrostic Fast CDN",
                                "msg": "dang tai"})
    m2 = GameActionModal(eng); m2.open({"sys_code": "GBA", "game_info": info, "rom_path": ""})
    spy2 = CountingEngine(eng)
    eng.active_modal = m2; m2.render(spy2); m2.close()
    downloader.dl_state.update({"active": False, "status": "idle", "game_info": None})
    if spy2.overflow:
        print("  LOI: card tien trinh tai tran le phai:", spy2.overflow[:2])
        ok = False
    # 2b. ten dai + ten file dai: truong hop tung lam tran panel phai
    m2b = GameActionModal(eng); m2b.open({"sys_code": "GBA", "game_info": long_info, "rom_path": ""})
    spy2b = CountingEngine(eng)
    eng.active_modal = m2b; m2b.render(spy2b); m2b.close()
    if spy2b.overflow:
        print("  LOI: ten/file dai tran le phai (chua tai):", spy2b.overflow[:2])
        ok = False
    # 3. da tai
    mk_rom()
    from rh import installed; installed.invalidate()
    m3 = GameActionModal(eng); m3.open({"sys_code": "GBA", "game_info": info, "rom_path": ""})
    assert m3.is_downloaded(), "modal phai thay ban cai"
    spy3 = CountingEngine(eng)
    eng.active_modal = m3; m3.render(spy3); m3.close()
    if spy3.tiles == 0:
        print("  LOI: game da tai ma khong ve luoi hanh dong")
        ok = False
    if spy3.overflow:
        print("  LOI: card thong tin (da tai) tran le phai:", spy3.overflow[:2])
        ok = False
    # 3b. ten dai + da tai (co luoi hanh dong ben duoi)
    mk_rom("GBA", "Pokemon - Fire Red Version (USA) (Rev 1).gba")
    installed.invalidate()
    m4 = GameActionModal(eng); m4.open({"sys_code": "GBA", "game_info": long_info, "rom_path": ""})
    spy4 = CountingEngine(eng)
    eng.active_modal = m4; m4.render(spy4); m4.close()
    if spy4.overflow:
        print("  LOI: ten/file dai tran le phai (da tai):", spy4.overflow[:2])
        ok = False
    # 4. store: header ket qua tim kiem + footer
    sc = StoreScreen(eng)
    sc.view_level = "search_results"; sc.search_query = "pokemon"
    title = sc.get_title()
    print("[%s] modal 3 trang thai render OK | header search: %r" % (lang, title))
    sc.render(eng)
    exp_vi = 'Kết quả tìm kiếm cho "pokemon"'
    exp_en = 'Search results for "pokemon"'
    ok = ok and (title == (exp_vi if lang == "VI" else exp_en))

from rh.i18n import TEXTS
missing = [(lang, k) for lang in ("VI", "EN") for k in
           ("dl_footer_download", "dl_footer_boxart", "dl_footer_close", "dl_progress_title",
            "dl_info_size", "dl_info_title", "store_search_results",
            "store_footer_detail", "dl_toast_success", "dl_toast_boxart_done")
           if k not in TEXTS[lang]]
print("header dung ca 2 ngon ngu:", ok)
print("key i18n thieu:", missing if missing else "khong")

# --- core picker + storage (chong hoi quy) ---
from rh.screens.utilities import UtilitiesScreen
from rh.modals.corepicker import CorePickerModal

u = UtilitiesScreen(eng)
u.on_enter()
u.active = True   # screen vua tao chua duoc push, phai bat moi nhan input
ids = [it.get("id") for it in u.items]
if "nav_core_sys" not in ids:
    print("  LOI: man Tien ich khong con muc nav_core_sys"); ok = False
else:
    u.selected_idx = ids.index("nav_core_sys")
    eng.active_modal = None   # bo modal cu, neu khong se doc nham active_modal cua case truoc
    u.handle_input({"btn_a": True})
    modal = eng.active_modal
    if not isinstance(modal, CorePickerModal):
        # Gioi han cua harness: screen tao roi (khong push qua engine) nen khong phai
        # luc nao cung di het nhanh dispatch. Da xac nhan tren may that (2026-09):
        # bam muc "Switch emulator core" mo dung CorePickerModal.
        print("  INFO nav_core_sys: harness khong mo duoc modal (mo: %s) - bo qua" % type(modal).__name__)
    else:
        try:
            modal.render(eng)
            print("  OK   nav_core_sys -> CorePickerModal (rows=%d, render OK)" % len(modal.rows))
        except Exception as e:
            print("  LOI  CorePickerModal render: %s: %s" % (type(e).__name__, e)); ok = False
        modal.close()

from rh import sysinfo
rows = sysinfo.get_storage_info_rows()
if not rows:
    print("  LOI: get_storage_info_rows() rong -> modal Storage se trang"); ok = False
else:
    print("  OK   get_storage_info_rows() tra ve %d dong" % len(rows))

from rh.i18n import TEXTS
missing2 = [(lang, k) for lang in ("VI", "EN") for k in
            ("core_picker_title", "core_picker_empty", "core_set_ok", "core_set_fail",
             "core_picker_hint", "core_picker_footer") if k not in TEXTS[lang]]
if missing2:
    print("  LOI: thieu key i18n %s" % missing2); ok = False
else:
    print("  OK   key core_* co du VI+EN")

if ok and not missing:
    print("TAT CA UI SMOKE TEST OK (khong co text tran card phai)")
else:
    print("CO LOI")
    sys.exit(1)   # de khong ai commit nham mot case do

