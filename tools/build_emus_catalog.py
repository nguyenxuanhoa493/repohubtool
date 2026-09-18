#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate catalog/emus_catalog.json from SD base Emus/ and package .tar.gz files."""

import os
import json
import shutil
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SD_BASE_EMUS = "/Users/xuanhoa/Downloads/trimui_brick_pro_tg4040_sd_base_20260824/Emus"
EMUS_TGZ_DIR = os.path.join(ROOT, "emus")
CATALOG_DIR = os.path.join(ROOT, "catalog")
OUTPUT_JSON = os.path.join(CATALOG_DIR, "emus_catalog.json")
APP_CATALOG_JSON = os.path.join(ROOT, "files", "catalog", "emus_catalog.json")
APP_EMUS_PREVIEW_DIR = os.path.join(ROOT, "files", "assets", "emus_preview")

SYSTEM_META = {
    "FC": {"name": "NES / Famicom", "category": "8-Bit", "company": "Nintendo", "year": "1983", "core": "FCEUmm / Nestopia", "desc": "Hệ máy 8-bit huyền thoại của Nintendo (Mario, Contra, Tank 1990...)"},
    "SFC": {"name": "Super Famicom / SNES", "category": "16-Bit", "company": "Nintendo", "year": "1990", "core": "Snes9x", "desc": "Hệ máy 16-bit đình đám của Nintendo (Chrono Trigger, Mario World...)"},
    "GB": {"name": "Game Boy", "category": "Handheld", "company": "Nintendo", "year": "1989", "core": "Gambatte", "desc": "Máy chơi game cầm tay màn hình đơn sắc đầu tiên của Nintendo."},
    "GBC": {"name": "Game Boy Color", "category": "Handheld", "company": "Nintendo", "year": "1998", "core": "Gambatte", "desc": "Phiên bản nâng cấp màn hình màu của dòng Game Boy."},
    "GBA": {"name": "Game Boy Advance", "category": "Handheld", "company": "Nintendo", "year": "2001", "core": "mGBA / gpSP", "desc": "Hệ máy cầm tay 32-bit thành công nhất (Pokemon, Zelda, MegaMan...)"},
    "NDS": {"name": "Nintendo DS", "category": "Handheld", "company": "Nintendo", "year": "2004", "core": "DraStic Standalone", "desc": "Máy chơi game 2 màn hình cảm ứng của Nintendo."},
    "N64": {"name": "Nintendo 64", "category": "3D Consoles", "company": "Nintendo", "year": "1996", "core": "Mupen64Plus / Parallel", "desc": "Hệ máy 3D 64-bit kinh điển (Super Mario 64, Ocarina of Time...)"},
    "GW": {"name": "Game & Watch", "category": "Handheld", "company": "Nintendo", "year": "1980", "core": "GW Libretro", "desc": "Dòng máy game màn hình LCD cầm tay đời đầu của Nintendo."},
    
    "MD": {"name": "Mega Drive / Genesis", "category": "16-Bit", "company": "Sega", "year": "1988", "core": "Genesis Plus GX / PicoDrive", "desc": "Hệ máy 16-bit lừng danh của Sega (Sonic the Hedgehog, Streets of Rage...)"},
    "MS": {"name": "Master System", "category": "8-Bit", "company": "Sega", "year": "1985", "core": "Genesis Plus GX", "desc": "Hệ máy 8-bit đối đầu trực tiếp với Famicom của Sega."},
    "GG": {"name": "Game Gear", "category": "Handheld", "company": "Sega", "year": "1990", "core": "Genesis Plus GX", "desc": "Máy cầm tay màn hình màu đầu tiên của Sega."},
    "SEGACD": {"name": "Sega CD / Mega CD", "category": "16-Bit", "company": "Sega", "year": "1991", "core": "Genesis Plus GX", "desc": "Phụ kiện ổ đĩa CD mở rộng cho Sega Genesis."},
    "SS": {"name": "Sega Saturn", "category": "3D Consoles", "company": "Sega", "year": "1994", "core": "Yaba Sanshiro", "desc": "Hệ máy 32-bit đĩa CD cao cấp của Sega."},
    "DC": {"name": "Sega Dreamcast", "category": "3D Consoles", "company": "Sega", "year": "1998", "core": "Flycast", "desc": "Hệ máy 128-bit cuối cùng và đỉnh cao của Sega."},
    
    "PS": {"name": "PlayStation 1 (PSX)", "category": "3D Consoles", "company": "Sony", "year": "1994", "core": "PCSX ReARMed / SwanStation", "desc": "Hệ máy đĩa CD mở đầu đế chế game của Sony (Final Fantasy, Resident Evil...)"},
    "PPSSPP": {"name": "PlayStation Portable (PSP)", "category": "Handheld", "company": "Sony", "year": "2004", "core": "PPSSPP Standalone", "desc": "Máy chơi game cầm tay đồ họa 3D ấn tượng của Sony (God of War, GTA...)"},
    
    "ARCADE": {"name": "Arcade (Máy thùng)", "category": "Arcade", "company": "Arcade", "year": "1980s", "core": "FBNeo / MAME", "desc": "Tổng hợp các trò chơi điện tử xèng / máy thùng cổ điển."},
    "CPS1": {"name": "Capcom CPS-1", "category": "Arcade", "company": "Capcom", "year": "1988", "core": "FBNeo / FBA2012", "desc": "Bo mạch máy thùng Capcom (Street Fighter II, Final Fight...)"},
    "CPS2": {"name": "Capcom CPS-2", "category": "Arcade", "company": "Capcom", "year": "1993", "core": "FBNeo / FBA2012", "desc": "Bo mạch máy thùng Capcom (Marvel vs Capcom, Street Fighter Alpha...)"},
    "CPS3": {"name": "Capcom CPS-3", "category": "Arcade", "company": "Capcom", "year": "1996", "core": "FBNeo / FBA2012", "desc": "Bo mạch máy thùng Capcom (Street Fighter III: 3rd Strike, JoJo...)"},
    "NEOGEO": {"name": "SNK Neo Geo", "category": "Arcade", "company": "SNK", "year": "1990", "core": "FBNeo / NeoCD", "desc": "Hệ máy game đối kháng và hành động đỉnh cao (Metal Slug, King of Fighters...)"},
    "FBNEO": {"name": "FinalBurn Neo", "category": "Arcade", "company": "Multi", "year": "2000s", "core": "FBNeo Libretro", "desc": "Trình giả lập arcade đa năng và chính xác cao."},
    "MAME": {"name": "MAME Arcade", "category": "Arcade", "company": "Multi", "year": "1997", "core": "MAME Arcade", "desc": "Trình giả lập bảo tồn phần cứng máy thùng thế giới."},
    "MAME2003PLUS": {"name": "MAME 2003 Plus", "category": "Arcade", "company": "Multi", "year": "2003", "core": "MAME 2003+", "desc": "Bản MAME tối ưu hiệu năng tuyệt vời cho máy cấu hình nhẹ."},
    "MAME2010": {"name": "MAME 2010", "category": "Arcade", "company": "Multi", "year": "2010", "core": "MAME 2010", "desc": "Bản MAME hỗ trợ mở rộng thêm nhiều đầu game thập niên 90/2000."},
    "PGM": {"name": "IGS PolyGame Master", "category": "Arcade", "company": "IGS", "year": "1997", "core": "FBNeo", "desc": "Hệ máy thùng arcade Đài Loan (Knights of Valour, Oriental Legend...)"},
    
    "PCE": {"name": "PC Engine / TG16", "category": "16-Bit", "company": "NEC", "year": "1987", "core": "Mednafen PCE Fast", "desc": "Hệ máy liên minh NEC và Hudson Soft (Castlevania: Rondo of Blood...)"},
    "NGP": {"name": "Neo Geo Pocket", "category": "Handheld", "company": "SNK", "year": "1998", "core": "Mednafen NGP", "desc": "Máy cầm tay phím điều hướng micro-switch của SNK."},
    "WSC": {"name": "WonderSwan Color", "category": "Handheld", "company": "Bandai", "year": "1999", "core": "Mednafen WSwan", "desc": "Máy cầm tay sáng tạo bởi Gunpei Yokoi (cha đẻ Game Boy)."},
    "LYNX": {"name": "Atari Lynx", "category": "Handheld", "company": "Atari", "year": "1989", "core": "Handy Libretro", "desc": "Máy chơi game cầm tay màn hình màu đầu tiên trên thế giới."},
    "ATARI2600": {"name": "Atari 2600", "category": "8-Bit", "company": "Atari", "year": "1977", "core": "Stella", "desc": "Cội nguồn ngành công nghiệp trò chơi điện tử gia đình."},
    "ATARI7800": {"name": "Atari 7800", "category": "8-Bit", "company": "Atari", "year": "1986", "core": "ProSystem", "desc": "Hệ máy thế hệ thứ 3 của Atari cải tiến đồ họa."},
    
    "PICO8": {"name": "PICO-8 Fantasy Console", "category": "Engines", "company": "Lexaloffle", "year": "2015", "core": "Fake08 / Retro8", "desc": "Hệ máy ảo phong cách retro 8-bit với hàng ngàn game indie sáng tạo."},
    "EASYRPG": {"name": "EasyRPG Player", "category": "Engines", "company": "Community", "year": "2010s", "core": "EasyRPG Libretro", "desc": "Trình thông dịch chạy các tựa game làm từ RPG Maker 2000 & 2003."},
    "OPENBOR": {"name": "OpenBOR", "category": "Engines", "company": "ChronoCrash", "year": "2000s", "core": "OpenBOR Standalone", "desc": "Engine game hành động đi cảnh chặt chém (Beat 'em up) mã nguồn mở."},
    "JAVA": {"name": "J2ME Mobile (Java)", "category": "Engines", "company": "Zulu/FreeJ2ME", "year": "2000s", "core": "FreeJ2ME Standalone", "desc": "Giả lập kho game Java phím bấm điện thoại Nokia/Sony Ericsson kinh điển."},
    "FFMPEG": {"name": "Media Player (FFMPEG)", "category": "Media", "company": "TrimUI", "year": "2024", "core": "FFMPEG", "desc": "Trình phát video và âm nhạc đa định dạng."},
}


