# -*- coding: utf-8 -*-
"""Multi-mirror, range-resuming download worker."""

import os
import ssl
import time
import shutil
import zipfile
import threading
import urllib.request
import concurrent.futures

from .paths import SDCARD_PATH, TEMP_DOWNLOAD_DIR
from . import state
from . import neterrors
from . import archive as archive_tool
from .storage import unlock
from .i18n import tr
from .media import pick_primary_rom, save_boxart_png
from .sysinfo import get_ip

try:
    import db
except Exception:
    db = None

MAX_CHUNK_STALLS = 3      # consecutive attempts gaining zero bytes before giving up
MAX_CHUNK_ATTEMPTS = 20   # hard cap on range requests per part
dl_state = {
    "active": False,
    "cancel_requested": False,
    "title": "",
    "size": "",
    "msg": "",
    "progress_pct": 0,
    "downloaded_str": "",
    "sys_code": "",
    "extracted_rom_path": None,
    "status": "idle",
    "selected_opt": 0,
    "speed_str": "0 KB/s",
    "is_background": False,
    "img_url": "",
    "game_info": None
}

# Pending downloads, oldest first. One runs at a time on purpose: this is a
# low-RAM handheld on Wi-Fi, so parallel transfers would fight over bandwidth and
# memory rather than finish any sooner.
dl_queue = []
dl_queue_lock = threading.Lock()

# Completed background downloads waiting to be surfaced as a toast.
dl_notifications = []

def pop_notification():
    """Oldest finished-in-background download, as (title, status), or None."""
    with dl_queue_lock:
        return dl_notifications.pop(0) if dl_notifications else None

def is_download_running():
    """A transfer is genuinely in flight."""
    return dl_state.get("status") in ("downloading", "extracting")

def is_showing_result():
    """A finished download whose modal is still waiting on the user.

    Kept distinct from "running": the queue must not be started behind this modal
    (it would steal the user's "play now" choice), but the item still has to be
    picked up once the modal is dismissed.
    """
    return bool(dl_state.get("active")) and dl_state.get("status") in ("success", "error", "cancelled")

def is_download_busy():
    return is_download_running() or is_showing_result()

def queued_items():
    """Snapshot of what is waiting, as (sys_code, game_info) pairs."""
    with dl_queue_lock:
        return list(dl_queue)

def queued_count():
    with dl_queue_lock:
        return len(dl_queue)

def clear_download_queue():
    with dl_queue_lock:
        n = len(dl_queue)
        dl_queue.clear()
    return n

def game_key(game_info):
    """Stable identity for a game across the queue and the active download."""
    if not game_info:
        return None
    return game_info.get("id") or game_info.get("filename") or game_info.get("title")

def download_state_for(game_info):
    """Where this game stands right now: 'downloading', 'queued', or None."""
    key = game_key(game_info)
    if key is None:
        return None
    if is_download_running() and game_key(dl_state.get("game_info")) == key:
        return "downloading"
    with dl_queue_lock:
        for _, g in dl_queue:
            if game_key(g) == key:
                return "queued"
    return None

def enqueue_download(sys_code, game_info):
    """Start this download, or line it up behind the one already running.

    Returns a message to show the user when it was queued, or None when it started
    straight away (the progress modal is feedback enough in that case).
    """
    already = download_state_for(game_info)
    if already == "downloading":
        return ("Game này đang được tải" if state.current_lang == "VI"
                else "That game is already downloading")
    if already == "queued":
        return ("Game này đã ở trong hàng chờ" if state.current_lang == "VI"
                else "That game is already in the queue")

    with dl_queue_lock:
        dl_queue.append((sys_code, game_info))
        pos = len(dl_queue)

    # Drain right away when nothing is actually transferring. Deciding *after* the
    # append is what closes the race: if the previous download finished between the
    # check and the insert, the item would otherwise sit in a queue with no running
    # worker left to pick it up.
    if not is_download_running() and not is_showing_result():
        # Foreground: the user just asked for this one, so the progress modal is the
        # expected feedback. Only queue hand-offs run silently in the background.
        start_next_queued(background=False)
        return None

    title = game_info.get("title", "Game")
    return (f"Đã thêm vào hàng chờ (#{pos}): {title}" if state.current_lang == "VI"
            else f"Queued (#{pos}): {title}")

