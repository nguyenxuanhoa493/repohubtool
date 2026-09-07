# -*- coding: utf-8 -*-
"""TikTok client via TikTok REST API Gateway for RetroHub on TrimUI devices."""

import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from rh.paths import (
    TIKTOK_CACHE_DIR,
    TIKTOK_FAVORITES_FALLBACK_FILE,
    TIKTOK_FAVORITES_FILE,
    TIKTOK_FEED_CACHE_FILE,
    TIKTOK_FEED_FALLBACK_FILE,
    TIKTOK_HISTORY_FILE,
)

API_BASE = "https://tiktok-api.chocode.com.vn"
API_KEY = "tk_live_1c95813ba949efce813b1378fb8bc3e1"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

DEFAULT_QUERIES = [
    "Dành cho bạn",
    "Xu hướng VN",
    "Hài Hước VN",
    "Ẩm thực quê",
]
DEFAULT_PRESET_QUERIES = tuple(DEFAULT_QUERIES)

CATEGORY_SOUNDS = {
    "Xu hướng VN": ["7330881678778960641"],
    "Hài Hước VN": ["7666054805521959688", "7677620999986858760"],
    "Ẩm thực quê": ["7061837257761639194"],
}

VIETNAMESE_CHARS = set(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
)

VIETNAMESE_KEYWORDS = {
    "vietnam", "việt nam", "viet nam", "vn", "xuhuong", "xu hướng", "xh", "fypvn", "nhachay",
    "nhạc", "hài", "gamingvn", "lienquan", "freefire", "amthuc", "ẩm thực", "vtv",
    "schannel", "beatvn", "tiin", "mixi", "streamer", "review", "tintuc", "tin tức",
    "hanoi", "saigon", "danang", "haiphong", "cantho", "tiktokvn", "tiktokvietnam", "viet", "việt"
}


def is_vietnamese_content(title: str, author_name: str = "", region: str = "") -> bool:
    """Check whether a video is from Vietnam region or has Vietnamese content."""
    if region and region.upper() == "VN":
        return True
    foreign_regions = {"US", "BR", "PK", "NG", "IN", "NP", "GB", "RU", "KE", "ID", "PH", "LK", "BD", "MM", "KH"}
    text = f"{title or ''} {author_name or ''}".lower()

    if any(c in VIETNAMESE_CHARS for c in text):
        return True

    words = re.findall(r"[a-z0-9_#]+", text)
    for w in words:
        if w.lstrip("#") in VIETNAMESE_KEYWORDS:
            return True

    if region and region.upper() in foreign_regions:
        return False

    return False


def _get_ssl_context():
    """Create unverified SSL context for embedded Linux devices without root CAs."""
    try:
        return ssl._create_unverified_context()
    except Exception:
        return None


def _api_request(endpoint: str, method: str = "GET", params: dict = None, body: dict = None, timeout: int = 12) -> dict:
    """Send authenticated request to TikTok REST API Gateway."""
    url = f"{API_BASE}{endpoint}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)

    req_data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method=method,
    )
    ctx = _get_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"[rh.tiktok] Request error on {endpoint}: {e}")
        return {}


def format_count(count: int) -> str:
    """Format integer views/likes into human readable strings (e.g. 1.2M, 45K)."""
    try:
        c = int(count or 0)
        if c >= 1_000_000:
            return f"{c / 1_000_000:.1f}M"
        elif c >= 1_000:
            return f"{c / 1_000:.1f}K"
        elif c > 0:
            return str(c)
    except Exception:
        pass
    return ""


def format_duration(seconds: int) -> str:
    """Format seconds into MM:SS string."""
    try:
        s = int(seconds or 0)
        m = s // 60
        sec = s % 60
        return f"{m}:{sec:02d}"
    except Exception:
        return "0:00"


