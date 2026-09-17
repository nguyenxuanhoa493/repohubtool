import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Center UI for Files and Stream
# For Files tab
content = content.replace(
    '<div id="tab-view-files" class="tab-view">',
    '<div id="tab-view-files" class="tab-view" style="flex-direction: column; width: 100%;">'
)

# For Stream tab
content = content.replace(
    '<div id="tab-view-stream" class="tab-view">',
    '<div id="tab-view-stream" class="tab-view" style="flex-direction: column; width: 100%;">'
)

# 2. Inject the Stream JS Logic if missing
stream_js = """
        // ==================== STREAM JS LOGIC ====================
        function openStreamNewTab() {
            window.open('http://' + window.location.hostname + ':8088', '_blank');
        }

        async function checkStreamStatus() {
            const statusBadge = document.getElementById('stream-status-badge');
            const toggleBtn = document.getElementById('btn-stream-toggle');
            const newTabBtn = document.getElementById('btn-stream-newtab');
            if (!statusBadge || !toggleBtn) return;
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: 'ps | grep "python.*streamer.py" | grep -v grep'})
                });
                const data = await res.json();
                const out = data.output || '';
                if (out.includes('streamer.py')) {
                    statusBadge.textContent = '🟢 Đang chạy';
                    statusBadge.style.color = '#10b981';
                    toggleBtn.innerHTML = '🛑 Tắt Stream';
                    toggleBtn.className = 'btn btn-danger';
                    if (newTabBtn) newTabBtn.style.display = 'inline-flex';
                } else {
                    statusBadge.textContent = '🔴 Đã tắt';
                    statusBadge.style.color = '#ef4444';
                    toggleBtn.innerHTML = '▶️ Bật Stream ngay';
                    toggleBtn.className = 'btn btn-secondary';
                    if (newTabBtn) newTabBtn.style.display = 'none';
                }
            } catch(e) {
                statusBadge.textContent = '⚠️ Lỗi kiểm tra';
            }
        }

        async function toggleScreenStream() {
            const toggleBtn = document.getElementById('btn-stream-toggle');
            if (!toggleBtn) return;
            
            const isRunning = toggleBtn.innerHTML.includes('Tắt');
            toggleBtn.disabled = true;
            toggleBtn.innerHTML = '⏳ Đang xử lý...';
            
            try {
                if (isRunning) {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'kill -9 $(ps | awk "/streamer\\.py/ {print $1}")'})
                    });
                } else {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'nohup /mnt/SDCARD/System/bin/python3 /mnt/SDCARD/Apps/RetroHub/streamer.py > /dev/null 2>&1 &'})
                    });
                }
                setTimeout(checkStreamStatus, 1500);
            } catch(e) {
                alert('Lỗi: ' + e.message);
                checkStreamStatus();
            } finally {
                setTimeout(() => toggleBtn.disabled = false, 1500);
            }
        }
        
        // Auto-check stream status initially
        setTimeout(checkStreamStatus, 1000);
"""

if "function toggleScreenStream()" not in content:
    # insert before window.onload or end of script
    content = content.replace("        // Khởi động trang web", stream_js + "\n        // Khởi động trang web")

# Also ensure switchMainTab actually checks Stream Status when clicked!
old_switch = """            if (tab === 'games') {
                if (!allSystems.length) loadSystems();
            } else if (tab === 'store') {
                if (!storeCategories.length) loadStoreInit();
            } else if (tab === 'youtube') {
                if (!ytPlaylists.length) loadYouTubeInit();
            }"""

new_switch = """            if (tab === 'games') {
                if (!allSystems.length) loadSystems();
            } else if (tab === 'store') {
                if (!storeCategories.length) loadStoreInit();
            } else if (tab === 'youtube') {
                if (!ytPlaylists.length) loadYouTubeInit();
            } else if (tab === 'stream') {
                checkStreamStatus();
            }"""

if "tab === 'stream'" not in content:
    content = content.replace(old_switch, new_switch)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Tabs UI Fixed!")
