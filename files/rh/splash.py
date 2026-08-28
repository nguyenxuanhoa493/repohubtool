# -*- coding: utf-8 -*-
"""Boot splash: back up the original, convert an image to fit, apply or restore."""

import os
import shutil
import subprocess

import sdl2
import sdl2.sdlimage as sdlimage

from .paths import (SPLASH_BACKUP_DIR, SPLASH_BACKUP_FILE, SPLASH_DIR, SPLASH_SYS_FILE,
                    SPLASH_TEMP_PREVIEW, SPLASH_TEMP_BMP, BOOTLOGO_BACKUP_FILE)
from . import state
from .i18n import tr

def ensure_splash_backup():
    try:
        os.makedirs(SPLASH_BACKUP_DIR, exist_ok=True)
        if not os.path.exists(SPLASH_BACKUP_FILE) and os.path.exists(SPLASH_SYS_FILE):
            shutil.copyfile(SPLASH_SYS_FILE, SPLASH_BACKUP_FILE)
            
        if not os.path.exists(BOOTLOGO_BACKUP_FILE):
            os.makedirs("/tmp/bootloader_mount", exist_ok=True)
            res = subprocess.call("mount -t vfat /dev/mmcblk0p1 /tmp/bootloader_mount 2>/dev/null", shell=True)
            if res == 0:
                src_bmp = "/tmp/bootloader_mount/bootlogo.bmp"
                if os.path.exists(src_bmp):
                    shutil.copyfile(src_bmp, BOOTLOGO_BACKUP_FILE)
                subprocess.call("umount /tmp/bootloader_mount 2>/dev/null", shell=True)
    except Exception as e:
        print(f"Error creating splash backup: {e}")

def scan_splash_images():
    ensure_splash_backup()
    images = []
    scan_dirs = [SPLASH_DIR, "/mnt/SDCARD/Pictures", "/mnt/SDCARD/Screenshots"]
    valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
    seen = set()
    for sdir in scan_dirs:
        if os.path.exists(sdir):
            for root, _, files in os.walk(sdir):
                for f in sorted(files):
                    if f.lower().endswith(valid_exts) and not f.startswith("."):
                        full_p = os.path.join(root, f)
                        if full_p not in seen and full_p != SPLASH_BACKUP_FILE:
                            seen.add(full_p)
                            size_kb = os.path.getsize(full_p) // 1024
                            images.append({
                                "filename": f,
                                "path": full_p,
                                "size_str": f"{size_kb} KB",
                                "dir": os.path.basename(root)
                            })
    
    # Also include full wallpapers from Themes (must be >= 30KB and not UI button/list slices)
    themes_dir = "/mnt/SDCARD/Themes"
    if os.path.exists(themes_dir):
        for root, _, files in os.walk(themes_dir):
            if "skin" in root.lower():
                continue
            for f in sorted(files):
                if f.lower().endswith(valid_exts) and not f.startswith("."):
                    f_low = f.lower()
                    if f_low in ("bg.png", "wallpaper.png", "background.png", "splash.png") or "wall" in f_low:
                        full_p = os.path.join(root, f)
                        if full_p not in seen and os.path.getsize(full_p) >= 30 * 1024:
                            seen.add(full_p)
                            size_kb = os.path.getsize(full_p) // 1024
                            images.append({
                                "filename": f"{os.path.basename(root)} - {f}",
                                "path": full_p,
                                "size_str": f"{size_kb} KB",
                                "dir": os.path.basename(root)
                            })
    return images