def start_next_queued(background=True):
    """Pop the oldest pending download and start it. True if one was started.

    Defaults to background: draining the queue should not throw a progress modal
    over whatever the user is doing - they queued these to run unattended.
    """
    with dl_queue_lock:
        if not dl_queue:
            return False
        sys_code, game_info = dl_queue.pop(0)
    start_download_thread(sys_code, game_info, background=background)
    return True

def cancel_active_download():
    dl_state["cancel_requested"] = True
    dl_state["status"] = "cancelled"
    dl_state["msg"] = tr("dl_cancelled_toast")

def start_download_thread(sys_code, game_info, background=False):
    def worker():
        dl_state["active"] = True
        dl_state["cancel_requested"] = False
        dl_state["title"] = game_info.get("title", "Game")
        # Same precedence the rest of the UI uses. The DB and the pre-download
        # probe both fill in file_size_str; `size` is only the legacy
        # catalogs.json field, which DB-sourced games do not carry at all.
        dl_state["size"] = (game_info.get("file_size_str")
                            or game_info.get("size") or "0 MB").strip() or "0 MB"
        dl_state["msg"] = "Đang kết nối máy chủ CDN..." if state.current_lang == "VI" else "Connecting to CDN..."
        dl_state["progress_pct"] = 0
        dl_state["downloaded_str"] = "0 MB"
        dl_state["speed_str"] = "0 KB/s"
        target_sys = game_info.get("sys_code", sys_code)
        dl_state["sys_code"] = target_sys
        dl_state["extracted_rom_path"] = None
        dl_state["status"] = "downloading"
        dl_state["selected_opt"] = 0
        dl_state["is_background"] = bool(background)
        dl_state["game_info"] = game_info
        dl_state["img_url"] = game_info.get("img_url", "")

        # Khong co mang thi khong mirror nao chay duoc, ma vong thu lai van ngoi
        # het ~20s timeout roi moi chiu bao. Te hon: man xac nhan van hien dung
        # luong - no lay tu catalogue duoi the, khong phai vua hoi server - nen
        # nguoi dung doc thanh "hoi duoc server ma tai khong duoc" va di trach
        # nguon game. Noi thang ra la chua bat Wi-Fi, ngay lap tuc.
        if neterrors.wifi_offline(get_ip):
            dl_state["msg"] = tr(neterrors.NO_NET)
            dl_state["status"] = "error"
            return

        # Some catalogue rows carry a whole path in `filename`, because the source
        # site groups its jars into category folders ("category/Game Tieng Anh 3/
        # x.jar"). Only the last component names the local file: joining the raw
        # value aimed the write at a directory that does not exist, so the download
        # failed with ENOENT even though the size probe - which touches no local
        # file - had just succeeded. Backslashes fold first so a Windows-style
        # value splits too.
        filename = os.path.basename(
            str(game_info.get("filename", "")).replace("\\", "/")).strip() or "game.zip"

        sys_data = state.catalogs.get(target_sys, {})
        rom_dir = sys_data.get("rom_dir", f"{SDCARD_PATH}/Roms/{target_sys}")
        # J2ME titles are each built for one handset resolution, and the launcher
        # reads that from the folder name - so a jar has to land in the right one.
        if target_sys in ("JAVA", "J2ME"):
            try:
                from .j2me import rom_dir_for, ensure_rom_dirs
                ensure_rom_dirs()
                rom_dir = rom_dir_for(filename)
            except Exception as e:
                print(f"J2ME rom dir resolve failed: {e}")
        img_dir = sys_data.get("img_dir", f"{SDCARD_PATH}/Imgs/{target_sys}")
        tmp_dir = TEMP_DOWNLOAD_DIR

        # Khong tao noi thu muc thi khong mirror nao cuu duoc. Bat ngay tai day:
        # de no roi xuong bay top-level thi nguoi dung nhan mot chuoi Errno bi
        # cat cut giua duong dan, kem loi khuyen "vui long thu lai" vo nghia.
        try:
            os.makedirs(rom_dir, exist_ok=True)
            os.makedirs(img_dir, exist_ok=True)
            os.makedirs(tmp_dir, exist_ok=True)
        except OSError as mk_err:
            print(f"Cannot create download folders: {mk_err}")
            dl_state["msg"] = tr(neterrors.classify_error(mk_err))
            dl_state["status"] = "error"
            return
        
        tmp_zip_path = os.path.join(tmp_dir, filename)
        img_url = game_info.get("img_url", "")

        # Always clean previous leftover temporary file before starting
        if os.path.exists(tmp_zip_path):
            unlock(tmp_zip_path)
            try: os.remove(tmp_zip_path)
            except: pass

        candidates = []
        if db and game_info.get("id"):
            try:
                mirrors = db.get_game_mirrors(game_info["id"])
                for m in mirrors:
                    if m.get("rom_url"):
                        candidates.append(m.get("rom_url"))
            except Exception as e:
                print(f"DB get_game_mirrors error: {e}")

        if not candidates:
            if game_info.get("rom_url"):
                candidates.append(game_info.get("rom_url"))
            if game_info.get("mirror_url"):
                candidates.append(game_info.get("mirror_url"))
            if game_info.get("topo_url"):
                candidates.append(game_info.get("topo_url"))

        # Deduplicate candidates while preserving priority order
        dedup_candidates = []
        for c in candidates:
            if c and c not in dedup_candidates:
                dedup_candidates.append(c)
        candidates = dedup_candidates

        def get_source_label(url_str):
            if not url_str:
                return "Máy chủ Online"
            if "retrostic" in url_str:
                if "romhacks" in url_str:
                    return "Retrostic ROM Hacks CDN"
                return "Retrostic Fast CDN"
            elif "toposhop.vn" in url_str:
                return "TOPO SHOP"
            elif "github" in url_str:
                return "GitHub Fast CDN"
            elif "myrient" in url_str:
                return "Myrient Fast Mirror"
            elif "archive.org" in url_str:
                if "/download/" in url_str:
                    try:
                        coll = url_str.split("/download/")[1].split("/")[0]
                        if "GameBoyAdvance" in coll:
                            return "Internet Archive (GBA TOSEC)"
                        elif "supernintendo" in coll:
                            return "Internet Archive (SNES Set)"
                        elif "nes-roms" in coll:
                            return "Internet Archive (NES Set)"
                        elif "sega-genesis" in coll:
                            return "Internet Archive (Genesis Set)"
                        elif "sega-game-gear" in coll:
                            return "Internet Archive (Game Gear)"
                        elif "sega-master" in coll:
                            return "Internet Archive (Master System)"
                        elif "nds" in coll:
                            return "Internet Archive (NDS AP-Fix)"
                        elif "fbnarcade" in coll:
                            return "Internet Archive (FBNeo Arcade)"
                        elif "pico-8" in coll:
                            return "Internet Archive (PICO-8)"
                    except:
                        pass
                return "Internet Archive"
            try:
                from urllib.parse import urlparse
                host = urlparse(url_str).netloc
                return host if host else "Online CDN"
            except:
                return "Online CDN"

        ctx = ssl._create_unverified_context()
        max_retries = 3
        download_success = False
        # Loi cuoi cung quyet dinh cau bao cho nguoi dung, thay vi mot cau chung
        # cho moi nguyen nhan.
        last_error = None
        offline_abort = False
        readonly_abort = False
        max_workers_cfg = 4
        num_workers = max_workers_cfg

        for target_url in candidates:
            if download_success or dl_state["cancel_requested"]:
                break

            source_name = get_source_label(target_url)
            dl_state["source_name"] = source_name
            retry_count = 0

            while retry_count < max_retries and not dl_state["cancel_requested"]:
                try:
                    # First attempt fans out; retries drop to a single connection, which
                    # rate-limited servers are far more likely to actually serve.
                    num_workers = max_workers_cfg if retry_count == 0 else 1

                    # Probe URL for Range support, total length and redirect target
                    probe_req = urllib.request.Request(
                        target_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                            "Range": "bytes=0-0"
                        }
                    )
                    
                    total_bytes = 0
                    real_url = target_url
                    supports_range = False

                    with urllib.request.urlopen(probe_req, context=ctx, timeout=25) as probe_resp:
                        real_url = probe_resp.geturl()
                        dl_state["source_name"] = get_source_label(real_url)

                        c_type = probe_resp.headers.get("Content-Type", "").lower()
                        if "text/html" in c_type and not filename.endswith(".html"):
                            raise ValueError("Invalid content: Server returned HTML web page instead of ROM file")

                        cr = probe_resp.headers.get("Content-Range", "")
                        if cr and "/" in cr:
                            try:
                                total_bytes = int(cr.split("/")[-1])
                                supports_range = True
                            except:
                                pass
                        if total_bytes == 0:
                            total_bytes = int(probe_resp.headers.get("Content-Length", 0))

                        if total_bytes > 0 and game_info.get("source_id"):
                            if total_bytes >= 1024 * 1024 * 1024:
                                s_fmt = f"{total_bytes / (1024*1024*1024):.2f} GB"
                            elif total_bytes >= 1024 * 1024:
                                s_fmt = f"{total_bytes / (1024*1024):.1f} MB"
                            elif total_bytes >= 1024:
                                s_fmt = f"{total_bytes / 1024:.1f} KB"
                            else:
                                s_fmt = f"{total_bytes} B"
                            game_info["file_size_str"] = s_fmt
                            dl_state["size"] = s_fmt
                            try:
                                db.update_source_file_size(game_info.get("source_id"), s_fmt)
                            except Exception:
                                pass

                    # TURBO MULTI-THREADED STREAMING (4 Parallel Threads)
                    if supports_range and total_bytes > 512 * 1024 and num_workers > 1:
                        with open(tmp_zip_path, "wb") as f_init:
                            f_init.truncate(total_bytes)

                        part_size = total_bytes // num_workers
                        progress_lock = threading.Lock()
                        downloaded_total = 0
                        thread_error = [None]
                        last_part_error = {}

                        last_ui_update_time = [0.0]

                        def chunk_worker(w_id):
                            nonlocal downloaded_total
                            w_start = w_id * part_size
                            w_end = total_bytes - 1 if w_id == num_workers - 1 else (w_id + 1) * part_size - 1
                            w_expected = w_end - w_start + 1
                            w_written = 0
                            w_stalls = 0
                            w_attempts = 0

                            try:
                                # Resume in place rather than discarding the part: a stream the
                                # server cuts short costs only the bytes still missing. Keep going
                                # while progress is being made; stop after MAX_CHUNK_STALLS
                                # consecutive attempts that gain nothing.
                                while (w_written < w_expected and w_stalls < MAX_CHUNK_STALLS
                                       and w_attempts < MAX_CHUNK_ATTEMPTS):
                                    if dl_state["cancel_requested"] or thread_error[0] is not None:
                                        break
                                    w_attempts += 1
                                    before = w_written
                                    r_start = w_start + w_written

                                    w_headers = {
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                                        "Range": f"bytes={r_start}-{w_end}",
                                        "Accept": "*/*"
                                    }
                                    # Re-resolve the redirect on every attempt instead of reusing
                                    # real_url from the probe: signed CDN links are often single-use
                                    # or pinned to one connection, which makes extra workers fail.
                                    w_req = urllib.request.Request(target_url, headers=w_headers)
                                    try:
                                        with urllib.request.urlopen(w_req, context=ctx, timeout=30) as w_resp:
                                            # 200 means the server ignored Range and is streaming the
                                            # whole file to every worker, which would interleave into
                                            # garbage at four different offsets.
                                            if w_resp.getcode() != 206:
                                                raise ValueError("expected 206, got %s" % w_resp.getcode())
                                            with open(tmp_zip_path, "r+b") as w_file:
                                                w_file.seek(r_start)
                                                while not dl_state["cancel_requested"] and thread_error[0] is None:
                                                    chunk = w_resp.read(65536)
                                                    if not chunk:
                                                        break
                                                    if w_written + len(chunk) > w_expected:
                                                        chunk = chunk[:w_expected - w_written]
                                                        if not chunk:
                                                            break
                                                    w_file.write(chunk)
                                                    w_written += len(chunk)
                                                    with progress_lock:
                                                        downloaded_total += len(chunk)
                                                        now_ts = time.time()
                                                        if now_ts - last_ui_update_time[0] > 0.08 or downloaded_total >= total_bytes:
                                                            pct = min(100, int((downloaded_total / total_bytes) * 100))
                                                            dl_state["progress_pct"] = pct
                                                            dl_state["downloaded_str"] = f"{downloaded_total / (1024*1024):.1f} / {total_bytes / (1024*1024):.1f} MB"
                                                            dl_state["msg"] = f"Đang tải: {dl_state['downloaded_str']} ({pct}%) [4x Turbo]" if state.current_lang == "VI" else f"Downloading: {dl_state['downloaded_str']} ({pct}%) [4x Turbo]"
                                                            last_ui_update_time[0] = now_ts
                                    except Exception as e_part:
                                        last_part_error[w_id] = e_part

                                    if w_written == before:
                                        w_stalls += 1
                                        time.sleep(0.5 * w_stalls)
                                    else:
                                        w_stalls = 0

                                if (not dl_state["cancel_requested"] and thread_error[0] is None
                                        and w_written < w_expected):
                                    raise ValueError(
                                        "Worker %d: incomplete, got %d/%d bytes after %d attempt(s) (last error: %s)"
                                        % (w_id, w_written, w_expected, w_attempts, last_part_error.get(w_id)))
                            except Exception as e_w:
                                thread_error[0] = e_w
                            return w_written

                        written_total = 0
                        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as pool:
                            futures = [pool.submit(chunk_worker, i) for i in range(num_workers)]
                            for fut in concurrent.futures.as_completed(futures):
                                written_total += (fut.result() or 0)

                        # Judge on bytes actually received. getsize() cannot be trusted here:
                        # the file was pre-allocated to total_bytes by truncate() above, so it
                        # always reports the full size even when nothing was downloaded.
                        if (thread_error[0] is None and not dl_state["cancel_requested"]
                                and os.path.exists(tmp_zip_path)
                                and written_total >= total_bytes):
                            download_success = True
                            break

                        if thread_error[0] is not None:
                            print("Turbo download failed, falling back to single stream: %s" % thread_error[0])

                    # SINGLE STREAM FALLBACK (Small files or non-range streams)
                    if not download_success and not dl_state["cancel_requested"]:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                            "Accept": "*/*"
                        }
                        req = urllib.request.Request(target_url, headers=headers)
                        with urllib.request.urlopen(req, context=ctx, timeout=45) as resp:
                            dl_state["source_name"] = get_source_label(resp.geturl())
                            c_type = resp.headers.get("Content-Type", "").lower()
                            if "text/html" in c_type and not filename.endswith(".html"):
                                raise ValueError("Invalid content: Server returned HTML web page instead of ROM file")

                            tot_len = int(resp.headers.get("Content-Length", 0))
                            if tot_len > 0 and game_info.get("source_id"):
                                if tot_len >= 1024 * 1024 * 1024:
                                    s_fmt = f"{tot_len / (1024*1024*1024):.2f} GB"
                                elif tot_len >= 1024 * 1024:
                                    s_fmt = f"{tot_len / (1024*1024):.1f} MB"
                                elif tot_len >= 1024:
                                    s_fmt = f"{tot_len / 1024:.1f} KB"
                                else:
                                    s_fmt = f"{tot_len} B"
                                game_info["file_size_str"] = s_fmt
                                dl_state["size"] = s_fmt
                                try:
                                    db.update_source_file_size(game_info.get("source_id"), s_fmt)
                                except Exception:
                                    pass
                            down_bytes = 0
                            last_s_update = 0.0
                            with open(tmp_zip_path, "wb") as f_out:
                                while not dl_state["cancel_requested"]:
                                    chunk = resp.read(131072)
                                    if not chunk:
                                        break
                                    f_out.write(chunk)
                                    down_bytes += len(chunk)
                                    now_s = time.time()
                                    if now_s - last_s_update > 0.08 or (tot_len > 0 and down_bytes >= tot_len):
                                        if tot_len > 0:
                                            pct = int((down_bytes / tot_len) * 100)
                                            dl_state["progress_pct"] = min(100, pct)
                                            dl_state["downloaded_str"] = f"{down_bytes / (1024*1024):.1f} / {tot_len / (1024*1024):.1f} MB"
                                            dl_state["msg"] = f"Đang tải: {dl_state['downloaded_str']} ({pct}%)" if state.current_lang == "VI" else f"Downloading: {dl_state['downloaded_str']} ({pct}%)"
                                        else:
                                            dl_state["downloaded_str"] = f"{down_bytes / (1024*1024):.1f} MB"
                                            dl_state["msg"] = f"Đang tải: {dl_state['downloaded_str']}" if state.current_lang == "VI" else f"Downloading: {dl_state['downloaded_str']}"
                                        last_s_update = now_s

                            # Same bug class as the turbo path: a stream cut short must be
                            # retried, not reported as a finished download.
                            if tot_len > 0 and down_bytes < tot_len:
                                raise ValueError("Truncated download: got %d/%d bytes" % (down_bytes, tot_len))

                            if os.path.exists(tmp_zip_path) and os.path.getsize(tmp_zip_path) > 500:
                                download_success = True
                                break

                except Exception as ex:
                    retry_count += 1
                    last_error = ex
                    print(f"Download attempt {retry_count} for {target_url} failed: {ex}")
                    if dl_state["cancel_requested"]:
                        break
                    if os.path.exists(tmp_zip_path) and os.path.getsize(tmp_zip_path) < 5000:
                        try: os.remove(tmp_zip_path)
                        except: pass
                    # Rot Wi-Fi giua chung: moi lan thu lai, tren moi mirror, deu
                    # hong y het. Dung luon thay vi tieu them ~20s de ra dung cau
                    # bao loi nay.
                    if neterrors.classify_error(ex) == neterrors.NO_NET:
                        offline_abort = True
                        break
                    # The khoa ghi thi mirror nao cung ghi truot y het. Dung
                    # luon, va cau bao loi cuoi cung se noi dung ve cai the.
                    if neterrors.classify_error(ex) == neterrors.READONLY:
                        readonly_abort = True
                        break
                    dl_state["msg"] = f"Đang kết nối lại ({retry_count}/{max_retries})..." if state.current_lang == "VI" else f"Reconnecting ({retry_count}/{max_retries})..."
                    time.sleep(1.5)

            if offline_abort or readonly_abort:
                break

        if dl_state["cancel_requested"]:
            if os.path.exists(tmp_zip_path):
                try: os.remove(tmp_zip_path)
                except: pass
            dl_state["status"] = "cancelled"
            dl_state["active"] = False
            dl_state["msg"] = tr("dl_cancelled_toast")
            return

        if download_success and os.path.exists(tmp_zip_path):
            # Mirror /romhacks/ cua retrostic tra ve file dinh nguyen mot khoi
            # header HTTP o dau. zipfile bo qua duoc, nhung 7-Zip tu choi mo,
            # va gia lap doc thang file .zip cung khong chac bo qua.
            if archive_tool.strip_http_prefix(tmp_zip_path):
                print("Stripped mirror HTTP header from download")

            dl_state["msg"] = tr("extracting")
            dl_state["status"] = "extracting"
            dl_state["progress_pct"] = 100

            NO_EXTRACT_SYSTEMS = ("ARCADE", "MAME", "NEOGEO", "CPS1", "CPS2", "CPS3", "PGM", "FBNEO", "JAVA", "J2ME")
            extracted_rom_path = None
            if target_sys not in NO_EXTRACT_SYSTEMS and zipfile.is_zipfile(tmp_zip_path):
                try:
                    extracted_files = []
                    with zipfile.ZipFile(tmp_zip_path, 'r') as zf:
                        for member in zf.infolist():
                            if not member.is_dir() and not member.filename.endswith('.url') and not member.filename.endswith('.txt'):
                                fname = os.path.basename(member.filename)
                                if fname:
                                    target_path = os.path.join(rom_dir, fname)
                                    unlock(target_path)
                                    with zf.open(member) as source, open(target_path, "wb") as dest:
                                        shutil.copyfileobj(source, dest, length=1024*1024)
                                    extracted_files.append(target_path)
                    extracted_rom_path = pick_primary_rom(extracted_files, target_sys)
                except Exception as ze:
                    print(f"Zip extraction exception: {ze}")

            # Ngoai zip thi Python khong tu bung duoc: .rar/.7z phai nho toi 7zz.
            # Ban scene PSP con long them mot tang - vo STORE chua bo RAR volume,
            # bo do moi chua ISO - nen unpack_to_rom lap chu khong bung mot lan.
            # Truoc day ca hai deu roi xuong nhanh chep nguyen khoi ben duoi, va
            # gia lap nhan duoc dung cai .rar: "could not load game".
            elif (target_sys not in NO_EXTRACT_SYSTEMS
                    and archive_tool.looks_like_archive(tmp_zip_path)):
                dl_state["status"] = "extracting"
                dl_state["progress_pct"] = 0

                def _extract_progress(pct):
                    dl_state["progress_pct"] = pct
                    dl_state["msg"] = (f"Đang giải nén: {pct}%" if state.current_lang == "VI"
                                       else f"Extracting: {pct}%")

                try:
                    extracted_rom_path = archive_tool.unpack_to_rom(
                        tmp_zip_path, rom_dir, target_sys,
                        exe=archive_tool.sevenzip(),
                        work_dir=os.path.join(tmp_dir, "giai-nen"),
                        progress=_extract_progress,
                        prefer_name=os.path.splitext(filename)[0])
                except archive_tool.ArchiveError as ae:
                    print(f"Archive extraction failed: {ae}")
                    try: os.remove(tmp_zip_path)
                    except: pass
                    # Con so "can 1,2 GB, con 400 MB" la thu duy nhat giup nguoi
                    # dung biet phai xoa bao nhieu; cac ly do khac da du ro.
                    detail = (f"\n({ae.detail})"
                              if ae.detail and ae.key == archive_tool.NO_SPACE else "")
                    dl_state["msg"] = f"{tr(ae.key)}{detail}"
                    dl_state["status"] = "error"
                    return

            if not extracted_rom_path or not os.path.exists(extracted_rom_path):
                target_rom = os.path.join(rom_dir, filename)
                # Ban cu cua chinh game nay co the dang mang co read-only cua DOS
                # (chep tu Windows/macOS, hay bung ra tu zip): ghi de len no tra
                # EACCES du ca phan con lai cua the van ghi tot.
                # copyfile chu khong phai copy2: buoc copystat cua copy2 goi chmod
                # len the FAT/exFAT, va cu chmod do co the bi tu choi ngay khi
                # file da chep xong - du de bao nham "the khoa ghi" cho mot lan
                # tai that ra da thanh cong.
                try:
                    unlock(target_rom)
                    shutil.copyfile(tmp_zip_path, target_rom)
                except OSError as cp_err:
                    print(f"Cannot write ROM into {rom_dir}: {cp_err}")
                    try: os.remove(tmp_zip_path)
                    except: pass
                    dl_state["msg"] = tr(neterrors.classify_error(cp_err))
                    dl_state["status"] = "error"
                    return
                try:
                    shutil.copystat(tmp_zip_path, target_rom)
                except OSError:
                    pass
                extracted_rom_path = target_rom

            try:
                os.remove(tmp_zip_path)
            except:
                pass

            if img_url and img_url != "null":
                try:
                    rom_base = os.path.splitext(os.path.basename(extracted_rom_path))[0]
                    target_img = os.path.join(img_dir, f"{rom_base}.png")
                    img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(img_req, context=ctx, timeout=15) as img_resp:
                        save_boxart_png(img_resp.read(), target_img)
                except Exception as ie:
                    print(f"Boxart download exception: {ie}")

            dl_state["extracted_rom_path"] = extracted_rom_path
            # Report where the file actually landed. Rebuilding the path from
            # target_sys named the wrong folder for J2ME, whose jars go into a
            # per-resolution subfolder of rom_dir.
            dl_state["msg"] = (f"{tr('success_msg')}\n• {rom_dir}/"
                               f"\n• {os.path.basename(extracted_rom_path)}")
            dl_state["status"] = "success"
        else:
            if os.path.exists(tmp_zip_path):
                try: os.remove(tmp_zip_path)
                except: pass
            dl_state["msg"] = tr(neterrors.classify_error(last_error))
            dl_state["status"] = "error"

    def safe_worker():
        try:
            worker()
        except Exception as e_top:
            print(f"Top-level worker exception: {e_top}")
            target_sys = game_info.get("sys_code", sys_code)
            fn = os.path.basename(
                str(game_info.get("filename", "")).replace("\\", "/")) or "game.zip"
            tmp_p = os.path.join(TEMP_DOWNLOAD_DIR, fn)
            if os.path.exists(tmp_p):
                try: os.remove(tmp_p)
                except: pass
            top_key = neterrors.classify_error(e_top)
            # Chi kem chuoi exception khi khong doan duoc gi hon; da co cau ro
            # rang roi thi day them ky tu la chi lam roi man hinh.
            detail = f"\n({str(e_top)[:40]})" if top_key == neterrors.GENERIC else ""
            dl_state["msg"] = f"{tr(top_key)}{detail}"
            dl_state["status"] = "error"

    def worker_then_next():
        safe_worker()
        if dl_state.get("status") not in ("success", "error", "cancelled"):
            return

        # A background download never showed a modal, so nothing will ever dismiss
        # it. Release the slot here, otherwise the manager sits at 100% forever and
        # is_showing_result() stays true, blocking the queue.
        if dl_state.get("is_background"):
            with dl_queue_lock:
                dl_notifications.append((dl_state.get("title", ""), dl_state.get("status")))
            dl_state["active"] = False
            dl_state["status"] = "idle"

        # Only auto-advance when something is actually waiting, so a lone foreground
        # download keeps its success modal and the "play now" option.
        if queued_count():
            start_next_queued()

    t = threading.Thread(target=worker_then_next, daemon=True)
    t.start()
