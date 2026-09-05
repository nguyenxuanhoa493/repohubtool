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
    if __name__ == "__main__":
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
                    # Increase buffer chunk to 128KB for fast high-throughput streaming
                    while True:
                        chunk = resp.read(131072)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception:
                # Client closed socket or seeked
                pass

    return StreamingProxy


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_STREAM_CACHE_FILE = "/tmp/yt_stream_cache.json"
_STREAM_CACHE = {}
_YTDLP_READY = False
_YTDLP_LOCK = threading.Lock()


def _load_stream_cache():
    global _STREAM_CACHE
    if os.path.exists(_STREAM_CACHE_FILE):
        try:
            with open(_STREAM_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    now = time.time()
                    for k, v in data.items():
                        if isinstance(v, list) and len(v) >= 3 and v[2] > now:
                            _STREAM_CACHE[k] = (v[0], v[1], v[2])
        except Exception:
            pass


def _save_stream_cache():
    try:
        now = time.time()
        to_save = {k: list(v) for k, v in _STREAM_CACHE.items() if len(v) >= 3 and v[2] > now}
        with open(_STREAM_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f)
    except Exception:
        pass


def ensure_ytdlp_ready():
    """Giai nen bin/yt-dlp vao bo nho RAM (/tmp/ytdlp_cache) de import tuc thi."""
    global _YTDLP_READY
    if _YTDLP_READY:
        return True
    _load_stream_cache()
    with _YTDLP_LOCK:
        if _YTDLP_READY:
            return True
        try:
            unzip_dir = "/tmp/ytdlp_cache"
            ytdlp_zip = os.path.join(APP_DIR, "bin", "yt-dlp")
            if not os.path.exists(ytdlp_zip):
                for c in [
                    os.path.join(SDCARD_PATH, "Apps", "RetroHub", "bin", "yt-dlp"),
                    os.path.join(SDCARD_PATH, ".retrohub", "bin", "yt-dlp"),
                ]:
                    if os.path.exists(c):
                        ytdlp_zip = c
                        break

            if os.path.exists(ytdlp_zip):
                if not os.path.exists(os.path.join(unzip_dir, "yt_dlp")):
                    import zipfile
                    os.makedirs(unzip_dir, exist_ok=True)
                    with zipfile.ZipFile(ytdlp_zip, "r") as z:
                        z.extractall(unzip_dir)
                if unzip_dir not in sys.path:
                    sys.path.insert(0, unzip_dir)
            else:
                if ytdlp_zip not in sys.path:
                    sys.path.insert(0, ytdlp_zip)

            import yt_dlp
            _YTDLP_READY = True
            log("yt-dlp da san sang trong bo nho RAM.")
            return True
        except Exception as e:
            log(f"Loi chuan bi yt-dlp: {e}")
            return False


def extract_stream_fast(video_id: str) -> tuple:
    """Lay truc tiep link stream tu cache neu co, neu chua co thi goi yt-dlp toi uu."""
    now = time.time()
    if not _STREAM_CACHE:
        _load_stream_cache()
    if video_id in _STREAM_CACHE:
        cached_url, cached_title, cached_exp = _STREAM_CACHE[video_id]
        if now < cached_exp:
            log(f"Lay link tu cache hop le cho video: {video_id}")
            return cached_url, cached_title

    return extract_stream_url(video_id)


def extract_stream_url(video_id: str) -> tuple:
    """Trích xuất stream URL định dạng MP4 360p progressive (format 18) bằng yt-dlp tối ưu."""
    ensure_ytdlp_ready()
    try:
        import yt_dlp
    except ImportError:
        record_error("Khong tim thay module yt-dlp!")
        return None, None

    yt_url = f"https://www.youtube.com/watch?v={video_id}"
    log(f"Dang phan tich video qua yt-dlp: {yt_url}")

    ydl_opts = {
        "format": "18/b[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "skip_download": True,
        "check_formats": False,
        "lazy_playlist": True,
        "no_color": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"],
                "skip": ["dash", "hls", "translated_subs", "comments", "subtitles"]
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(yt_url, download=False)
            stream_url = info.get("url")
            title = info.get("title", video_id)
            log(f"Phan tich thanh cong qua yt-dlp: '{title}', format: {info.get('format')}")
            if stream_url:
                _STREAM_CACHE[video_id] = (stream_url, title, time.time() + 10800)
                _save_stream_cache()
            return stream_url, title
    except Exception as e:
        record_error(f"Loi khi trich xuat link video tu YouTube: {e}")
        return None, None


def play_video(video_id: str, direct_stream_url: str = None, direct_title: str = None):
    # Reset error marker
    if os.path.exists(ERR_MARKER):
        try:
            os.remove(ERR_MARKER)
        except Exception:
            pass

    log(f"==================================================")
    log(f"Bat dau phat YouTube video ID: {video_id}")

    if direct_stream_url:
        stream_url = direct_stream_url
        title = direct_title or video_id
        log(f"Su dung stream URL da trich xuat san tu app (Bo qua buoc phan tich).")
    else:
        stream_url, title = extract_stream_fast(video_id)

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
    import argparse
    import json

    parser = argparse.ArgumentParser(description="RetroHub YouTube Player")
    parser.add_argument("video_id", help="YouTube Video ID or URL")
    parser.add_argument("--stream-url", default=None, help="Pre-extracted direct stream URL")
    parser.add_argument("--title", default=None, help="Video title")
    parser.add_argument("--info-file", default=None, help="Path to JSON file with stream info")

    args = parser.parse_args()
    v_id = args.video_id.strip()
    if "v=" in v_id:
        v_id = v_id.split("v=")[1].split("&")[0]
    elif "youtu.be/" in v_id:
        v_id = v_id.split("youtu.be/")[1].split("?")[0]

    s_url = args.stream_url
    s_title = args.title

    if args.info_file and os.path.exists(args.info_file):
        try:
            with open(args.info_file, "r", encoding="utf-8") as f:
                inf = json.load(f)
            if isinstance(inf, dict):
                s_url = inf.get("stream_url") or s_url
                s_title = inf.get("title") or s_title
                v_id = inf.get("video_id") or v_id
        except Exception as e:
            log(f"Loi doc info file {args.info_file}: {e}")

    play_video(v_id, direct_stream_url=s_url, direct_title=s_title)
