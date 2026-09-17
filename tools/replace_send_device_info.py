with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

new_send_info = """        async function sendDeviceInfoToAI() {
            const btn = document.getElementById('btn-send-info');
            if(btn) { btn.disabled = true; btn.innerHTML = '⏳ Đang quét...'; }
            
            const cmd = "echo '--- SYSTEM INFO ---'; uname -a; echo ''; echo '--- RAM ---'; free -m; echo ''; echo '--- DISK ---'; df -h; echo ''; echo '--- ROOT DIR ---'; ls -la /mnt/SDCARD | head -n 30; echo ''; echo '--- ROMS DIRS ---'; ls -d /mnt/SDCARD/Roms/*/ 2>/dev/null; echo ''; echo '--- GIẢ LẬP ĐÃ CÀI (/mnt/SDCARD/Emus) ---'; ls -d /mnt/SDCARD/Emus/*/ 2>/dev/null; echo ''; echo '--- APPS (/mnt/SDCARD/Apps) ---'; ls -d /mnt/SDCARD/Apps/*/ 2>/dev/null; echo ''; echo '--- RETROARCH CORES (.so) ---'; ls /mnt/SDCARD/RetroArch/.retroarch/cores/*.so 2>/dev/null | awk -F/ '{print $NF}'; echo ''; echo '--- CÁC FILE LOG THỰC TẾ TRÊN MÁY ---'; find /mnt/SDCARD /tmp -maxdepth 5 -type f \\( -iname \"*.log\" -o -iname \"*.out\" -o -iname \"*loi.txt\" \\) 2>/dev/null | grep -iE \"retro|hub|gameweb|nohup|imgrun\" | head -n 30";
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                const outLog = data.output || '(Lỗi đọc dữ liệu)';
                const safeLog = outLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #34d399; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span>📡</span> Đã nạp cấu hình & giả lập máy cho AI
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem chi tiết)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeLog}</div>
                </details>`;
                
                appendChatMessage('user', htmlText, true, true);
                
                const plainText = 'Đây là toàn bộ thông tin phần cứng, danh sách giả lập đã cài (/mnt/SDCARD/Emus, RetroArch Cores, Apps), cấu trúc thư mục và các file log thực tế trên máy TrimUI:\\n```\\n' + outLog + '\\n```\\nHãy ghi nhớ các giả lập và file log này để tư vấn chính xác.';
                aiChatHistory.push({ role: 'user', content: plainText });
                
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                
                doHeadlessAiFetch();
            } catch (e) {
                alert('Lỗi lấy thông tin: ' + e.message);
            } finally {
                if(btn) { btn.disabled = false; btn.innerHTML = '📡 Gửi thông tin máy'; }
            }
        }"""

content = re.sub(r'        async function sendDeviceInfoToAI\(\) \{[\s\S]*?\n        \}\n', new_send_info + "\n", content, count=1)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Replaced sendDeviceInfoToAI successfully!")
