# -*- coding: utf-8 -*-
"""Libretro Cheat Codes Downloader & Manager for TrimUI handheld devices:
Downloads official Libretro Cheats bundle (~37MB ZIP containing thousands of .cht files)
and extracts them directly into RetroArch's cheats directory.
"""

import os
import time
import zipfile
import threading
import urllib.request
from .paths import SDCARD_PATH

LIBRETRO_CHEATS_URL = "http://buildbot.libretro.com/assets/frontend/cheats.zip"


def get_cheats_dir(base_sd=None):
    """Lấy đường dẫn thư mục cheats chính của RetroArch."""
    sd = base_sd or SDCARD_PATH
    primary = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
    return primary


def get_cheats_status(base_sd=None):
    """Kiểm tra xem thư mục cheats đã được cài đặt chưa và đếm số lượng file .cht."""
    sd = base_sd or SDCARD_PATH
    c_dir = get_cheats_dir(sd)
    secondary = os.path.join(sd, "RetroArch", "cheats")

    target_dir = c_dir if os.path.isdir(c_dir) else secondary
    if not os.path.isdir(target_dir):
        return {"installed": False, "count": 0, "dir": c_dir}

    count = 0
    try:
        for root, _, files in os.walk(target_dir):
            for f in files:
                if f.lower().endswith(".cht"):
                    count += 1
    except OSError:
        pass

    return {
        "installed": count > 0,
        "count": count,
        "dir": target_dir
    }


def count_cheats(base_sd=None):
    """Đếm nhanh số mã cheat hiện có."""
    st = get_cheats_status(base_sd=base_sd)
    return st.get("count", 0)


