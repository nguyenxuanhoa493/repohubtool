import re

with open("gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r'<div id="tab-view-stream" class="tab-view">.*?</div>\s*</div>\s*</div>'

new_stream_html = """<div id="tab-view-stream" class="tab-view">
        <div style="display:flex; justify-content:center; align-items:center; height:100%; width:100%; padding:20px; flex:1;">
            <div style="background:#0f172a; border:1px solid var(--border); border-radius:16px; padding:40px; text-align:center; max-width:550px; width:100%; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                <div style="font-size:48px; margin-bottom:20px;">🖥️</div>
                <h2 style="margin:0 0 10px 0; color:#38bdf8;">Stream Màn Hình TrimUI</h2>
                <p style="color:var(--text-sub); font-size:14px; margin-bottom:30px; line-height:1.5;">
                    Phát trực tiếp màn hình máy chơi game lên trình duyệt với độ trễ siêu thấp (&lt; 30ms).
                </p>
                
                <div style="background:#0a0e1a; border:1px solid var(--border); border-radius:10px; padding:20px; margin-bottom:30px; text-align:left;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px; align-items:center;">
                        <span style="color:#94a3b8;">Trạng thái dịch vụ:</span>
                        <strong id="stream-status-badge" style="color:#94a3b8;">Đang tải...</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px; align-items:center;">
                        <span style="color:#94a3b8;">Địa chỉ Web Stream:</span>
                        <strong style="color:#10b981;" id="stream-url-disp">http://---:8088</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:14px; border-top:1px dashed var(--border); padding-top:12px; margin-top:12px; align-items:center;">
                        <span style="color:#94a3b8;">Nguồn phát OBS (MJPEG):</span>
                        <span style="color:#f59e0b; font-size:13px; font-family:monospace;" id="stream-obs-link">http://---:8088/stream.mjpg</span>
                    </div>
                </div>

                <div style="display:flex; gap:10px;">
                    <button id="btn-stream-toggle" class="btn btn-secondary" onclick="toggleScreenStream()" style="font-size:15px; padding:12px 20px; border-radius:12px; flex:1;">
                        Đang kiểm tra...
                    </button>
                    <button id="btn-stream-newtab" class="btn btn-primary" onclick="openStreamNewTab()" style="font-size:15px; padding:12px 20px; border-radius:12px; flex:1; display:none;">
                        Mở Web Stream
                    </button>
                </div>

                <script>
                    document.addEventListener("DOMContentLoaded", () => {
                        setTimeout(() => {
                            const host = window.location.hostname || '127.0.0.1';
                            const el = document.getElementById("stream-url-disp");
                            if(el) el.textContent = "http://" + host + ":8088";
                        }, 500);
                    });
                </script>
            </div>
            
            <!-- Hidden containers to satisfy existing JS updateStreamUI logic -->
            <div id="stream-off-container" style="display:none;"></div>
            <div id="stream-on-container" style="display:none;"></div>
            <iframe id="stream-frame" style="display:none;"></iframe>
        </div>
    </div>"""

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_stream_html, content, flags=re.DOTALL)
    with open("gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated stream HTML successfully!")
else:
    print("Pattern not found!")

