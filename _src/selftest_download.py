#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selftest headless cho luong tai game va man chi tiet (khong SDL2, khong mang).

    python3 _src/selftest_download.py

Moi test deu chay tren mot the SD gia trong thu muc tam. Khong test nao cham
mang, cham thiet bi hay mo cua so, nen bo nay chay duoc ca trong CI lan tren may
Windows. Logic duoc kiem qua cac module la (rh/installed.py, rh/downloader.py,
rh/archive.py, rh/catalog.py) - phan SDL2 chi con vai dong goi lai.
"""

import os
import shutil
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = os.path.join(ROOT, "files")

SD = tempfile.mkdtemp(prefix="rh-selftest-")
os.environ["SDCARD_PATH"] = SD
sys.path.insert(0, FILES)
sys.modules.setdefault("db", None)          # khong can kho game SQLite

from rh import archive, catalog, downloader, installed, romfiles   # noqa: E402

FAILED = []

def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (("  <- " + detail) if detail and not cond else ""))
    if not cond:
        FAILED.append(name)

def sd_path(*parts):
    p = os.path.join(SD, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

def write(path, data=b"x"):
    with open(path, "wb") as f:
        f.write(data)
    return path

def reset_state():
    downloader.dl_queue[:] = []
    downloader.dl_state.update({"active": False, "status": "idle", "cancel_requested": False,
                                "title": "", "game_info": None, "is_background": False})
    installed.invalidate()

# ---------------------------------------------------------------------------
print("T1. Tai xong (foreground) roi tai tiep: slot phai duoc nha")
reset_state()
started = []
downloader.start_download_thread = lambda *a, **k: started.append(a[1].get("title"))
downloader.dl_state.update({"active": True, "status": "success", "is_background": False,
                            "title": "Game A", "game_info": {"id": 1, "title": "Game A"}})
downloader.release_result_slot()
check("T1a. active=False sau khi nha slot", downloader.dl_state["active"] is False,
      "active=%r" % downloader.dl_state["active"])
check("T1b. is_download_busy() het chan", downloader.is_download_busy() is False)
downloader.enqueue_download("GBA", {"id": 2, "title": "Game B", "filename": "b.zip"})
check("T1c. game ke tiep duoc tai ngay", started == ["Game B"], "started=%r" % started)

print("T2. Huy mot game con trong hang cho")
reset_state()
downloader.dl_state.update({"active": True, "status": "downloading", "title": "Dang chay",
                            "game_info": {"id": 9, "title": "Dang chay"}})
queued = {"id": 3, "title": "Game C", "filename": "c.zip"}
with downloader.dl_queue_lock:
    downloader.dl_queue.append(("GBA", queued))
check("T2a. cancel_download tra True khi co trong hang cho", downloader.cancel_download(queued) is True)
check("T2b. hang cho rong", downloader.queued_count() == 0, "count=%d" % downloader.queued_count())
check("T2c. phien dang chay khong bi dung", downloader.dl_state["cancel_requested"] is False)

print("T3. Khop ban cai that: catalogue .zip, tren the la .gba")
reset_state()
write(sd_path("Roms", "GBA", "Pokemon - Emerald Version (U).gba"), b"\x00" * 1024)
found = installed.find("GBA", "Pokemon - Emerald Version (U).zip")
check("T3a. find() thay ban cai", bool(found), "found=%r" % (found,))
check("T3b. tra dung duong dan", bool(found) and found["path"].endswith(".gba"))
check("T3c. base_key chuan hoa", installed.base_key("GBA", "Pokemon - Emerald Version (U).zip") == "pokemon - emerald version (u)")

print("T4. Xoa game: liet ke file cung base")
reset_state()
rom = write(sd_path("Roms", "PS", "Game.cue"), b"cue")
write(sd_path("Roms", "PS", "Game.bin"), b"\x00" * 2048)
write(sd_path("Roms", "PS", "Game (Disc 2).bin"), b"\x00" * 2048)
write(sd_path("Roms", "PS", "Other.bin"), b"\x00" * 2048)
names = sorted(os.path.basename(p) for p in installed.companions(rom))
check("T4a. gom dung file cung base", names == ["Game.bin"], "names=%r" % names)

print("T5. Cai xong thi store phai tim lai duoc (ten .cue doi theo ten kho)")
reset_state()
rom_dir = os.path.join(SD, "Roms", "PS")
os.makedirs(rom_dir, exist_ok=True)
store_name = "Need for Speed Most Wanted Underground"
zp = os.path.join(SD, "NSFMWU.zip")
with zipfile.ZipFile(zp, "w") as z:
    z.writestr("a-nfsmwu.cue", 'FILE "a-nfsmwu.bin" BINARY\n')
    z.writestr("a-nfsmwu.bin", b"\x00" * 2048)
primary, _files = downloader.unpack_zip(zp, rom_dir, "PS", store_name + ".zip")
check("T5a. ROM chinh doi ten theo ten kho",
      os.path.basename(primary) == store_name + ".cue", os.path.basename(primary))
check("T5b. .bin giu nguyen ten de cue tro dung",
      os.path.exists(os.path.join(rom_dir, "a-nfsmwu.bin")))
entry = installed.find("PS", store_name + ".zip")
check("T5c. store tim lai duoc ban cai", bool(entry) and entry["path"] == primary)
write(sd_path("Imgs", "PS", store_name + ".png"), b"png")
check("T5d. boxart theo ten kho", installed.image_path("PS", store_name + ".zip") is not None)
cue = write(sd_path("Roms", "PS", "track.cue"), b'FILE "track.bin" BINARY\n')
check("T5e. doi ten khi khong bi .cue tro toi",
      romfiles.safe_preferred_name(cue, [], "Ten Kho") == "Ten Kho")
check("T5f. giu nguyen ten khi co .cue tro toi no",
      romfiles.safe_preferred_name(sd_path("Roms", "PS", "track.bin"), [cue], "Ten Kho") is None)

print("T6. Giai nen zip: staging, giu cau truc, khong ghi do dang")
reset_state()
rom_dir = os.path.join(SD, "Roms", "PS")
os.makedirs(rom_dir, exist_ok=True)
zp = os.path.join(SD, "Game.zip")
with zipfile.ZipFile(zp, "w") as z:
    z.writestr("Disc 1/Game.cue", "FILE \"Game.bin\" BINARY\n")
    z.writestr("Disc 1/Game.bin", b"\x00" * 4096)
    z.writestr("Disc 2/Game.bin", b"\x01" * 4096)
primary, files = downloader.unpack_zip(zp, rom_dir, "PS", "Game.zip")
rel = sorted(os.path.relpath(p, rom_dir).replace(os.sep, "/") for p in files)
check("T6a. giu cau truc thu muc", rel == ["Disc 1/Game.bin", "Disc 1/Game.cue", "Disc 2/Game.bin"], "rel=%r" % rel)
check("T6b. khong mat file trung ten", os.path.getsize(os.path.join(rom_dir, "Disc 2", "Game.bin")) == 4096)
primary_rel = os.path.relpath(primary, rom_dir).replace(os.sep, "/")
check("T6c. chon .cue lam ROM chinh", primary_rel == "Disc 1/Game.cue", "primary=%r" % primary_rel)
check("T6d. staging da don", not os.path.exists(os.path.join(downloader.TEMP_DOWNLOAD_DIR, "staging-Game.zip")))

print("T7. Chan khi thieu dung luong")
try:
    downloader.ensure_space(10 ** 12, rom_dir, free_space=lambda p: 1024)
    check("T7a. nem NotEnoughSpace", False, "khong nem gi")
except downloader.NotEnoughSpace as e:
    check("T7a. nem NotEnoughSpace", "can" in str(e) or "need" in str(e).lower(), str(e))
except Exception as e:
    check("T7a. nem NotEnoughSpace", False, "%s: %s" % (type(e).__name__, e))

print("T8. Turbo: phai khop Content-Range")
check("T8a. nhan dung offset", downloader.range_start("bytes 1048576-2097151/5000000") == 1048576)
check("T8b. header la -> None", downloader.range_start("") is None)
check("T8c. lech offset bi tu choi", downloader.range_start_ok("bytes 0-99/5000", 4096) is False)
check("T8d. dung offset duoc nhan", downloader.range_start_ok("bytes 4096-8191/5000", 4096) is True)

print("T9. Doc danh sach 7zz: phan biet parse duoc va khong")
out_ok = ("Listing archive\n----------\nPath = a.iso\nSize = 100\nFolder = -\n\n"
          "Path = b.nfo\nSize = 10\nFolder = -\n\n")
total, names, parsed = archive.parse_list_output(out_ok)
check("T9a. parse duoc", parsed is True and total == 110 and names == ["a.iso", "b.nfo"], "%r %r %r" % (total, names, parsed))
total2, names2, parsed2 = archive.parse_list_output("7-Zip: unexpected output")
check("T9b. bao khong parse duoc thay vi tra 0", parsed2 is False, "%r" % (parsed2,))

# 7-Zip tren Windows tra ve CRLF, va so dau gach cua dong ngan cach doi theo ban
# 7-Zip. Truoc day ca hai deu lam buoc doc danh sach that bai, va nguoi dung nhan
# "FILE TAI VE HONG" cho mot archive lanh.
total3, names3, parsed3 = archive.parse_list_output(out_ok.replace("\n", "\r\n"))
check("T9c. doc duoc output CRLF (7-Zip tren Windows)",
      parsed3 is True and total3 == 110 and names3 == ["a.iso", "b.nfo"], "%r %r %r" % (total3, names3, parsed3))
out_long = "Listing archive\r\n" + "-" * 24 + "\r\nPath = x.bin\r\nSize = 7\r\nFolder = -\r\n\r\n"
total4, names4, parsed4 = archive.parse_list_output(out_long)
check("T9d. doc duoc dong ngan cach dai", parsed4 is True and names4 == ["x.bin"], "%r %r" % (total4, parsed4))

print("T9e. Phan biet ly do: file hong / khong co ROM / ECM")
check("T9e1. key rieng cho file hong", archive.BROKEN in archive.ARCHIVE_KEYS)
check("T9e2. key rieng cho archive khong co ROM", archive.NO_ROM in archive.ARCHIVE_KEYS)
check("T9e3. key rieng cho ROM nen ECM", archive.ECM in archive.ARCHIVE_KEYS)
from rh.i18n import TEXTS
missing_keys = [k for lang in ("VI", "EN") for k in (archive.BROKEN, archive.NO_ROM, archive.ECM) if k not in TEXTS[lang]]
check("T9e4. ca 3 key deu co VI+EN", not missing_keys, "%r" % (missing_keys,))

print("T9f. Nhan dien anh CD nen ECM (.bin.ecm cua ban scene)")
ecm = write(sd_path("tmp", "game.bin.ecm"), b"ECM\x00" + b"\x00" * 32)
plain = write(sd_path("tmp", "that.bin"), b"\x00" * 32)
misnamed = write(sd_path("tmp", "ten-sai.ecm"), b"BIN\x00" + b"\x00" * 32)
check("T9f1. .bin.ecm dung magic -> ECM", archive.ecm_packed(ecm) is True)
check("T9f2. file .bin khong bi coi la ECM", archive.ecm_packed(plain) is False)
check("T9f3. .ecm dat ten sai (khong magic) khong tinh la ECM", archive.ecm_packed(misnamed) is False)

print("T10. Library/store: ton trong casing 'roms' cua the")
reset_state()
write(sd_path("roms", "NES", "Contra (USA).nes"), b"\x00" * 512)
games = catalog.scan_all_downloaded_games()
check("T10a. van thay game khi thu muc ten 'roms'",
      any(g["filename"] == "Contra (USA).nes" for g in games), "games=%d" % len(games))

print("T10b. PICO-8: ROM la file .p8.png")
reset_state()
write(sd_path("Roms", "PICO8", "Celeste Classic.p8.png"), b"\x00" * 512)
check("T10b. nhan dien duoc game PICO-8",
      installed.find("PICO8", "Celeste Classic.p8.png") is not None)

print()
if FAILED:
    print("FAILED %d test: %s" % (len(FAILED), ", ".join(FAILED)))
    sys.exit(1)
print("OK: tat ca selftest deu pass")
shutil.rmtree(SD, ignore_errors=True)
