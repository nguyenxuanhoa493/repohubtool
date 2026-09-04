# -*- coding: utf-8 -*-
"""YouTube standalone player launcher for RetroHub on TrimUI devices."""

import http.server
import os
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import threading
import time
import urllib.request

SDCARD_PATH = os.environ.get("SDCARD_PATH", "/mnt/SDCARD")
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(SDCARD_PATH, "RetroHub-yt.log")
TEMP_LOG = "/tmp/retrohub_yt.log"
ERR_MARKER = "/tmp/yt_last_error.txt"


def log(msg: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [rh.yt_player] {msg}"
    print(line, flush=True)
    try:
        with open(TEMP_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def record_error(err: str):
    log(f"ERROR: {err}")
    try:
        with open(ERR_MARKER, "w", encoding="utf-8") as f:
            f.write(err)
    except Exception:
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_proxy_class(target_cdn_url: str):
    class StreamingProxy(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            pass

        def do_HEAD(self):
            ctx = ssl._create_unverified_context()
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            for h in ("Range", "range", "Accept", "accept"):
                if h in self.headers:
                    headers[h] = self.headers[h]

            req = urllib.request.Request(target_cdn_url, headers=headers)
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() in ("content-type", "content-length", "content-range", "accept-ranges"):
                            self.send_header(k, v)
                    self.end_headers()
            except Exception:
                pass

        def do_GET(self):
            ctx = ssl._create_unverified_context()
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            for h in ("Range", "range", "Accept", "accept"):
                if h in self.headers:
                    headers[h] = self.headers[h]

            req = urllib.request.Request(target_cdn_url, headers=headers)
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() in ("content-type", "content-length", "content-range", "accept-ranges"):
                            self.send_header(k, v)
                    self.end_headers()
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception as e:
                # Client closed socket or seeked
                pass

    return StreamingProxy


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def extract_stream_url(video_id: str) -> tuple:
    """Uses yt-dlp to resolve direct streaming URL (format 18 / 360p-720p progressive)."""
    # 1. Add bin/yt-dlp to sys.path
    ytdlp_candidates = [
        os.path.join(APP_DIR, "bin", "yt-dlp"),
        os.path.join(SDCARD_PATH, "Apps", "RetroHub", "bin", "yt-dlp"),
        os.path.join(SDCARD_PATH, ".retrohub", "bin", "yt-dlp"),
    ]
    for c in ytdlp_candidates:
        if os.path.exists(c) and c not in sys.path:
            sys.path.insert(0, c)

    try:
        import yt_dlp
    except ImportError:
        record_error(f"Khong tim thay module yt-dlp tai {ytdlp_candidates}")
        return None, None

    yt_url = f"https://www.youtube.com/watch?v={video_id}"
    log(f"Dang phan tich video qua yt-dlp: {yt_url}")

    ydl_opts = {
        # Format 18 la video MP4 360p co san am thanh AAC trong cung 1 stream
        # Fallback sang cac stream ket hop khac duoi 720p
        "format": "18/best[height<=720][ext=mp4]/best[ext=mp4]/b/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"]
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(yt_url, download=False)
            stream_url = info.get("url")
            title = info.get("title", video_id)
            log(f"Phan tich thanh cong: '{title}', format: {info.get('format')}")
            return stream_url, title
    except Exception as e:
        record_error(f"Loi khi trich xuat link video tu YouTube: {e}")
        return None, None


def play_video(video_id: str):
    # Reset error marker
    if os.path.exists(ERR_MARKER):
        try:
            os.remove(ERR_MARKER)
        except Exception:
            pass

    log(f"==================================================")
    log(f"Bat dau phat YouTube video ID: {video_id}")

    stream_url, title = extract_stream_url(video_id)
    if not stream_url:
        log("Huy phat video vi khong lay duoc link.")
        return False

    # 1. Local HTTP streaming bridge
    proxy_server = None
    play_url = stream_url

    if stream_url.startswith("https://"):
        try:
            port = 8899
            try:
                proxy_server = ThreadedHTTPServer(("127.0.0.1", port), make_proxy_class(stream_url))
            except Exception:
                port = find_free_port()
                proxy_server = ThreadedHTTPServer(("127.0.0.1", port), make_proxy_class(stream_url))

            t = threading.Thread(target=proxy_server.serve_forever, daemon=True)
            t.start()
            play_url = f"http://127.0.0.1:{port}/stream.mp4"
            log(f"Da khoi dong Streaming Proxy bridge tai: {play_url}")
        except Exception as e:
            log(f"Khong the bat Streaming Proxy, dung link goc: {e}")
            play_url = stream_url

    # 2. Tao cau hinh bo phim dieu khien & OSD cho RetroArch
    ra_override_path = "/tmp/ra_yt_override.cfg"
    ra_override_content = """# RetroArch Media Controls & OSD Override for YouTube Streaming
# Tat hotkey enable de cac nut phan cung hoat dong truc tiep ngay lap tuc
input_enable_hotkey_btn = "nul"
input_enable_hotkey = "nul"

# Phim A (btn 1): Tam dung / Tiep tuc phat (Pause / Resume)
input_pause_toggle_btn = "1"
input_pause_toggle = "p"

# Phim B (btn 0): Thoat video ngay lap tuc, quay ve RetroHub
input_exit_emulator_btn = "0"
input_exit_emulator = "escape"

# Phim X (btn 3): Mo Menu RetroArch (Quick Menu)
input_menu_toggle_btn = "3"
input_menu_toggle_gamepad_combo = "4"

# Phim Y (btn 2): Tua nhanh (Fast forward)
input_toggle_fast_forward_btn = "2"
input_hold_fast_forward_btn = "2"

# Phim Start (btn 6): Tam dung / Tiep tuc
input_player1_start_btn = "6"

# Cho phep can Analog Trai hoat dong nhu D-Pad de tua video muot ma
input_player1_analog_dpad_mode = "1"

# Mapping D-Pad cho ffmpeg core (13=Left: -10s, 14=Right: +10s, 12=Down: -60s, 11=Up: +60s)
input_player1_b_btn = "0"
input_player1_a_btn = "1"
input_player1_y_btn = "2"
input_player1_x_btn = "3"
input_player1_select_btn = "4"
input_player1_start_btn = "6"
input_player1_l_btn = "9"
input_player1_r_btn = "10"
input_player1_up_btn = "11"
input_player1_down_btn = "12"
input_player1_left_btn = "13"
input_player1_right_btn = "14"

# Phim L / R (btn 9 / 10): Giam / Tang am luong
input_volume_up_btn = "10"
input_volume_down_btn = "9"

# Cau hinh OSD (On-Screen Display) ro net mau Cyan
video_font_enable = "true"
video_message_pos_x = "0.050000"
video_message_pos_y = "0.060000"
video_message_color = "00f6f6"
video_font_size = "32.000000"
notification_show_fast_forward = "true"
fps_show = "false"
input_driver = "sdl2"
input_joypad_driver = "sdl2"
"""
    try:
        with open(ra_override_path, "w", encoding="utf-8") as f:
            f.write(ra_override_content)
        ffmpeg_cfg_dir = os.path.join(SDCARD_PATH, "RetroArch", ".retroarch", "config", "FFmpeg")
        if os.path.exists(ffmpeg_cfg_dir):
            with open(os.path.join(ffmpeg_cfg_dir, "FFmpeg.cfg"), "w", encoding="utf-8") as f:
                f.write(ra_override_content)
    except Exception as e:
        log(f"Loi khi ghi override config: {e}")

    # 3. Xac dinh trinh phat RetroArch
    ra_dir = os.path.join(SDCARD_PATH, "RetroArch")
    emu_dir = os.path.join(SDCARD_PATH, "Emus", "FFMPEG")
    ra_bin = os.path.join(ra_dir, "ra64.trimui")
    ffmpeg_core = os.path.join(emu_dir, "ffmpeg_libretro.so")

    success = False
    try:
        if os.path.exists(ra_bin) and os.path.exists(ffmpeg_core):
            log(f"Khoi chay RetroArch FFMPEG core: {ra_bin}")
            # CPU boost
            for sh_f in ("cpufreq.sh", "cpuswitch.sh"):
                p = os.path.join(emu_dir, sh_f)
                if os.path.exists(p):
                    subprocess.call(["sh", p])

            env = os.environ.copy()
            env["HOME"] = ra_dir
            env["LD_LIBRARY_PATH"] = f"/mnt/SDCARD/System/lib:/usr/trimui/lib:{os.path.join(ra_dir, 'lib')}:" + env.get("LD_LIBRARY_PATH", "")
            cmd = [
                ra_bin,
                "--appendconfig=" + ra_override_path,
                "-L", ffmpeg_core,
                play_url,
            ]
            log(f"Command: {' '.join(cmd)}")
            subprocess.call("echo 1 > /tmp/stay_awake 2>/dev/null", shell=True)
            res = subprocess.run(cmd, cwd=ra_dir, env=env)
            subprocess.call("rm -f /tmp/stay_awake 2>/dev/null", shell=True)
            log(f"RetroArch exit code: {res.returncode}")
            success = (res.returncode == 0)


        else:
            msg = "Hệ thống chưa cài RetroArch hoặc core FFMPEG!"
            log(msg)
            record_error(msg)
            return False

    except Exception as e:
        record_error(f"Loi khi thuc thi trinh phat video: {e}")
        return False

    finally:
        if proxy_server:
            try:
                proxy_server.shutdown()
                proxy_server.server_close()
                log("Da dong Streaming Proxy bridge.")
            except Exception:
                pass

    log(f"Hoan tat phien phat video.")
    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 yt_player.py <video_id>")
        sys.exit(1)
    v_id = sys.argv[1].strip()
    # Ho tro ca full URL hoac chi ID
    if "v=" in v_id:
        v_id = v_id.split("v=")[1].split("&")[0]
    elif "youtu.be/" in v_id:
        v_id = v_id.split("youtu.be/")[1].split("?")[0]
    play_video(v_id)
