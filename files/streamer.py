#!/usr/bin/env python3
# ==============================================================================
# TRIMUI PRO - MINIMAL & CLEAN ULTRA LOW-LATENCY STREAMER (PORT 8088)
# Features: Zero-Copy mmap • Fastint DCT • 1.5x Scale Button • Clean UI
# Defaults: 720p (Native Crisp) • 30 FPS • Ultra-Low Latency (< 30ms)
# ==============================================================================
import os
import sys
import time
import mmap
import socket
import struct
import fcntl
import base64
import hashlib
import urllib.parse
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 8088
FBIOGET_VSCREENINFO = 0x4600
SOI = bytes([0xff, 0xd8])
EOI = bytes([0xff, 0xd9])
WS_MAGIC = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# Default to 720p Resolution & 30 FPS
current_fps = 30
current_res = "720"
config_lock = threading.Lock()

latest_frame = None
latest_frame_id = 0
frame_lock = threading.Lock()

active_clients = 0
active_clients_lock = threading.Lock()
grabber_thread = None
stop_event = threading.Event()
restart_grabber_event = threading.Event()

HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrimUI Pro - Live Screen</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: #090d16;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 12px;
            overflow-x: hidden;
        }
        /* Top Mini Status Bar */
        .top-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            max-width: 800px;
            margin-bottom: 8px;
            padding: 0 4px;
            transition: max-width 0.25s ease;
        }
        .top-bar.scale-150 { max-width: 1020px; }
        .top-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #00f0ff;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .top-status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            color: #94a3b8;
            font-family: monospace;
        }
        .dot {
            width: 7px;
            height: 7px;
            background: #00df8f;
            border-radius: 50%;
            box-shadow: 0 0 6px #00df8f;
            display: inline-block;
        }

        /* Screen Canvas Container */
        .screen-wrap {
            position: relative;
            background: #000;
            border: 2px solid #1e293b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
            width: 100%;
            max-width: 760px;
            aspect-ratio: 4 / 3;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: max-width 0.25s ease, aspect-ratio 0.2s ease;
        }
        .screen-wrap.scale-150 {
            max-width: 1020px;
        }
        .screen-wrap.scale-100 {
            max-width: 640px;
        }
        .screen-wrap.aspect-16-9 {
            aspect-ratio: 16 / 9;
            max-width: 860px;
        }
        .screen-wrap.aspect-16-9.scale-150 {
            max-width: 1140px;
        }
        #canvas {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        #canvas.pixelated {
            image-rendering: pixelated;
            image-rendering: crisp-edges;
        }

        /* Minimal Floating Toolbar */
        .toolbar {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 10px;
            padding: 6px 10px;
            background: #111827;
            border: 1px solid #1f293d;
            border-radius: 30px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
            flex-wrap: wrap;
        }
        .btn {
            background: transparent;
            color: #cbd5e1;
            border: 1px solid transparent;
            padding: 7px 14px;
            border-radius: 20px;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            user-select: none;
        }
        .btn:hover {
            background: #1e293b;
            color: #00f0ff;
            border-color: #334155;
        }
        .btn.active {
            background: #00f0ff;
            color: #040810;
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
        }
        .btn-rec.recording {
            background: #ef4444;
            color: #fff;
            animation: pulse 1s infinite alternate;
        }

        /* Collapsible Settings Drawer */
        .settings-panel {
            display: none;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
            padding: 12px 16px;
            background: #0d1424;
            border: 1px solid #1f2a44;
            border-radius: 12px;
            width: 100%;
            max-width: 800px;
        }
        .settings-panel.open {
            display: flex;
        }
        .opt-row {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }
        .opt-title {
            font-size: 0.78rem;
            color: #94a3b8;
            font-weight: 700;
            min-width: 110px;
        }
        .pill-btn {
            background: #1e293b;
            border: 1px solid #334155;
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .pill-btn:hover {
            color: #fff;
        }
        .pill-btn.active {
            background: #00f0ff;
            color: #050b14;
            border-color: #00f0ff;
            font-weight: 700;
        }
        .obs-bar {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 4px;
            padding-top: 6px;
            border-top: 1px solid #172033;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .obs-link {
            color: #f59e0b;
            font-family: monospace;
            cursor: pointer;
            text-decoration: underline;
        }
        @keyframes pulse {
            from { opacity: 0.8; }
            to { opacity: 1; transform: scale(1.03); }
        }
    </style>
</head>
<body>
    <!-- 1. Minimal Header -->
    <div class="top-bar" id="top-bar">
        <div class="top-title">🎮 TrimUI Live</div>
        <div class="top-status">
            <span class="dot"></span>
            <span id="stat-res-fps">720p • 30 FPS</span>
            <span>•</span>
            <span id="stat-scale">1.5x</span>
            <span>•</span>
            <span id="stat-fps">30 FPS</span>
            <span>•</span>
            <span id="stat-ms">&lt; 30ms</span>
        </div>
    </div>

    <!-- 2. Screen Canvas -->
    <div class="screen-wrap scale-150" id="screen-wrap" title="Nhấp đúp để Toàn màn hình" ondblclick="toggleFullscreen()">
        <canvas id="canvas" width="640" height="480"></canvas>
    </div>

    <!-- 3. Minimal Main Toolbar with 1.5x Button -->
    <div class="toolbar">
        <button class="btn" onclick="takeSnapshot()">📷 Chụp ảnh</button>
        <button class="btn btn-rec" id="btn-rec" onclick="toggleRecord()">⏺ Quay video</button>
        <button class="btn active" id="btn-scale" onclick="cycleScale()">🔍 Size: 1.5x</button>
        <button class="btn" onclick="toggleFullscreen()">⛶ Toàn màn hình</button>
        <button class="btn" id="btn-settings" onclick="toggleSettings()">⚙️ Tùy chỉnh</button>
    </div>

    <!-- 4. Collapsible Settings Drawer -->
    <div class="settings-panel" id="settings-panel">
        <div class="opt-row">
            <span class="opt-title">Kích thước khung:</span>
            <button class="pill-btn active" id="scale-btn-15" onclick="setScale('1.5x')">🔍 Phóng to 1.5x</button>
            <button class="pill-btn" id="scale-btn-10" onclick="setScale('1.0x')">1.0x (Gốc)</button>
            <button class="pill-btn" id="scale-btn-fit" onclick="setScale('fit')">Vừa màn hình (Fit)</button>
        </div>
        <div class="opt-row">
            <span class="opt-title">Độ phân giải:</span>
            <button class="pill-btn active" id="res-720" onclick="setRes('720')">⚡ 720p (Mặc định - Nét nhất)</button>
            <button class="pill-btn" id="res-480" onclick="setRes('480')">480p (Cân bằng)</button>
            <button class="pill-btn" id="res-360" onclick="setRes('360')">360p (Cực nhẹ)</button>
        </div>
        <div class="opt-row">
            <span class="opt-title">Tốc độ khung hình:</span>
            <button class="pill-btn" id="fps-60" onclick="setFPS(60)">60 FPS (Mượt)</button>
            <button class="pill-btn active" id="fps-30" onclick="setFPS(30)">30 FPS (Chuẩn)</button>
            <button class="pill-btn" id="fps-24" onclick="setFPS(24)">24 FPS (Tiết kiệm)</button>
        </div>
        <div class="opt-row">
            <span class="opt-title">Hiển thị:</span>
            <button class="pill-btn" id="btn-aspect" onclick="toggleAspect()">Tỷ lệ: 4:3</button>
            <button class="pill-btn" id="btn-pixel" onclick="togglePixel()">Nét Pixel Art: Tắt</button>
        </div>
        <div class="obs-bar">
            <span>Link phát cho OBS Studio / VLC: <span class="obs-link" onclick="copyObsLink()" title="Bấm để sao chép" id="obs-text">/stream.mjpg</span></span>
            <span style="font-size: 0.72rem; color: #475569;">Phím tắt: [F] Toàn màn hình • [S] Chụp ảnh • [R] Quay video • [Z] Đổi Size 1.5x</span>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d', { alpha: false, desynchronized: true });
        const obsLink = window.location.origin + '/stream.mjpg';
        document.getElementById('obs-text').textContent = obsLink;

        let currentRes = '720'; // Default 720p Native
        let currentFPS = 30;
        let currentScale = '1.5x'; // Default 1.5x scale
        let ws = null;
        let isRendering = false;
        let isPixel = false;
        let isAspect169 = false;
        let frameCount = 0;
        let lastFPSCheck = performance.now();

        function connectWebSocket() {
            if (ws) { try { ws.close(); } catch(e) {} }
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            ws = new WebSocket(protocol + window.location.host + '/ws');
            ws.binaryType = 'blob';

            ws.onmessage = async (event) => {
                if (isRendering) return;
                isRendering = true;

                try {
                    const t0 = performance.now();
                    const bmp = await createImageBitmap(event.data);
                    if (canvas.width !== bmp.width || canvas.height !== bmp.height) {
                        canvas.width = bmp.width;
                        canvas.height = bmp.height;
                    }
                    ctx.drawImage(bmp, 0, 0);
                    bmp.close();

                    const decodeMs = Math.round(performance.now() - t0);
                    document.getElementById('stat-ms').textContent = decodeMs + 'ms';

                    frameCount++;
                    const now = performance.now();
                    if (now - lastFPSCheck >= 1000) {
                        const actual = Math.round((frameCount * 1000) / (now - lastFPSCheck));
                        document.getElementById('stat-fps').textContent = actual + ' FPS';
                        frameCount = 0;
                        lastFPSCheck = now;
                    }
                } catch (e) {
                } finally {
                    isRendering = false;
                }
            };

            ws.onclose = () => { setTimeout(connectWebSocket, 1000); };
        }
        connectWebSocket();

        function toggleSettings() {
            const panel = document.getElementById('settings-panel');
            const btn = document.getElementById('btn-settings');
            panel.classList.toggle('open');
            btn.classList.toggle('active', panel.classList.contains('open'));
        }

        function setScale(scale) {
            currentScale = scale;
            const wrap = document.getElementById('screen-wrap');
            const topBar = document.getElementById('top-bar');
            wrap.classList.remove('scale-150', 'scale-100');
            topBar.classList.remove('scale-150');

            document.querySelectorAll('#scale-btn-15, #scale-btn-10, #scale-btn-fit').forEach(el => el.classList.remove('active'));

            if (scale === '1.5x') {
                wrap.classList.add('scale-150');
                topBar.classList.add('scale-150');
                document.getElementById('scale-btn-15').classList.add('active');
                document.getElementById('btn-scale').textContent = '🔍 Size: 1.5x';
                document.getElementById('btn-scale').classList.add('active');
                document.getElementById('stat-scale').textContent = '1.5x';
            } else if (scale === '1.0x') {
                wrap.classList.add('scale-100');
                document.getElementById('scale-btn-10').classList.add('active');
                document.getElementById('btn-scale').textContent = '🔍 Size: 1.0x';
                document.getElementById('btn-scale').classList.remove('active');
                document.getElementById('stat-scale').textContent = '1.0x';
            } else { // fit
                document.getElementById('scale-btn-fit').classList.add('active');
                document.getElementById('btn-scale').textContent = '🔍 Size: Fit';
                document.getElementById('btn-scale').classList.remove('active');
                document.getElementById('stat-scale').textContent = 'Fit';
            }
        }

        function cycleScale() {
            if (currentScale === '1.5x') setScale('1.0x');
            else if (currentScale === '1.0x') setScale('fit');
            else setScale('1.5x');
        }

        function setRes(res) {
            currentRes = res;
            document.querySelectorAll('#res-720, #res-480, #res-360').forEach(el => el.classList.remove('active'));
            document.getElementById('res-' + res).classList.add('active');
            updateDisplay();
            sendConfig();
        }

        function setFPS(fps) {
            currentFPS = fps;
            document.querySelectorAll('#fps-60, #fps-30, #fps-24').forEach(el => el.classList.remove('active'));
            document.getElementById('fps-' + fps).classList.add('active');
            updateDisplay();
            sendConfig();
        }

        function updateDisplay() {
            const resText = (currentRes === '720' ? '720p' : (currentRes === '480' ? '480p' : '360p'));
            document.getElementById('stat-res-fps').textContent = resText + ' • ' + currentFPS + ' FPS';
        }

        function sendConfig() {
            fetch('/api/set_config?res=' + currentRes + '&fps=' + currentFPS)
                .then(r => r.json())
                .catch(() => {});
        }

        function toggleAspect() {
            isAspect169 = !isAspect169;
            document.getElementById('screen-wrap').classList.toggle('aspect-16-9', isAspect169);
            document.getElementById('btn-aspect').textContent = isAspect169 ? 'Tỷ lệ: 16:9' : 'Tỷ lệ: 4:3';
        }

        function togglePixel() {
            isPixel = !isPixel;
            canvas.classList.toggle('pixelated', isPixel);
            document.getElementById('btn-pixel').textContent = isPixel ? 'Nét Pixel Art: Bật' : 'Nét Pixel Art: Tắt';
        }

        function toggleFullscreen() {
            const wrap = document.getElementById('screen-wrap');
            if (!document.fullscreenElement) {
                wrap.requestFullscreen().catch(() => {});
            } else {
                document.exitFullscreen().catch(() => {});
            }
        }

        function takeSnapshot() {
            const a = document.createElement('a');
            a.href = canvas.toDataURL('image/png');
            a.download = 'trimui_' + Date.now() + '.png';
            a.click();
        }

        let mediaRecorder = null;
        let recordedChunks = [];
        let isRecording = false;

        function toggleRecord() {
            const btn = document.getElementById('btn-rec');
            if (!isRecording) {
                const stream = canvas.captureStream(currentFPS);
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp8' });
                recordedChunks = [];

                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'video/webm' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'trimui_video_' + Date.now() + '.webm';
                    a.click();
                };

                mediaRecorder.start();
                isRecording = true;
                btn.textContent = '⏹ Dừng quay';
                btn.classList.add('recording');
            } else {
                mediaRecorder.stop();
                isRecording = false;
                btn.textContent = '⏺ Quay video';
                btn.classList.remove('recording');
            }
        }

        function copyObsLink() {
            navigator.clipboard.writeText(obsLink).then(() => {
                alert('Đã sao chép link OBS: ' + obsLink);
            }).catch(() => {});
        }

        window.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT') return;
            const key = e.key.toLowerCase();
            if (key === 'f') toggleFullscreen();
            else if (key === 's') takeSnapshot();
            else if (key === 'r') toggleRecord();
            else if (key === 'z') cycleScale();
        });
    </script>
