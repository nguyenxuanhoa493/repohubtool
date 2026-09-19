# -*- coding: utf-8 -*-
"""Playback session, queue, resume progress and watch history for YouTube.

Backend-agnostic on purpose: the bookkeeping for what is playing, what comes
next, where the user left off and what they have watched lives here, so the
playback engine (RetroArch today, an in-app player later) can be swapped
without touching the UI or the runner. State is persisted atomically under
SDCARD/.retrohub/.
"""

import json
import os
import threading
import time

from .paths import YT_SESSION_FILE, YT_PROGRESS_FILE, YT_WATCHED_FILE

_LOCK = threading.Lock()

MAX_QUEUE = 200
MAX_PROGRESS = 500
MAX_WATCHED = 100
RESUME_MIN_POS = 15.0   # ignore positions shorter than this many seconds
RESUME_TAIL = 10.0      # treat as finished when this close to the end
REPEAT_MODES = ("off", "one", "all")


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(default, dict):
            return data if isinstance(data, dict) else default
        if isinstance(default, list):
            return data if isinstance(data, list) else default
        return data
    except Exception:
        return default


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def duration_seconds(text) -> int:
    """Parse 'H:MM:SS' / 'M:SS' / 'SS' into seconds. 0 when unknown."""
    if not text:
        return 0
    try:
        parts = [int(p) for p in str(text).strip().split(":")]
    except ValueError:
        return 0
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 1:
        return parts[0]
    return 0


def format_seconds(sec) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%d:%02d:%02d" % (h, m, s)
    return "%d:%02d" % (m, s)


# ---------------------------------------------------------------------------
# Playback session (queue + cursor + options)
# ---------------------------------------------------------------------------
class PlaybackSession:
    """The state of one continuous viewing/listening session."""

    def __init__(self, queue=None, index=0, mode="single", context="",
                 repeat="off", shuffle=False, audio_only=False, state="idle"):
        self.queue = [dict(v) for v in (queue or []) if isinstance(v, dict) and v.get("id")]
        self.index = int(index) if self.queue else 0
        if self.index < 0 or self.index >= len(self.queue):
            self.index = 0
        self.mode = mode
        self.context = context
        self.repeat = repeat if repeat in REPEAT_MODES else "off"
        self.shuffle = bool(shuffle)
        self.audio_only = bool(audio_only)
        self.state = state

    # -- serialization ------------------------------------------------------
    def to_dict(self):
        return {
            "queue": self.queue[:MAX_QUEUE],
            "index": self.index,
            "mode": self.mode,
            "context": self.context,
            "repeat": self.repeat,
            "shuffle": self.shuffle,
            "audio_only": self.audio_only,
            "state": self.state,
            "updated_at": time.time(),
        }

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        sess = cls(
            queue=d.get("queue"),
            index=d.get("index", 0),
            mode=d.get("mode", "single"),
            context=d.get("context", ""),
            repeat=d.get("repeat", "off"),
            shuffle=d.get("shuffle", False),
            audio_only=d.get("audio_only", False),
            state=d.get("state", "idle"),
        )
        return sess if sess.queue else None

    # -- cursor -------------------------------------------------------------
    def current(self):
        if 0 <= self.index < len(self.queue):
            return self.queue[self.index]
        return None

    def _random_index(self):
        import random
        n = len(self.queue)
        if n <= 1:
            return 0
        idx = self.index
        while idx == self.index:
            idx = random.randrange(n)
        return idx

    def next_index(self) -> int:
        n = len(self.queue)
        if n == 0:
            return -1
        if self.shuffle:
            return self._random_index()
        nxt = self.index + 1
        if nxt >= n:
            return 0 if self.repeat == "all" else -1
        return nxt

    def prev_index(self) -> int:
        n = len(self.queue)
        if n == 0:
            return -1
        if self.shuffle:
            return self._random_index()
        prv = self.index - 1
        if prv < 0:
            return n - 1 if self.repeat == "all" else 0
        return prv

    def advance(self) -> bool:
        """Move to the next item. Returns True when playback should continue."""
        if not self.queue:
            self.state = "idle"
            return False
        if self.repeat == "one":
            self.state = "playing"
            return True
        nxt = self.next_index()
        if nxt < 0:
            self.state = "idle"
            return False
        self.index = nxt
        self.state = "playing"
        return True

    def back(self) -> bool:
        if not self.queue:
            return False
        prv = self.prev_index()
        if prv < 0:
            return False
        self.index = prv
        self.state = "playing"
        return True

    # -- editing ------------------------------------------------------------
    def add(self, video, position=None):
        if not isinstance(video, dict) or not video.get("id"):
            return False
        if position is None:
            position = len(self.queue)
        self.queue.insert(max(0, min(position, len(self.queue))), dict(video))
        if len(self.queue) > MAX_QUEUE:
            self.queue = self.queue[:MAX_QUEUE]
        return True

    def remove(self, idx):
        if 0 <= idx < len(self.queue):
            self.queue.pop(idx)
            if self.index >= len(self.queue):
                self.index = max(0, len(self.queue) - 1)
            return True
        return False

    def clear(self):
        self.queue = []
        self.index = 0
        self.state = "idle"


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------
def save_session_file(path, sess):
    if not sess:
        return False
    with _LOCK:
        return _save_json(path, sess.to_dict())


