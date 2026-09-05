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

from rh.paths import (
    YT_HISTORY_FILE,
    YT_FEED_CACHE_FILE,
    YT_FEED_FALLBACK_FILE,
    YT_FAVORITES_FILE,
    YT_FAVORITES_FALLBACK_FILE,
)

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

DEFAULT_QUERIES = ["Music", "KPOP", "USUK", "Tiktok"]
DEFAULT_PRESET_QUERIES = ("Music", "KPOP", "USUK", "Tiktok")
LEGACY_PRESETS = {
    "mv", "nhạc trẻ", "nhạc tiktok", "kpop", "nhảy tiktok", "game", "remix",
    "mv vpop", "nhạc hot tiktok", "hot girl tiktok", "mv kpop",
}


def parse_age_hours(text: str) -> float:
    """Parse relative time string into hours if needed."""
    if not text:
        return 999999.0
    s = text.strip().lower()
    if "hôm nay" in s:
        return 4.0
    if "hôm qua" in s or "yesterday" in s:
        return 24.0
    m = re.search(r"(\d+)", s)
    if not m:
        return 999999.0
    val = float(m.group(1))
    if "giây" in s or "second" in s:
        return val / 3600.0
    elif "phút" in s or "minute" in s:
        return val / 60.0
    elif "giờ" in s or "hour" in s:
        return val
    elif "ngày" in s or "day" in s:
        return val * 24.0
    elif "tuần" in s or "week" in s:
        return val * 24.0 * 7.0
    elif "tháng" in s or "month" in s:
        return val * 24.0 * 30.0
    elif "năm" in s or "year" in s:
        return val * 24.0 * 365.0
    return 999999.0


def get_effective_query(query: str) -> str:
    """Return cleaned query keyword without altering sorting or appending year."""
    return (query or "").strip()