</body>
</html>
"""

def make_ws_binary_frame(data):
    length = len(data)
    if length <= 125:
        return bytes([0x82, length]) + data
    elif length <= 65535:
        return struct.pack("!BBH", 0x82, 126, length) + data
    else:
        return struct.pack("!BBQ", 0x82, 127, length) + data

def frame_grabber_worker():
    global latest_frame, latest_frame_id

    while not stop_event.is_set():
        with active_clients_lock:
            if active_clients <= 0:
                break

        restart_grabber_event.clear()

        with config_lock:
            fps = current_fps
            res_mode = current_res

        if res_mode == "720":
            scale_filter = "format=yuvj420p"
            q_val = "6"
        elif res_mode == "360":
            scale_filter = "scale=360:-1:flags=neighbor,format=yuvj420p"
            q_val = "8"
        else: # "480"
            scale_filter = "scale=480:-1:flags=neighbor,format=yuvj420p"
            q_val = "7"

        threads_cnt = "2"

        try:
            with open("/dev/fb0", "rb") as fb:
                buf = fcntl.ioctl(fb.fileno(), FBIOGET_VSCREENINFO, bytes(160))
                res = struct.unpack("IIIIIIIIIIII", buf[:48])
                xres, yres, xres_v, yres_v, xoff, yoff = res[:6]
                bpp = res[6]
                bytes_pp = bpp // 8
                stride = xres_v * bytes_pp
                frame_size = stride * yres
                total_fb_size = stride * yres_v

                mm = mmap.mmap(fb.fileno(), total_fb_size, prot=mmap.PROT_READ)

                cmd = [
                    "/usr/bin/ffmpeg",
                    "-f", "rawvideo",
                    "-pix_fmt", "bgra",
                    "-s", f"{xres}x{yres}",
                    "-r", str(fps),
                    "-i", "pipe:0",
                    "-vf", scale_filter,
                    "-f", "image2pipe",
                    "-vcodec", "mjpeg",
                    "-dct", "fastint",
                    "-q:v", q_val,
                    "-threads", threads_cnt,
                    "pipe:1"
                ]

                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0
                )

                def stdin_pump():
                    interval = 1.0 / float(fps)
                    try:
                        while not stop_event.is_set() and not restart_grabber_event.is_set() and proc.poll() is None:
                            with active_clients_lock:
                                if active_clients <= 0:
                                    break
                            t0 = time.time()
                            vbuf = fcntl.ioctl(fb.fileno(), FBIOGET_VSCREENINFO, bytes(160))
                            vres = struct.unpack("IIIIIIIIIIII", vbuf[:48])
                            cur_offset = (vres[5] * stride) + (vres[4] * bytes_pp)
                            
                            proc.stdin.write(memoryview(mm)[cur_offset : cur_offset + frame_size])
                            proc.stdin.flush()

                            spent = time.time() - t0
                            if interval > spent:
                                time.sleep(interval - spent)
                    except Exception:
                        pass
                    finally:
                        try: proc.stdin.close()
                        except Exception: pass

                writer_t = threading.Thread(target=stdin_pump, daemon=True)
                writer_t.start()

                buffer = bytearray()
                while not stop_event.is_set() and not restart_grabber_event.is_set():
                    with active_clients_lock:
                        if active_clients <= 0:
                            break

                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    buffer.extend(chunk)

                    while True:
                        a = buffer.find(SOI)
                        if a == -1:
                            buffer.clear()
                            break
                        b = buffer.find(EOI, a + 2)
                        if b == -1:
                            if a > 0:
                                del buffer[:a]
                            break

                        next_a = buffer.find(SOI, b + 2)
                        if next_a != -1:
                            del buffer[:next_a]
                            continue

                        jpg = bytes(buffer[a:b+2])
                        del buffer[:b+2]

                        with frame_lock:
                            latest_frame = jpg
                            latest_frame_id += 1

                try:
                    proc.terminate()
                    proc.wait(timeout=0.3)
                except Exception:
                    pass

                try:
                    mm.close()
                except Exception:
                    pass

        except Exception:
            time.sleep(0.3)

def start_grabber_if_needed():
    global grabber_thread
    with active_clients_lock:
        if grabber_thread is None or not grabber_thread.is_alive():
            stop_event.clear()
            grabber_thread = threading.Thread(target=frame_grabber_worker, daemon=True)
            grabber_thread.start()

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        global active_clients, current_fps, current_res
        try:
            self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/ws":
            key = self.headers.get("Sec-WebSocket-Key", "")
            if not key:
                self.send_error(400, "Missing Sec-WebSocket-Key")
                return

            accept_val = base64.b64encode(hashlib.sha1(key.encode() + WS_MAGIC).digest()).decode()
            
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
            )
            self.request.sendall(response.encode())

            with active_clients_lock:
                active_clients += 1
            start_grabber_if_needed()

            last_sent_id = -1
            try:
                while True:
                    frame = None
                    with frame_lock:
                        if latest_frame_id != last_sent_id and latest_frame is not None:
                            frame = latest_frame
                            last_sent_id = latest_frame_id

                    if frame:
                        packet = make_ws_binary_frame(frame)
                        self.request.sendall(packet)

                    time.sleep(0.008)
            except Exception:
                pass
            finally:
                with active_clients_lock:
                    active_clients = max(0, active_clients - 1)

        elif path == "/api/set_config":
            query = urllib.parse.parse_qs(parsed.query)
            changed = False
            
            if "res" in query:
                res_val = query["res"][0]
                if res_val in ("720", "480", "360"):
                    with config_lock:
                        current_res = res_val
                    changed = True

            if "fps" in query:
                fps_val = int(query["fps"][0])
                if fps_val in (60, 30, 24):
                    with config_lock:
                        current_fps = fps_val
                    changed = True

            if changed:
                restart_grabber_event.set()
            
            resp_json = f'{{"status": "ok", "res": "{current_res}", "fps": {current_fps}}}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_json)))
            self.end_headers()
            self.wfile.write(resp_json.encode())

        elif path == "/snapshot.jpg":
            with active_clients_lock:
                active_clients += 1
            start_grabber_if_needed()
            
            frame = None
            for _ in range(25):
                with frame_lock:
                    if latest_frame is not None:
                        frame = latest_frame
                        break
                time.sleep(0.04)
            
            with active_clients_lock:
                active_clients = max(0, active_clients - 1)

            if frame:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame)))
                self.end_headers()
                self.wfile.write(frame)
            else:
                self.send_error(503, "Frame not ready")

        elif path == "/stream.mjpg":
            with active_clients_lock:
                active_clients += 1
            start_grabber_if_needed()

            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, private")
            self.send_header("Pragma", "no-cache")
            self.end_headers()

            last_sent_id = -1
            try:
                while True:
                    frame = None
                    with frame_lock:
                        if latest_frame_id != last_sent_id and latest_frame is not None:
                            frame = latest_frame
                            last_sent_id = latest_frame_id

                    if frame:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    
                    time.sleep(0.015)
            except Exception:
                pass
            finally:
                with active_clients_lock:
                    active_clients = max(0, active_clients - 1)
        else:
            self.send_error(404)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def main():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), StreamHandler)
    print(f"TrimUI 720p Native Default Streamer running on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

if __name__ == "__main__":
    main()