def load_session_file(path):
    with _LOCK:
        data = _load_json(path, {})
    return PlaybackSession.from_dict(data)


def save_session(sess):
    return save_session_file(YT_SESSION_FILE, sess)


def load_session():
    return load_session_file(YT_SESSION_FILE)


def clear_session_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def clear_session():
    clear_session_file(YT_SESSION_FILE)


# ---------------------------------------------------------------------------
# Resume progress
# ---------------------------------------------------------------------------
def load_progress():
    with _LOCK:
        return _load_json(YT_PROGRESS_FILE, {})


def get_progress(video_id):
    if not video_id:
        return None
    return load_progress().get(video_id)


def set_progress(video_id, pos, dur, title="", channel=""):
    if not video_id:
        return
    with _LOCK:
        data = _load_json(YT_PROGRESS_FILE, {})
        if not isinstance(data, dict):
            data = {}
        data[video_id] = {
            "pos": round(float(pos or 0), 1),
            "dur": round(float(dur or 0), 1),
            "ts": time.time(),
            "title": title,
            "channel": channel,
        }
        if len(data) > MAX_PROGRESS:
            overflow = len(data) - MAX_PROGRESS
            oldest = sorted(data.items(), key=lambda kv: kv[1].get("ts", 0))[:overflow]
            for k, _ in oldest:
                data.pop(k, None)
        _save_json(YT_PROGRESS_FILE, data)


def resume_position(video_id, dur=None) -> float:
    """Return the position to resume from, or 0.0 when not worth resuming."""
    entry = get_progress(video_id)
    if not entry:
        return 0.0
    pos = float(entry.get("pos", 0) or 0)
    total = float(entry.get("dur", 0) or 0) or float(dur or 0)
    if pos < RESUME_MIN_POS:
        return 0.0
    if total and (total - pos) < RESUME_TAIL:
        return 0.0
    return pos


def clear_progress(video_id=None):
    with _LOCK:
        if not video_id:
            try:
                if os.path.exists(YT_PROGRESS_FILE):
                    os.remove(YT_PROGRESS_FILE)
            except Exception:
                pass
            return
        data = _load_json(YT_PROGRESS_FILE, {})
        if isinstance(data, dict) and video_id in data:
            data.pop(video_id, None)
            _save_json(YT_PROGRESS_FILE, data)


# ---------------------------------------------------------------------------
# Watch history
# ---------------------------------------------------------------------------
def load_watched():
    return _load_json(YT_WATCHED_FILE, [])


def add_watched(video, pos=0.0):
    if not isinstance(video, dict) or not video.get("id"):
        return
    with _LOCK:
        items = _load_json(YT_WATCHED_FILE, [])
        if not isinstance(items, list):
            items = []
        vid = video["id"]
        items = [it for it in items if it.get("id") != vid]
        items.insert(0, {
            "id": vid,
            "title": video.get("title", ""),
            "disp_title": video.get("disp_title", ""),
            "channel": video.get("channel", ""),
            "disp_info": video.get("disp_info", ""),
            "duration": video.get("duration", ""),
            "thumb": video.get("thumb", ""),
            "pub": video.get("pub", ""),
            "age": video.get("age", 0.0),
            "ts": time.time(),
            "pos": round(float(pos or 0), 1),
        })
        _save_json(YT_WATCHED_FILE, items[:MAX_WATCHED])


def clear_watched():
    try:
        if os.path.exists(YT_WATCHED_FILE):
            os.remove(YT_WATCHED_FILE)
    except Exception:
        pass