class CheatDownloaderRunner:
    """Điều phối tải và giải nén kho Cheat Code chạy nền với thanh tiến độ thời gian thực."""

    def __init__(self):
        self.active = False
        self.done = False
        self.stop_requested = False
        self.phase = "idle"  # idle, downloading, extracting, done, error
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.progress_pct = 0
        self.speed_bps = 0
        self.status_msg = ""
        self.extracted_count = 0
        self.error_msg = ""
        self._lock = threading.Lock()
        self._thread = None

    def is_running(self):
        return self.active and not self.done

    def get_state(self):
        with self._lock:
            return {
                "active": self.active,
                "running": self.is_running(),
                "done": self.done,
                "stop_requested": self.stop_requested,
                "phase": self.phase,
                "downloaded_bytes": self.downloaded_bytes,
                "total_bytes": self.total_bytes,
                "progress_pct": self.progress_pct,
                "speed_bps": self.speed_bps,
                "status_msg": self.status_msg,
                "extracted_count": self.extracted_count,
                "error_msg": self.error_msg,
            }

    def request_stop(self):
        self.stop_requested = True
        with self._lock:
            self.status_msg = "Đang dừng tải Cheat Code..."

    def start(self, base_sd=None, url=None):
        if self.active and not self.done:
            return False

        self.active = True
        self.done = False
        self.stop_requested = False
        self.phase = "downloading"
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.progress_pct = 0
        self.speed_bps = 0
        self.status_msg = "Bắt đầu kết nối tải kho Cheat..."
        self.extracted_count = 0
        self.error_msg = ""

        self._thread = threading.Thread(
            target=self._run,
            args=(base_sd, url),
            daemon=True
        )
        self._thread.start()
        return True

    def _run(self, base_sd=None, url=None):
        sd = base_sd or SDCARD_PATH
        download_url = url or LIBRETRO_CHEATS_URL

        primary_dir = os.path.join(sd, "RetroArch", ".retroarch", "cheats")
        secondary_dir = os.path.join(sd, "RetroArch", "cheats")
        os.makedirs(primary_dir, exist_ok=True)
        os.makedirs(secondary_dir, exist_ok=True)

        tmp_zip = os.path.join(sd, "RetroArch", ".cheats_download.zip")
        if not os.path.isdir(os.path.dirname(tmp_zip)):
            tmp_zip = "/tmp/cheats_download.zip"

        try:
            # -------------------------------------------------------------
            # BƯỚC 1: TẢI FILE CHEATS.ZIP TỪ BUILDBOT
            # -------------------------------------------------------------
            with self._lock:
                self.phase = "downloading"
                self.status_msg = "Đang kết nối tới máy chủ Libretro..."

            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "RetroHub-TrimUI/1.92"}
            )

            with urllib.request.urlopen(req, timeout=20) as resp, open(tmp_zip, "wb") as out_f:
                tot_header = resp.getheader("Content-Length")
                total_len = int(tot_header) if tot_header and tot_header.isdigit() else 37157000
                with self._lock:
                    self.total_bytes = total_len

                downloaded = 0
                start_t = time.time()
                last_t = start_t
                last_bytes = 0

                chunk_size = 65536
                while True:
                    if self.stop_requested:
                        break

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break

                    out_f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if now - last_t >= 0.2:
                        speed = (downloaded - last_bytes) / (now - last_t)
                        pct = min(99, int((downloaded / total_len) * 100)) if total_len > 0 else 0
                        mb_done = downloaded / (1024 * 1024)
                        mb_tot = total_len / (1024 * 1024)
                        speed_kbs = speed / 1024

                        with self._lock:
                            self.downloaded_bytes = downloaded
                            self.progress_pct = pct
                            self.speed_bps = speed
                            self.status_msg = f"Đang tải: {mb_done:.1f}/{mb_tot:.1f} MB ({speed_kbs:.0f} KB/s)"

                        last_t = now
                        last_bytes = downloaded

            if self.stop_requested:
                if os.path.isfile(tmp_zip):
                    try:
                        os.remove(tmp_zip)
                    except Exception:
                        pass
                with self._lock:
                    self.done = True
                    self.active = False
                    self.phase = "idle"
                    self.status_msg = "Đã hủy tải Cheat Code!"
                return

            # -------------------------------------------------------------
            # BƯỚC 2: GIẢI NÉN VÀO THƯ MỤC CHEATS
            # -------------------------------------------------------------
            with self._lock:
                self.phase = "extracting"
                self.progress_pct = 99
                self.status_msg = "Đang giải nén hàng ngàn mã Cheat vào RetroArch..."

            extracted = 0
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                namelist = zf.namelist()
                tot_members = len(namelist)

                for idx, member in enumerate(namelist):
                    if self.stop_requested:
                        break

                    norm_p = os.path.normpath(member)
                    if norm_p.startswith("..") or os.path.isabs(norm_p):
                        continue

                    target_file = os.path.join(primary_dir, norm_p)
                    if member.endswith("/"):
                        os.makedirs(target_file, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        with zf.open(member) as src, open(target_file, "wb") as dst:
                            dst.write(src.read())
                        extracted += 1

                    if idx % 150 == 0:
                        with self._lock:
                            self.extracted_count = extracted
                            self.status_msg = f"Đang giải nén: {extracted} file cheat..."

            # Xóa file zip tạm sau khi giải nén
            if os.path.isfile(tmp_zip):
                try:
                    os.remove(tmp_zip)
                except Exception:
                    pass

            with self._lock:
                self.done = True
                self.active = False
                self.phase = "done"
                self.progress_pct = 100
                self.extracted_count = extracted
                self.status_msg = f"Hoàn tất! Đã cài đặt thành công {extracted} mã Cheat."

        except Exception as e:
            if os.path.isfile(tmp_zip):
                try:
                    os.remove(tmp_zip)
                except Exception:
                    pass
            with self._lock:
                self.done = True
                self.active = False
                self.phase = "error"
                self.error_msg = str(e)
                self.status_msg = f"Lỗi tải Cheat: {str(e)}"


cheat_runner = CheatDownloaderRunner()
