# -*- coding: utf-8 -*-
"""YouTube client via InnerTube API for RetroHub on TrimUI devices."""

import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

from rh.paths import YT_HISTORY_FILE

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

DEFAULT_QUERIES = ["MV Vpop", "Nhạc hot tiktok", "Hot girl tiktok", "MV Kpop"]
DEFAULT_PRESET_QUERIES = ("MV Vpop", "Nhạc hot tiktok", "Hot girl tiktok", "MV Kpop")
LEGACY_PRESETS = {
    "mv", "nhạc trẻ", "nhạc tiktok", "kpop", "nhảy tiktok", "game", "remix"
}


def get_effective_query(query: str) -> str:
    """Return cleaned query keyword."""
    return (query or "").strip()


def load_search_history() -> list:
    """Load list of recent search queries from disk."""
    try:
        if os.path.exists(YT_HISTORY_FILE):
            with open(YT_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    user_history = []
                    preset_lowers = {p.lower() for p in DEFAULT_PRESET_QUERIES} | LEGACY_PRESETS
                    for q in data:
                        q_str = str(q).strip()
                        if not q_str or q_str.lower() in preset_lowers:
                            continue
                        if q_str not in user_history:
                            user_history.append(q_str)
                    combined = list(DEFAULT_QUERIES) + user_history
                    return combined[:10]
    except Exception as e:
        print(f"[rh.yt] Error loading search history: {e}")
    return list(DEFAULT_QUERIES)


def save_search_history(queries: list):
    """Save list of recent search queries to disk."""
    try:
        user_history = []
        preset_lowers = {p.lower() for p in DEFAULT_PRESET_QUERIES} | LEGACY_PRESETS
        for q in queries:
            q_str = str(q).strip()
            if not q_str or q_str.lower() in preset_lowers:
                continue
            if q_str not in user_history:
                user_history.append(q_str)
        combined = list(DEFAULT_QUERIES) + user_history
        os.makedirs(os.path.dirname(YT_HISTORY_FILE), exist_ok=True)
        with open(YT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(combined[:10], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[rh.yt] Error saving search history: {e}")

WEB_CONTEXT = {
    "client": {
        "clientName": "WEB",
        "clientVersion": "2.20240101.00.00",
        "hl": "vi",
        "gl": "VN",
    }
}


def _get_ssl_context():
    """Create unverified SSL context for embedded Linux devices without root CAs."""
    try:
        return ssl._create_unverified_context()
    except Exception:
        return None


def _make_request(endpoint: str, payload: dict, timeout: int = 10) -> dict:
    """Send JSON POST request to YouTube InnerTube endpoint with SSL bypass."""
    url = f"{INNERTUBE_URL}/{endpoint}?prettyPrint=false"
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    ctx = _get_ssl_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _extract_videos_from_json(node, found_list: list, limit: int = 30):
    """Recursively traverse JSON structure to find all videoRenderer objects."""
    if len(found_list) >= limit:
        return

    if isinstance(node, dict):
        v = node.get("videoRenderer") or node.get("gridVideoRenderer")
        if v:
            vid = v.get("videoId")
            if vid:
                # Title
                title_runs = v.get("title", {}).get("runs", [])
                title = title_runs[0].get("text", "") if title_runs else v.get("title", {}).get("simpleText", "")
                if not title:
                    title = "Video YouTube"

                # Channel
                owner_runs = (
                    v.get("ownerText", {}).get("runs", [])
                    or v.get("shortBylineText", {}).get("runs", [])
                    or v.get("longBylineText", {}).get("runs", [])
                )
                channel = owner_runs[0].get("text", "") if owner_runs else ""

                # Duration
                duration = v.get("lengthText", {}).get("simpleText", "")

                # Thumbnail: Always use standard YouTube 16:9 JPEG (mqdefault.jpg: 320x180)
                # YouTube InnerTube returns WebP which SDL_image on TrimUI cannot decode.
                thumb_url = f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"

                # Avoid duplicate video IDs
                if not any(it["id"] == vid for it in found_list):
                    found_list.append({
                        "id": vid,
                        "title": title,
                        "channel": channel,
                        "duration": duration,
                        "thumb": thumb_url,
                    })

        for val in node.values():
            _extract_videos_from_json(val, found_list, limit)
            if len(found_list) >= limit:
                break

    elif isinstance(node, list):
        for item in node:
            _extract_videos_from_json(item, found_list, limit)
            if len(found_list) >= limit:
                break


def search_youtube(query: str, limit: int = 30, sort_by_date: bool = True) -> list:
    """Search videos on YouTube by keyword, sorting by newest upload date by default.

    Returns a list of dicts:
        [{'id': str, 'title': str, 'channel': str, 'duration': str, 'thumb': str}]
    """
    if not query or not query.strip():
        return []

    payload = {
        "context": WEB_CONTEXT,
        "query": query.strip(),
    }
    if sort_by_date:
        # CAISAhAB = Protobuf for: sort_by=UPLOAD_DATE (2), type=VIDEO (1)
        payload["params"] = "CAISAhAB"

    try:
        data = _make_request("search", payload)
    except Exception as e:
        print(f"[rh.yt] Search error for '{query}': {e}")
        return []

    results = []
    try:
        _extract_videos_from_json(data, results, limit=limit)
    except Exception as e:
        print(f"[rh.yt] Extract videos error: {e}")

    # Fallback to standard relevance search if sort_by_date returned 0 items
    if not results and sort_by_date:
        payload.pop("params", None)
        try:
            data = _make_request("search", payload)
            _extract_videos_from_json(data, results, limit=limit)
        except Exception:
            pass

    return results


def get_trending(limit: int = 30) -> list:
    """Get latest music videos on YouTube using default query 'MV Vpop'."""
    items = search_youtube("MV Vpop", limit=limit, sort_by_date=True)
    if not items:
        items = search_youtube("MV Vpop", limit=limit, sort_by_date=False)
    return items


def fetch_thumbnail(url: str, cache_dir: str, video_id: str) -> str:
    """Download standard YouTube 16:9 JPEG thumbnail and return local cached path."""
    if not video_id:
        return ""

    os.makedirs(cache_dir, exist_ok=True)
    target_path = os.path.join(cache_dir, f"{video_id}.jpg")

    # If already cached, check if it's a valid JPEG (starts with FF D8)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 500:
        try:
            with open(target_path, "rb") as f:
                header = f.read(2)
                if header == b"\xff\xd8":
                    return target_path
        except Exception:
            pass

    # Standard YouTube 16:9 JPEG thumbnail
    std_url = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
    dl_urls = [std_url]
    if url and url != std_url:
        dl_urls.append(url)

    ctx = _get_ssl_context()
    for u in dl_urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6, context=ctx) as resp:
                data = resp.read()
                # Verify JPEG header before saving
                if len(data) > 500 and data[:2] == b"\xff\xd8":
                    with open(target_path, "wb") as f:
                        f.write(data)
                    return target_path
        except Exception:
            continue

    return ""


YT_VIDEO_CACHE_DIR = "/tmp/yt_cache"


def resolve_ytdlp():
    """Dynamically import yt_dlp module from app or sdcard bin."""
    sdcard = os.environ.get("SDCARD_PATH", "/mnt/SDCARD")
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(app_dir, "bin", "yt-dlp"),
        os.path.join(sdcard, "Apps", "RetroHub", "bin", "yt-dlp"),
        os.path.join(sdcard, ".retrohub", "bin", "yt-dlp"),
    ]
    for c in candidates:
        if os.path.exists(c) and c not in sys.path:
            sys.path.insert(0, c)
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        return None


def extract_stream_url(video_id: str) -> tuple:
    """Uses yt-dlp to resolve direct streaming URL (format 18 / 360p progressive)."""
    yt_dlp = resolve_ytdlp()
    if not yt_dlp:
        return None, None

    yt_url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
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
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(yt_url, download=False)
        return info.get("url"), info.get("title", video_id)


def get_cached_video_path(video_id: str) -> str:
    """Return local path if video is already downloaded and valid, else empty string."""
    target = os.path.join(YT_VIDEO_CACHE_DIR, f"{video_id}.mp4")
    if os.path.exists(target) and os.path.getsize(target) > 500 * 1024:
        return target
    return ""


def cleanup_cache(max_mb: int = 250):
    """Keep the /tmp/yt_cache directory within reasonable size limits."""
    try:
        if not os.path.exists(YT_VIDEO_CACHE_DIR):
            return
        files = []
        total_bytes = 0
        for fn in os.listdir(YT_VIDEO_CACHE_DIR):
            if fn.endswith(".mp4"):
                fp = os.path.join(YT_VIDEO_CACHE_DIR, fn)
                sz = os.path.getsize(fp)
                mt = os.path.getmtime(fp)
                files.append((mt, sz, fp))
                total_bytes += sz

        max_bytes = max_mb * 1024 * 1024
        if total_bytes > max_bytes:
            # Sort oldest modified first
            files.sort(key=lambda x: x[0])
            for _, sz, fp in files:
                if total_bytes <= max_bytes * 0.6:
                    break
                try:
                    os.remove(fp)
                    total_bytes -= sz
                except Exception:
                    pass
    except Exception:
        pass


def download_video_stream(video_id: str, progress_cb=None, cancel_fn=None) -> tuple:
    """Download video to local cache with progress reporting.

    Args:
        video_id: YouTube video ID.
        progress_cb: fn(pct, cur_mb, tot_mb, speed_mb)
        cancel_fn: fn() -> bool, returns True if user pressed Cancel.

    Returns:
        (file_path, title, err_msg)
    """
    os.makedirs(YT_VIDEO_CACHE_DIR, exist_ok=True)
    dest_path = os.path.join(YT_VIDEO_CACHE_DIR, f"{video_id}.mp4")
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 500 * 1024:
        return dest_path, "", None

    cleanup_cache(max_mb=250)

    try:
        stream_url, title = extract_stream_url(video_id)
    except Exception as e:
        return None, "", f"Lỗi lấy link: {e}"

    if not stream_url:
        return None, "", "Không lấy được link luồng video"

    if cancel_fn and cancel_fn():
        return None, title, "Đã hủy"

    part_path = dest_path + ".part"
    try:
        ctx = _get_ssl_context()
        req = urllib.request.Request(stream_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp, open(part_path, "wb") as f:
            total_len = resp.headers.get("Content-Length")
            total_bytes = int(total_len) if total_len and total_len.isdigit() else 0
            downloaded = 0
            chunk_size = 256 * 1024
            start_time = time.time()

            while True:
                if cancel_fn and cancel_fn():
                    f.close()
                    if os.path.exists(part_path):
                        os.remove(part_path)
                    return None, title, "Đã hủy tải"

                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                if progress_cb:
                    elapsed = time.time() - start_time
                    speed_mb = (downloaded / elapsed) / (1024 * 1024) if elapsed > 0 else 0
                    pct = int(downloaded * 100 / total_bytes) if total_bytes > 0 else 0
                    cur_mb = downloaded / (1024 * 1024)
                    tot_mb = total_bytes / (1024 * 1024) if total_bytes > 0 else 0
                    progress_cb(pct, cur_mb, tot_mb, speed_mb)

        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(part_path, dest_path)
        return dest_path, title, None
    except Exception as e:
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except Exception:
                pass
        return None, title, f"Lỗi tải: {e}"


def build_play_command(video_id: str, info_file: str = "/tmp/yt_stream_info.json") -> str:
    """Build the shell command string to execute in handoff script /tmp/launch_game.sh.

    Streams YouTube video immediately using rh.yt_player with RetroArch FFMPEG core.
    If info_file exists, passes pre-extracted stream URL to bypass yt-dlp extraction entirely.
    """
    info_arg = f'--info-file "{info_file}"' if info_file else ""
    cmd = f"""#!/bin/sh
SDCARD_PATH="${{SDCARD_PATH:-/mnt/SDCARD}}"
APP_DIR="$SDCARD_PATH/Apps/RetroHub"
LOG_FILE="$SDCARD_PATH/RetroHub-yt.log"

echo "=== YouTube Streaming: {video_id} ($(date 2>/dev/null)) ===" > "$LOG_FILE"

# Ensure System/lib is in LD_LIBRARY_PATH for OpenSSL 1.1.1 and SDL2
export LD_LIBRARY_PATH="/mnt/SDCARD/System/lib:/usr/trimui/lib:$LD_LIBRARY_PATH"

PY3="python3"
if [ -f "$APP_DIR/python/bin/python3" ]; then
    PY3="$APP_DIR/python/bin/python3"
elif [ -f "$SDCARD_PATH/System/bin/python3" ]; then
    PY3="$SDCARD_PATH/System/bin/python3"
elif [ -f "$SDCARD_PATH/.retrohub/python/bin/python3" ]; then
    PY3="$SDCARD_PATH/.retrohub/python/bin/python3"
elif which python3 >/dev/null 2>&1; then
    PY3="python3"
fi

cd "$APP_DIR"
"$PY3" -m rh.yt_player "{video_id}" {info_arg} >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "Streaming Exit Code: $EXIT_CODE" >> "$LOG_FILE"
"""
    return cmd

