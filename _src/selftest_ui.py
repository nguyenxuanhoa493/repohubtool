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

def mk_rom():
    d = os.path.join(SD, "Roms", "GBA"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "Demo Game (USA).gba"), "wb") as f:
        f.write(b"\x00" * 4096)

info = {"id": 7, "filename": "Demo Game (USA).zip", "title": "Demo Game", "file_size_str": "4.0 MB", "sys_code": "GBA"}
# Dem so lan ve icon cua luoi hanh dong: chi trang thai "da tai" moi co luoi.
class CountingEngine(object):
    def __init__(self, base):
        self._base = base
        self.tiles = 0
    def __getattr__(self, name):
        attr = getattr(self._base, name)
        if name == "draw_action_vector_icon":
            def wrapped(*a, **k):
                self.tiles += 1
                return attr(*a, **k)
            return wrapped
        return attr

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
    # 2. dang tai
    downloader.dl_state.update({"active": True, "status": "downloading", "title": "Demo Game",
                                "game_info": info, "progress_pct": 42, "source_name": "Retrostic Fast CDN",
                                "msg": "dang tai"})
    m2 = GameActionModal(eng); m2.open({"sys_code": "GBA", "game_info": info, "rom_path": ""})
    eng.active_modal = m2; m2.render(eng); m2.close()
    downloader.dl_state.update({"active": False, "status": "idle", "game_info": None})
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
print("TAT CA UI SMOKE TEST OK" if ok and not missing else "CO LOI")
