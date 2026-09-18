#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch optimize and compress all PNGs in files/assets/themes_preview."""

import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS_DIR = os.path.join(ROOT, "files", "assets", "themes_preview")


def optimize_previews():
    if not os.path.isdir(PREVIEWS_DIR):
        print(f"Directory not found: {PREVIEWS_DIR}")
        return

    files = [f for f in os.listdir(PREVIEWS_DIR) if f.endswith(".png")]
    total_files = len(files)
    initial_total_size = sum(os.path.getsize(os.path.join(PREVIEWS_DIR, f)) for f in files)

    print(f"[*] Starting optimization on {total_files} files...")
    print(f"[*] Initial total size: {initial_total_size / (1024 * 1024):.2f} MB")

    for i, fname in enumerate(files):
        fpath = os.path.join(PREVIEWS_DIR, fname)
        old_sz = os.path.getsize(fpath)
        try:
            with Image.open(fpath) as im:
                target_w = 400
                if im.width > target_w:
                    ratio = target_w / float(im.width)
                    target_h = max(1, int(im.height * ratio))
                    resized = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
                else:
                    resized = im

                # Quantize to 256 colors adaptive palette
                quantized = resized.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=256)
                
                temp_path = f"{fpath}.tmp.png"
                quantized.save(temp_path, "PNG", optimize=True)

                new_sz = os.path.getsize(temp_path)
                if new_sz < old_sz:
                    os.replace(temp_path, fpath)
                    print(f"  [{i+1}/{total_files}] {fname}: {old_sz/1024:.1f} KB -> {new_sz/1024:.1f} KB (-{int((1 - new_sz/old_sz)*100)}%)")
                else:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    print(f"  [{i+1}/{total_files}] {fname}: kept original ({old_sz/1024:.1f} KB)")
        except Exception as e:
            print(f"  [!] Error optimizing {fname}: {e}")

    final_total_size = sum(os.path.getsize(os.path.join(PREVIEWS_DIR, f)) for f in files)
    saved_mb = (initial_total_size - final_total_size) / (1024 * 1024)
    pct_saved = (1 - final_total_size / initial_total_size) * 100

    print("\n[+] Optimization Completed!")
    print(f"[+] Final total size: {final_total_size / (1024 * 1024):.2f} MB")
    print(f"[+] Space saved: {saved_mb:.2f} MB ({pct_saved:.1f}%)")


if __name__ == "__main__":
    optimize_previews()