def load_search_history() -> list:
    """Load list of recent search queries from disk. Falls back to DEFAULT_QUERIES if empty or missing."""
    try:
        if os.path.exists(YT_HISTORY_FILE):
            with open(YT_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    cleaned = []
                    for q in data:
                        q_str = str(q).strip()
                        if q_str and q_str not in cleaned:
                            cleaned.append(q_str)
                    if cleaned:
                        return cleaned[:10]
    except Exception as e:
        print(f"[rh.yt] Error loading search history: {e}")
    return list(DEFAULT_QUERIES)


def save_search_history(queries: list):
    """Save list of recent search queries to disk."""
    try:
        clean_list = []
        for q in queries:
            q_str = str(q).strip()
            if q_str and q_str not in clean_list:
                clean_list.append(q_str)
        os.makedirs(os.path.dirname(YT_HISTORY_FILE), exist_ok=True)
        with open(YT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(clean_list[:10], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[rh.yt] Error saving search history: {e}")


def remove_search_history_item(query_to_remove: str) -> list:
    """Remove any search keyword (preset or custom) from history and save to disk."""
    q_clean = (query_to_remove or "").strip().lower()
    if not q_clean:
        return load_search_history()

    current_history = load_search_history()
    new_history = [q for q in current_history if q.strip().lower() != q_clean]
    if not new_history:
        new_history = list(DEFAULT_QUERIES)

    save_search_history(new_history)
    return new_history


def load_favorites() -> list:
    """Load user favorite videos list from persistent storage."""
    for p in (YT_FAVORITES_FILE, YT_FAVORITES_FALLBACK_FILE):
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    return []


def save_favorites(favorites: list):
    """Save user favorite videos list to persistent storage."""
    for p in (YT_FAVORITES_FILE, YT_FAVORITES_FALLBACK_FILE):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(favorites, f, ensure_ascii=False, indent=2)
            return
        except Exception:
            continue


def is_favorite(video_id: str, favorites_list: list = None) -> bool:
    """Check if a video ID is in favorites."""
    if not video_id:
        return False
    favs = favorites_list if favorites_list is not None else load_favorites()
    return any(item.get("id") == video_id for item in favs)


def toggle_favorite(video: dict, favorites_list: list) -> tuple:
    """Toggle favorite status of a video. Returns (new_favorites_list, is_added)."""
    if not video or not video.get("id") or video.get("id") == "__LOAD_MORE__":
        return favorites_list, False
    vid = video["id"]
    new_favs = [v for v in favorites_list if v.get("id") != vid]
    if len(new_favs) == len(favorites_list):
        # Video was not in favorites, add it
        new_favs.insert(0, dict(video))
        save_favorites(new_favs)
        return new_favs, True
    else:
        # Video was in favorites, removed
        save_favorites(new_favs)
        return new_favs, False


def load_feed_cache(category: str = "trending") -> tuple:
    """Load cached feed items for category. Returns (items_list, timestamp)."""
    for path in (YT_FEED_CACHE_FILE, YT_FEED_FALLBACK_FILE):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cat = data.get(category)
                    if isinstance(cat, dict):
                        return cat.get("items", []), float(cat.get("timestamp", 0))
            except Exception:
                pass
    return [], 0.0


def save_feed_cache(category: str, items: list):
    """Save feed items for category to disk cache."""
    if not items:
        return
    for path in (YT_FEED_CACHE_FILE, YT_FEED_FALLBACK_FILE):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            if not isinstance(data, dict):
                data = {}
            data[category] = {
                "timestamp": time.time(),
                "items": items,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            break
        except Exception:
            continue

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


def _make_request(endpoint: str, payload: dict, timeout: int = 7) -> dict:
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

                # Upload relative date & computed age in hours
                pub = v.get("publishedTimeText", {}).get("simpleText", "")
                age = parse_age_hours(pub)

                # Pre-format truncated titles and channel info for zero-overhead UI rendering
                disp_title = title if len(title) <= 120 else title[:117] + "..."
                if pub:
                    info_str = f"{channel} • {pub}" if channel else pub
                else:
                    info_str = channel
                disp_info = info_str if len(info_str) <= 34 else info_str[:32] + "..."

                # Avoid duplicate video IDs
                if not any(it["id"] == vid for it in found_list):
                    found_list.append({
                        "id": vid,
                        "title": title,
                        "disp_title": disp_title,
                        "channel": channel,
                        "disp_info": disp_info,
                        "duration": duration,
                        "thumb": thumb_url,
                        "pub": pub,
                        "age": age,
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


def _find_continuation_token(node) -> str:
    """Recursively search for continuation token in response dict/list."""
    if isinstance(node, dict):
        if "continuationCommand" in node:
            tok = node["continuationCommand"].get("token")
            if tok:
                return tok
        for val in node.values():
            tok = _find_continuation_token(val)
            if tok:
                return tok
    elif isinstance(node, list):
        for item in node:
            tok = _find_continuation_token(item)
            if tok:
                return tok
    return ""


_CONTINUATION_TOKENS = {}


def get_continuation_token(query: str) -> str:
    """Get stored continuation token for a search query."""
    return _CONTINUATION_TOKENS.get(query, "")


def set_continuation_token(query: str, token: str):
    """Store continuation token for pagination."""
    if token:
        _CONTINUATION_TOKENS[query] = token
    else:
        _CONTINUATION_TOKENS.pop(query, None)


def fetch_more_youtube(query: str, cont_token: str = None) -> tuple:
    """Fetch next batch of videos using continuation token. Returns (videos_list, next_token)."""
    token = cont_token or get_continuation_token(query)
    if not token:
        return [], ""

    payload = {
        "context": WEB_CONTEXT,
        "continuation": token,
    }
    try:
        cont_data = _make_request("search", payload, timeout=6)
    except Exception as e:
        print(f"[rh.yt] Error fetching more videos for '{query}': {e}")
        return [], ""

    more_videos = []
    try:
        _extract_videos_from_json(cont_data, more_videos, limit=18)
    except Exception as e:
        print(f"[rh.yt] Extract more videos error: {e}")

    next_token = _find_continuation_token(cont_data)
    set_continuation_token(query, next_token)
    return more_videos, next_token


def search_youtube(query: str, limit: int = 24) -> list:
    """Search videos on YouTube by keyword, preserving natural YouTube ranking without sorting.

    Returns a list of dicts:
        [{'id': str, 'title': str, 'channel': str, 'duration': str, 'thumb': str, 'pub': str, 'age': float}]
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    eff_query = get_effective_query(clean_query)

    payload = {
        "context": WEB_CONTEXT,
        "query": eff_query,
    }

    try:
        data = _make_request("search", payload)
    except Exception as e:
        print(f"[rh.yt] Search error for '{eff_query}': {e}")
        return []

    results = []
    try:
        _extract_videos_from_json(data, results, limit=limit)
    except Exception as e:
        print(f"[rh.yt] Extract videos error: {e}")

    # Extract and store continuation token for "Load more" at the end of the list
    cont_token = _find_continuation_token(data)
    set_continuation_token(clean_query, cont_token)

    # Only fetch continuation if the first page returned fewer than 6 candidate videos
    if len(results) < 6 and cont_token:
        try:
            cont_payload = {"context": WEB_CONTEXT, "continuation": cont_token}
            cont_data = _make_request("search", cont_payload, timeout=5)
            _extract_videos_from_json(cont_data, results, limit=limit)
            next_token = _find_continuation_token(cont_data)
            set_continuation_token(clean_query, next_token)
        except Exception as e:
            print(f"[rh.yt] Continuation fetch error: {e}")

    final_results = results[:limit]
    if final_results:
        save_feed_cache(clean_query, final_results)
    return final_results


def get_trending(limit: int = 24) -> list:
    """Get latest music videos on YouTube using default query 'Music'."""
    items = search_youtube("Music", limit=limit)
    if items:
        save_feed_cache("trending", items)
        save_feed_cache("Music", items)
    return items


def fetch_thumbnail(url: str, cache_dir: str, video_id: str) -> str:
    """Download standard YouTube 16:9 JPEG thumbnail and return local cached path."""
    if not video_id:
        return ""

    os.makedirs(cache_dir, exist_ok=True)
    target_path = os.path.join(cache_dir, f"{video_id}.jpg")

    # Fast cache hit check (avoid file open / re-read overhead on every frame)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 500:
        return target_path

    # Standard YouTube 16:9 JPEG thumbnail (mqdefault: 320x180, ~10-15KB)
    std_url = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
    dl_urls = [std_url]
    if url and url != std_url:
        dl_urls.append(url)

    ctx = _get_ssl_context()
    for u in dl_urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
                data = resp.read()
                # Verify JPEG header (FF D8) before saving
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