def load_search_history() -> list:
    """Load list of recent search queries from disk, migrating legacy categories."""
    legacy_map = {
        "Xu hướng": "Xu hướng VN",
        "Trending": "Xu hướng VN",
        "Gaming": "Gaming VN",
        "Remix": "Nhạc Hot VN",
        "Hài hước": "Hài Hước VN",
        "Ẩm thực": "Ẩm Thực VN",
    }
    try:
        if os.path.exists(TIKTOK_HISTORY_FILE):
            with open(TIKTOK_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    cleaned = []
                    for q in data:
                        q_str = str(q).strip()
                        q_str = legacy_map.get(q_str, q_str)
                        if q_str and q_str not in cleaned:
                            cleaned.append(q_str)
                    if cleaned:
                        return cleaned[:10]
    except Exception as e:
        print(f"[rh.tiktok] Error loading search history: {e}")
    return list(DEFAULT_QUERIES)


def save_search_history(queries: list):
    """Save list of recent search queries to disk."""
    try:
        clean_list = []
        for q in queries:
            q_str = str(q).strip()
            if q_str and q_str not in clean_list:
                clean_list.append(q_str)
        os.makedirs(os.path.dirname(TIKTOK_HISTORY_FILE), exist_ok=True)
        with open(TIKTOK_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(clean_list[:10], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[rh.tiktok] Error saving search history: {e}")


def remove_search_history_item(query_to_remove: str) -> list:
    """Remove a search keyword from history and save to disk."""
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
    """Load user favorite TikTok videos from persistent storage."""
    for p in (TIKTOK_FAVORITES_FILE, TIKTOK_FAVORITES_FALLBACK_FILE):
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
    """Save user favorite TikTok videos to persistent storage."""
    for p in (TIKTOK_FAVORITES_FILE, TIKTOK_FAVORITES_FALLBACK_FILE):
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
    vid = str(video["id"])
    new_favs = [v for v in favorites_list if str(v.get("id")) != vid]
    if len(new_favs) == len(favorites_list):
        new_favs.insert(0, dict(video))
        save_favorites(new_favs)
        return new_favs, True
    else:
        save_favorites(new_favs)
        return new_favs, False


def load_feed_cache(category: str = "Dành cho bạn") -> tuple:
    """Load cached feed items for category. Returns (items_list, timestamp)."""
    fallback_cats = [category]
    if category in ("Dành cho bạn", "FYP", "Live"):
        fallback_cats = ["Dành cho bạn", "FYP", "Live"]
    elif category in ("Xu hướng VN", "Xu hướng"):
        fallback_cats = ["Xu hướng VN", "Xu hướng"]

    for path in (TIKTOK_FEED_CACHE_FILE, TIKTOK_FEED_FALLBACK_FILE):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for c in fallback_cats:
                        cat_data = data.get(c)
                        if isinstance(cat_data, dict):
                            items = cat_data.get("items", [])
                            if items:
                                return items, float(cat_data.get("timestamp", 0))
            except Exception:
                pass
    return [], 0.0


def save_feed_cache(category: str, items: list):
    """Save feed items for category to disk cache."""
    if not items:
        return
    for path in (TIKTOK_FEED_CACHE_FILE, TIKTOK_FEED_FALLBACK_FILE):
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
            now_ts = time.time()
            data[category] = {
                "timestamp": now_ts,
                "items": items,
            }
            if category == "Xu hướng VN":
                data["Xu hướng"] = {
                    "timestamp": now_ts,
                    "items": items,
                }
            elif category == "Xu hướng":
                data["Xu hướng VN"] = {
                    "timestamp": now_ts,
                    "items": items,
                }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            break
        except Exception:
            continue


def _normalize_tikwm_item(item: dict) -> dict:
    """Normalize video dict from TikWM API into RetroHub standardized format."""
    if not isinstance(item, dict):
        return None
    vid_id = str(item.get("id") or item.get("video_id") or "")
    if not vid_id:
        return None

    title = (item.get("title") or "").strip()
    author_info = item.get("author") or {}
    author_name = author_info.get("nickname") if isinstance(author_info, dict) else ""
    author_uid = author_info.get("unique_id") if isinstance(author_info, dict) else ""
    if not author_name:
        author_name = author_uid or "TikToker"
    if not title:
        title = f"TikTok @{author_name}"

    stream_url = item.get("play") or item.get("wmplay") or ""
    cover_url = item.get("cover") or item.get("origin_cover") or ""
    dur_sec = int(item.get("duration") or 0)
    play_count = int(item.get("play_count") or 0)
    digg_count = int(item.get("digg_count") or 0)

    return {
        "id": vid_id,
        "title": title,
        "disp_title": title,
        "author": author_name,
        "author_id": author_uid,
        "stream_url": stream_url,
        "cover_url": cover_url,
        "duration": format_duration(dur_sec),
        "duration_sec": dur_sec,
        "duration_str": format_duration(dur_sec),
        "views": play_count,
        "views_str": format_count(play_count),
        "likes": digg_count,
        "likes_str": format_count(digg_count),
        "source": "tiktok",
    }


def _normalize_aweme_item(item: dict) -> dict:
    """Normalize raw TikTok API aweme object into standardized RetroHub video dict."""
    if not isinstance(item, dict):
        return None

    vid_id = str(item.get("aweme_id") or "")
    if not vid_id or vid_id == "7554918276849995011":
        return None

    desc = (item.get("desc") or "").strip()
    author_info = item.get("author", {})
    author_nick = author_info.get("nickname") if isinstance(author_info, dict) else ""
    author_uid = author_info.get("unique_id") if isinstance(author_info, dict) else ""
    author_name = author_nick or author_uid or "TikToker"

    title = desc if desc else f"TikTok @{author_name}"

    video_data = item.get("video", {}) if isinstance(item.get("video"), dict) else {}
    stats = item.get("statistics", {}) if isinstance(item.get("statistics"), dict) else {}

    # Duration
    dur_val = video_data.get("duration", 0)
    dur_sec = dur_val // 1000 if dur_val > 1000 else dur_val

    # Skip photo albums / slideshows (not playable as video)
    if item.get("aweme_type") in (68, 150):
        return None

    # Direct CDN stream URLs from play_addr.url_list
    play_addr = video_data.get("play_addr", {})
    url_list = play_addr.get("url_list", []) if isinstance(play_addr, dict) else []
    stream_url = ""
    for u in url_list:
        if any(h in u for h in ("tiktokcdn", "tiktokv", "byteicdn")) and "music" not in u and not u.endswith(".mp3"):
            stream_url = u
            break
    if not stream_url:
        for u in url_list:
            if "music" not in u and not u.endswith(".mp3") and not u.startswith("https://www.tiktok.com") and "v16-webapp-prime" not in u:
                stream_url = u
                break
    if not stream_url:
        cand = video_data.get("no_watermark_url") or video_data.get("play_url") or ""
        if cand and not cand.startswith("https://www.tiktok.com") and "v16-webapp-prime" not in cand and "music" not in cand and not cand.endswith(".mp3"):
            stream_url = cand

    if not stream_url:
        return None

    # Cover URL
    cover_url = ""
    dynamic_cover = video_data.get("dynamic_cover", {})
    if isinstance(dynamic_cover, dict) and dynamic_cover.get("url_list"):
        cover_url = dynamic_cover["url_list"][0]
    if not cover_url:
        cover_data = video_data.get("cover", {})
        if isinstance(cover_data, dict) and cover_data.get("url_list"):
            cover_url = cover_data["url_list"][0]
        elif video_data.get("cover_url"):
            cover_url = video_data["cover_url"]

    return {
        "id": vid_id,
        "title": title,
        "disp_title": title,
        "author": author_name,
        "author_id": author_uid,
        "stream_url": stream_url,
        "cover_url": cover_url,
        "duration": format_duration(dur_sec),
        "duration_sec": dur_sec,
        "duration_str": format_duration(dur_sec),
        "views": stats.get("play_count", 0),
        "views_str": format_count(stats.get("play_count", 0)),
        "likes": stats.get("digg_count", 0),
        "likes_str": format_count(stats.get("digg_count", 0)),
        "source": "tiktok",
    }


def fetch_trending_feed(count: int = 20, cursor: int = 0) -> list:
    """Fetch live For You Page (FYP) videos via GET /api/v1/feed."""
    resp = _api_request("/api/v1/feed", params={"limit": count}, timeout=12)
    aweme_list = resp.get("data", {}).get("aweme_list", [])
    items = []
    seen = set()
    for raw in aweme_list:
        normalized = _normalize_aweme_item(raw)
        if normalized and normalized["id"] not in seen and normalized.get("stream_url"):
            seen.add(normalized["id"])
            items.append(normalized)

    if items and cursor == 0:
        save_feed_cache("Dành cho bạn", items)
    return items


def fetch_category_feed(category: str, count: int = 20, cursor: int = 0) -> list:
    """Fetch videos specifically for a designated preset category using real Sound IDs."""
    if cursor == 0:
        cached_items, _ = load_feed_cache(category)
        if cached_items:
            return cached_items

    if category in ("Dành cho bạn", "FYP", "Live"):
        return fetch_trending_feed(count=count, cursor=cursor)

    sound_ids = CATEGORY_SOUNDS.get(category, [])
    if not sound_ids:
        return fetch_trending_feed(count=count, cursor=cursor)

    items = []
    seen = set()
    for sid in sound_ids:
        resp = _api_request("/api/v1/music/videos", params={"music_id": sid, "limit": count}, timeout=12)
        raw_list = resp.get("data", {}).get("aweme_list", [])
        for raw in raw_list:
            region = raw.get("region", "")
            desc = raw.get("desc", "")
            author = raw.get("author", {}).get("nickname", "")
            if not is_vietnamese_content(desc, author, region):
                continue
            normalized = _normalize_aweme_item(raw)
            if normalized and normalized["id"] not in seen and normalized.get("stream_url"):
                seen.add(normalized["id"])
                items.append(normalized)

    if items and cursor == 0:
        save_feed_cache(category, items)
    return items


_STREAM_CACHE = {}


def search_tiktok(keyword: str, count: int = 20, offset: int = 0) -> list:
    """Route keyword or category to real TikTok feed."""
    q = (keyword or "").strip()
    if not q or q in ("Dành cho bạn", "FYP", "Live"):
        return fetch_trending_feed(count=count, cursor=offset)

    if q in CATEGORY_SOUNDS:
        return fetch_category_feed(q, count=count, cursor=offset)

    for cat in CATEGORY_SOUNDS:
        if q.lower() in cat.lower() or cat.lower() in q.lower():
            return fetch_category_feed(cat, count=count, cursor=offset)

    return fetch_trending_feed(count=count, cursor=offset)


def fetch_more_tiktok(query_str: str, current_count: int = 0) -> list:
    """Fetch additional videos for pagination / infinite scroll."""
    q = (query_str or "").strip()
    if not q or q in ("Dành cho bạn", "FYP", "Live"):
        return fetch_trending_feed(count=10, cursor=current_count)
    if q in CATEGORY_SOUNDS:
        return fetch_category_feed(q, count=20, cursor=current_count)
    return fetch_trending_feed(count=10, cursor=current_count)


def resolve_stream_url(video_id: str, item: dict = None) -> tuple:
    """Resolve direct MP4 stream URL for a TikTok video with in-memory caching."""
    if not video_id:
        return "", ""

    if video_id in _STREAM_CACHE:
        return _STREAM_CACHE[video_id]

    # Fast path: check if item already has a direct CDN stream URL
    if item and item.get("stream_url"):
        s = item["stream_url"]
        if s.startswith("http") and not s.startswith("https://www.tiktok.com") and "v16-webapp-prime" not in s:
            res = (s, item.get("title", video_id))
            _STREAM_CACHE[video_id] = res
            return res

    final_url = item.get("stream_url") if item else ""
    res = (final_url, item.get("title", video_id) if item else video_id)
    if final_url:
        _STREAM_CACHE[video_id] = res
    return res


def extract_stream_fast(video_id: str, item: dict = None) -> tuple:
    """Fast stream resolver wrapper for background speculative hover preloading."""
    return resolve_stream_url(video_id, item)


def fetch_thumbnail(cover_url: str, cache_dir: str, video_id: str, stream_url: str = None) -> str:
    """Download, convert or extract thumbnail for TikTok video, returning local path."""
    if not video_id:
        return ""

    os.makedirs(cache_dir, exist_ok=True)
    target_path = os.path.join(cache_dir, f"{video_id}.jpg")

    if os.path.exists(target_path) and os.path.getsize(target_path) > 500:
        return target_path

    if not cover_url and len(video_id) == 11 and not video_id.isdigit():
        cover_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    # Try downloading cover image
    if cover_url and cover_url.startswith("http"):
        try:
            ctx = _get_ssl_context()
            req = urllib.request.Request(cover_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                data = resp.read()

            # If standard JPEG header (FF D8)
            if len(data) > 500 and data[:2] == b"\xff\xd8":
                with open(target_path, "wb") as f:
                    f.write(data)
                return target_path

            # If HEIC or WebP, convert to JPEG with ffmpeg
            temp_path = f"/tmp/{video_id}_cover.raw"
            with open(temp_path, "wb") as f:
                f.write(data)

            cmd = ["ffmpeg", "-y", "-i", temp_path, "-frames:v", "1", "-q:v", "3", target_path]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

            if res.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 500:
                return target_path
        except Exception:
            pass

    # If cover failed or not available, extract a frame directly from stream URL using ffmpeg
    if stream_url and stream_url.startswith("http"):
        try:
            cmd = ["ffmpeg", "-y", "-ss", "00:00:00.5", "-i", stream_url, "-vframes", "1", "-q:v", "3", "-vf", "scale=320:-1", target_path]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 500:
                return target_path
        except Exception:
            pass

    return ""


def build_play_command(video_id: str, info_file: str = "/tmp/tiktok_stream_info.json") -> str:
    """Build the shell command string to execute in handoff script /tmp/launch_game.sh."""
    info_arg = f'--info-file "{info_file}"' if info_file else ""
    cmd = f"""#!/bin/sh
SDCARD_PATH="${{SDCARD_PATH:-/mnt/SDCARD}}"
APP_DIR="$SDCARD_PATH/Apps/RetroHub"
LOG_FILE="$SDCARD_PATH/RetroHub-tiktok.log"

echo "=== TikTok Streaming: {video_id} ($(date 2>/dev/null)) ===" > "$LOG_FILE"

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