def main():
    os.makedirs(EMUS_TGZ_DIR, exist_ok=True)
    os.makedirs(CATALOG_DIR, exist_ok=True)
    os.makedirs(APP_EMUS_PREVIEW_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(APP_CATALOG_JSON), exist_ok=True)

    theme_dir = os.path.join(SD_BASE_EMUS, "_theme")

    emus_list = []

    if not os.path.isdir(SD_BASE_EMUS):
        print(f"Error: SD base directory not found: {SD_BASE_EMUS}")
        return

    # 1. Copy preview icons and posters
    if os.path.isdir(theme_dir):
        for f in os.listdir(theme_dir):
            if f.endswith(".png"):
                src = os.path.join(theme_dir, f)
                dst = os.path.join(APP_EMUS_PREVIEW_DIR, f)
                if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                    shutil.copy2(src, dst)
        print("  [+] Synced _theme assets to files/assets/emus_preview/")

    # 2. Iterate through each emulator folder in SD Base
    for item in sorted(os.listdir(SD_BASE_EMUS)):
        if item.startswith(".") or item.startswith("_sample_") or item == "_theme":
            continue
        emu_src_path = os.path.join(SD_BASE_EMUS, item)
        if not os.path.isdir(emu_src_path):
            continue

        cfg_file = os.path.join(emu_src_path, "config.json")
        cfg = {}
        if os.path.isfile(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8-sig") as f:
                    cfg = json.load(f)
            except Exception as e:
                print(f"  [!] Error reading config.json in {item}: {e}")

        meta = SYSTEM_META.get(item, {
            "name": cfg.get("label", item),
            "category": "Other",
            "company": "Other",
            "year": "Unknown",
            "core": "RetroArch / Standalone",
            "desc": f"Giả lập hệ máy {item} cho TrimUI."
        })

        tar_path = os.path.join(EMUS_TGZ_DIR, f"{item}.tar.gz")
        
        # Build tar.gz if not exists or if source is modified
        need_pack = not os.path.isfile(tar_path)
        if not need_pack:
            src_mtime = max(os.path.getmtime(os.path.join(r, f)) for r, _, fl in os.walk(emu_src_path) for f in fl) if os.listdir(emu_src_path) else 0
            if src_mtime > os.path.getmtime(tar_path):
                need_pack = True

        if need_pack:
            print(f"  [>] Packaging {item} -> {tar_path}...")
            def tar_filter(tarinfo):
                # Ignore macOS and redundant legacy version backup folders in SD Base
                name = tarinfo.name
                if "/." in name and not "/.config" in name:
                    return None
                for ignore_dir in ["PPSSPP_1.15.4", "PPSSPP_1.17.1_vulkan", "PPSSPP_1.18.1_vulkan", "PPSSPP_1.20.4"]:
                    if ignore_dir in name:
                        return None
                for ignore_file in ["PPSSPPSDL_gl_1.17.1_20241002", "PPSSPPSDL_gl_1.17.1_stable"]:
                    if ignore_file in name:
                        return None
                return tarinfo

            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(emu_src_path, arcname=item, filter=tar_filter)
            print(f"      Done ({os.path.getsize(tar_path) // 1024} KB)")

        size_kb = os.path.getsize(tar_path) // 1024 if os.path.isfile(tar_path) else 0
        size_str = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

        icon_file = f"ic-{item.lower()}.png"
        poster_file = f"poster-{item.lower()}.png"
        bg_file = f"bg-{item.lower()}.png"

        launchlist = []
        if isinstance(cfg.get("launchlist"), list):
            for l in cfg["launchlist"]:
                if isinstance(l, dict) and "name" in l:
                    launchlist.append({"name": l.get("name"), "launch": l.get("launch")})

        emu_entry = {
            "id": item,
            "name": meta.get("name", item),
            "label": cfg.get("label", item),
            "category": meta.get("category", "Other"),
            "company": meta.get("company", "Unknown"),
            "year": meta.get("year", ""),
            "core": meta.get("core", ""),
            "desc": meta.get("desc", ""),
            "rompath": cfg.get("rompath", f"../../Roms/{item}"),
            "extlist": cfg.get("extlist", ""),
            "themecolor": cfg.get("themecolor", "333333"),
            "launchlist": launchlist,
            "package_file": f"emus/{item}.tar.gz",
            "package_size": size_str,
            "icon_url": f"/assets/emus_preview/{icon_file}" if os.path.isfile(os.path.join(APP_EMUS_PREVIEW_DIR, icon_file)) else "",
            "poster_url": f"/assets/emus_preview/{poster_file}" if os.path.isfile(os.path.join(APP_EMUS_PREVIEW_DIR, poster_file)) else "",
            "bg_url": f"/assets/emus_preview/{bg_file}" if os.path.isfile(os.path.join(APP_EMUS_PREVIEW_DIR, bg_file)) else "",
        }
        emus_list.append(emu_entry)

    order = {"8-Bit": 1, "16-Bit": 2, "Handheld": 3, "3D Consoles": 4, "Arcade": 5, "Engines": 6, "Media": 7, "Other": 8}
    emus_list.sort(key=lambda x: (order.get(x["category"], 99), x["name"]))

    catalog_data = {
        "version": "1.0.0",
        "total_systems": len(emus_list),
        "systems": emus_list
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)

    with open(APP_CATALOG_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Successfully generated {OUTPUT_JSON} and {APP_CATALOG_JSON}")
    print(f"[+] Total emulators in catalog: {len(emus_list)}")


if __name__ == "__main__":
    main()