def convert_and_fit_splash(src_path, dst_path=SPLASH_TEMP_PREVIEW, width=1024, height=768):
    """Safely converts and fits any image to exact screen resolution (1024x768 or 1280x720) with black letterboxing, generating both PNG and BMP."""
    try:
        if os.path.exists(dst_path):
            os.remove(dst_path)
        if os.path.exists(SPLASH_TEMP_BMP):
            os.remove(SPLASH_TEMP_BMP)

        # 1. Try GraphicsMagick first (highest quality bicubic downscale/fit)
        gm_bin = "/mnt/SDCARD/System/bin/gm"
        if os.path.exists(gm_bin):
            cmd_png = f'export LD_LIBRARY_PATH=/mnt/SDCARD/System/lib:$LD_LIBRARY_PATH; "{gm_bin}" convert "{src_path}" -resize {width}x{height} -gravity center -background black -extent {width}x{height} "{dst_path}"'
            cmd_bmp = f'export LD_LIBRARY_PATH=/mnt/SDCARD/System/lib:$LD_LIBRARY_PATH; "{gm_bin}" convert "{src_path}" -resize {width}x{height} -gravity center -background black -extent {width}x{height} -type TrueColor "{SPLASH_TEMP_BMP}"'
            res1 = subprocess.call(cmd_png, shell=True)
            res2 = subprocess.call(cmd_bmp, shell=True)
            if res1 == 0 and os.path.exists(dst_path) and os.path.getsize(dst_path) > 100:
                return True

        # 2. PySDL2 surface scaling fallback
        src_surf = sdlimage.IMG_Load(src_path.encode('utf-8'))
        if not src_surf:
            return False
        sw = src_surf.contents.w
        sh = src_surf.contents.h
        scale = min(float(width) / sw, float(height) / sh)
        tw = max(1, int(sw * scale))
        th = max(1, int(sh * scale))
        tx = (width - tw) // 2
        ty = (height - th) // 2

        target_surf = sdl2.SDL_CreateRGBSurface(0, width, height, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
        sdl2.SDL_FillRect(target_surf, None, 0xFF000000)

        dest_rect = sdl2.SDL_Rect(tx, ty, tw, th)
        sdl2.SDL_BlitScaled(src_surf, None, target_surf, dest_rect)
        sdlimage.IMG_SavePNG(target_surf, dst_path.encode('utf-8'))
        sdl2.SDL_SaveBMP(target_surf, SPLASH_TEMP_BMP.encode('utf-8'))
        sdl2.SDL_FreeSurface(src_surf)
        sdl2.SDL_FreeSurface(target_surf)

        return os.path.exists(dst_path) and os.path.getsize(dst_path) > 100
    except Exception as e:
        print(f"Error converting splash: {e}")
        return False

def apply_splash_update(converted_path=SPLASH_TEMP_PREVIEW, converted_bmp=SPLASH_TEMP_BMP):
    """Atomic and verified update to /etc/splash.png AND U-Boot bootlogo.bmp with backup."""
    try:
        if not os.path.exists(converted_path) or os.path.getsize(converted_path) < 100:
            return False, "Tệp ảnh chuyển đổi không hợp lệ!" if state.current_lang == "VI" else "Invalid converted image file!"

        ensure_splash_backup()
        
        # 1. Update Linux OS splash (/etc/splash.png)
        shutil.copyfile(converted_path, SPLASH_SYS_FILE)
        
        # 2. Update U-Boot hardware bootlogo (/dev/mmcblk0p1/bootlogo.bmp)
        # This is the logo shown at power-on, before Linux starts. It can fail on its
        # own (BMP conversion failed, partition would not mount) while the OS splash
        # succeeded, so track it and say so rather than claiming a full update.
        bootlogo_done = False
        if os.path.exists(converted_bmp) and os.path.getsize(converted_bmp) > 100:
            os.makedirs("/tmp/bootloader_mount", exist_ok=True)
            res = subprocess.call("mount -t vfat /dev/mmcblk0p1 /tmp/bootloader_mount 2>/dev/null", shell=True)
            if res == 0:
                dst_boot_bmp = "/tmp/bootloader_mount/bootlogo.bmp"
                shutil.copyfile(converted_bmp, dst_boot_bmp)
                subprocess.call("sync; umount /tmp/bootloader_mount 2>/dev/null", shell=True)
                bootlogo_done = True

        subprocess.call("sync", shell=True)
        if bootlogo_done:
            return True, "Đã cập nhật ảnh khởi động thành công!" if state.current_lang == "VI" else "Boot splash updated successfully!"
        return True, ("Đã cập nhật splash hệ điều hành, nhưng KHÔNG đổi được logo nguồn (bootlogo)."
                      if state.current_lang == "VI" else
                      "OS splash updated, but the power-on bootlogo could NOT be changed.")
    except Exception as e:
        return False, f"Lỗi: {e}"

def restore_original_splash():
    try:
        # 1. Restore Linux OS splash
        if os.path.exists(SPLASH_BACKUP_FILE):
            shutil.copyfile(SPLASH_BACKUP_FILE, SPLASH_SYS_FILE)
        else:
            subprocess.call("rm -f /overlay/upper/etc/splash.png 2>/dev/null", shell=True)

        # 2. Restore U-Boot hardware bootlogo
        if os.path.exists(BOOTLOGO_BACKUP_FILE):
            os.makedirs("/tmp/bootloader_mount", exist_ok=True)
            res = subprocess.call("mount -t vfat /dev/mmcblk0p1 /tmp/bootloader_mount 2>/dev/null", shell=True)
            if res == 0:
                shutil.copyfile(BOOTLOGO_BACKUP_FILE, "/tmp/bootloader_mount/bootlogo.bmp")
                subprocess.call("sync; umount /tmp/bootloader_mount 2>/dev/null", shell=True)

        subprocess.call("sync", shell=True)
        return True, "Đã khôi phục ảnh khởi động gốc thành công!" if state.current_lang == "VI" else "Default boot splash restored!"
    except Exception as e:
        return False, f"Lỗi: {e}"

def scan_directory_for_images(dir_path="/mnt/SDCARD"):
    entries = []
    if not os.path.exists(dir_path):
        return entries
    
    # Parent directory
    if dir_path.rstrip("/") != "/mnt/SDCARD" and dir_path.rstrip("/") != "":
        parent_dir = os.path.dirname(dir_path.rstrip("/"))
        if not parent_dir:
            parent_dir = "/mnt/SDCARD"
        entries.append({
            "id": "fb_up",
            "type": "dir",
            "title": tr("fb_up"),
            "path": parent_dir
        })
        
    valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
    try:
        dirs = []
        files = []
        with os.scandir(dir_path) as it:
            for entry in it:
                name = entry.name
                if name.startswith("."):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    dirs.append({
                        "id": f"fb_d_{name}",
                        "type": "dir",
                        "title": f"[DIR] {name}/",
                        "path": entry.path
                    })
                elif entry.is_file(follow_symlinks=False) and name.lower().endswith(valid_exts):
                    size_kb = entry.stat().st_size // 1024
                    files.append({
                        "id": f"fb_f_{name}",
                        "type": "file",
                        "title": f"[IMG] {name}",
                        "path": entry.path,
                        "size_str": f"{size_kb} KB",
                        "filename": name
                    })
        dirs.sort(key=lambda d: d["title"].lower())
        files.sort(key=lambda f: f["filename"].lower())
        entries.extend(dirs)
        entries.extend(files)
    except Exception as e:
        print(f"Error scanning dir {dir_path}: {e}")
    return entries
