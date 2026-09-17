with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_banner = """                <div id="store-download-banner" style="display:none; background: #0f172a; border: 1px solid #0284c7; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700; margin-bottom:6px;">
                        <span id="store-dl-title" style="color:#38bdf8;">Đang tải game về máy...</span>
                        <span id="store-dl-pct" style="color:#10b981;">0%</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 8px; margin-bottom:6px;">
                        <div id="store-dl-bar" class="progress-bar-fill" style="width:0%;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-sub);">
                        <span id="store-dl-speed">Tốc độ: 0 KB/s</span>
                        <span id="store-dl-status">Đang kết nối server...</span>
                    </div>
                </div>"""

new_banner = """                <!-- Floating Pinned Download Progress Bar -->
                <div id="store-download-banner" style="display:none; position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); width: 90%; max-width: 580px; background: rgba(11, 19, 41, 0.95); border: 1px solid #0284c7; border-radius: 12px; padding: 14px 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(2,132,199,0.3); z-index: 1000; backdrop-filter: blur(10px);">
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; font-weight:700; margin-bottom:8px;">
                        <span id="store-dl-title" style="color:#38bdf8; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;">Đang tải game về máy...</span>
                        <span id="store-dl-pct" style="color:#10b981; font-weight:800; font-size:14px;">0%</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 8px; margin-bottom:8px; background:#1e293b; border-radius:4px; overflow:hidden;">
                        <div id="store-dl-bar" class="progress-bar-fill" style="width:0%; background:linear-gradient(90deg, #0284c7, #10b981); height:100%; transition:width 0.25s ease;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11.5px; color:#94a3b8;">
                        <span id="store-dl-speed">Tốc độ: 0 KB/s</span>
                        <span id="store-dl-status">Đang kết nối server...</span>
                    </div>
                </div>"""

if old_banner in content:
    content = content.replace(old_banner, new_banner)
    with open("files/gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Pinned download banner to bottom successfully!")
else:
    print("Could not find old_banner in content!")
