import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add nav buttons
nav_pattern = r'                <button id="nav-btn-youtube".*?                </button>'
nav_replacement = """                <button id="nav-btn-youtube" class="nav-tab" onclick="switchMainTab('youtube')">
                    <span>📺</span> Quản lý playlist YouTube
                </button>
                <button id="nav-btn-files" class="nav-tab" onclick="switchMainTab('files')">
                    <span>📁</span> Quản lý file
                </button>
                <button id="nav-btn-stream" class="nav-tab" onclick="switchMainTab('stream')">
                    <span>🖥️</span> Truyền màn hình
                </button>
                <button id="nav-btn-chat" class="nav-tab" onclick="switchMainTab('chat')">
                    <span>🤖</span> AI Chatbot
                </button>"""
content = re.sub(nav_pattern, nav_replacement, content, flags=re.DOTALL)

# 2. Add Tab HTML contents
# We will append them before <!-- MODALS -->
tab_htmls = """    <!-- TAB FILES -->
    <div id="tab-view-files" class="tab-view">
        <div style="display:flex; justify-content:center; align-items:center; height:100%; padding:20px;">
            <div style="background:#0f172a; border:1px solid var(--border); border-radius:16px; padding:40px; text-align:center; max-width:550px; width:100%; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
                <div style="font-size:48px; margin-bottom:20px;">📁</div>
                <h2 style="margin:0 0 10px 0; color:#38bdf8;">Web Quản Lý File (SFTPGo)</h2>
                <p style="color:var(--text-sub); font-size:14px; margin-bottom:30px; line-height:1.5;">
                    Truy cập, quản lý toàn bộ tệp tin trên thẻ nhớ qua giao diện Web chuyên nghiệp.
                </p>
                <div style="background:#0a0e1a; border:1px solid var(--border); border-radius:10px; padding:20px; margin-bottom:30px; text-align:left;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px;">
                        <span style="color:#94a3b8;">Địa chỉ Web (Trình duyệt):</span>
                        <strong style="color:#10b981;" id="files-sftp-url-disp">Đang tải...</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px;">
                        <span style="color:#94a3b8;">Tài khoản (Web):</span>
                        <strong style="color:#fff;">root</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px; font-size:14px;">
                        <span style="color:#94a3b8;">Mật khẩu (Web):</span>
                        <strong style="color:#fff;">root</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:14px; border-top:1px dashed var(--border); padding-top:12px; margin-top:12px;">
                        <span style="color:#94a3b8;">Kết nối qua SFTP (WinSCP):</span>
                        <span style="color:#e2e8f0; font-size:13px;">Cổng: <strong style="color:#f59e0b;">2022</strong> (user/pass: <strong>trimui</strong>)</span>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="window.open('http://' + window.location.hostname + ':8080', '_blank')" style="font-size:16px; padding:12px 30px; border-radius:12px; width:100%; justify-content:center;">
                    Mở Web Quản Lý File (Sang Tab mới)
                </button>
                <script>
                    document.addEventListener("DOMContentLoaded", () => {
                        setTimeout(() => {
                            document.getElementById("files-sftp-url-disp").textContent = "http://" + window.location.hostname + ":8080";
                        }, 500);
                    });
                </script>
            </div>
        </div>
    </div>

    <!-- TAB STREAM -->
    <div id="tab-view-stream" class="tab-view">
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
                            const obs = document.getElementById("stream-obs-link");
                            if(obs) obs.textContent = "http://" + host + ":8088/stream.mjpg";
                        }, 500);
                    });
                </script>
            </div>
        </div>
    </div>
"""

insert_pattern = r'    <!-- ================================================================= -->\n    <!-- MODALS -->'
if "<!-- TAB FILES -->" not in content:
    content = content.replace("    <!-- ================================================================= -->\n    <!-- MODALS -->", tab_htmls + "\n    <!-- ================================================================= -->\n    <!-- MODALS -->")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Tabs restored successfully!")
