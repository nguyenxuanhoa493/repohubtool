import re

with open("gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

new_tab_html = """    <div id="tab-view-files" class="tab-view">
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
    </div>"""

pattern = r'    <div id="tab-view-files" class="tab-view">.*?(?=    <!-- ================================================================= -->\n    <!-- MODALS -->)'
new_content = re.sub(pattern, new_tab_html + "\n\n", content, flags=re.DOTALL)

with open("gameweb.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Replaced tab-view-files!")
