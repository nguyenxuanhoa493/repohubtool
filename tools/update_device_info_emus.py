with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the System Prompt structure section
old_sys_struct = """CẤU TRÚC HỆ THỐNG & ĐƯỜNG DẪN QUAN TRỌNG:
- Thẻ nhớ gốc: /mnt/SDCARD/
- Ứng dụng RetroHub: /mnt/SDCARD/Apps/RetroHub/
- ROMs Game: /mnt/SDCARD/Roms/<hệ_máy>/ (Ví dụ: GBA, PS, SNES)
- BIOS: /mnt/SDCARD/BIOS/
- Saves & States: /mnt/SDCARD/Saves/
- RetroArch Config: /mnt/SDCARD/RetroArch/retroarch.cfg (và thư mục /mnt/SDCARD/RetroArch/config/)"""

new_sys_struct = """CẤU TRÚC HỆ THỐNG & ĐƯỜNG DẪN QUAN TRỌNG:
- Thẻ nhớ gốc: /mnt/SDCARD/
- Trình giả lập & Launcher hệ máy: /mnt/SDCARD/Emus/<hệ_máy>/ (Ví dụ: JAVA, GBA, PS, PPSSPP, NDS)
- Core giả lập RetroArch: /mnt/SDCARD/RetroArch/.retroarch/cores/ (*.so)
- Ứng dụng & Tool độc lập: /mnt/SDCARD/Apps/ (Ví dụ: RetroHub, PortMaster, FileManager)
- ROMs Game: /mnt/SDCARD/Roms/<hệ_máy>/ (Ví dụ: GBA, PS, SNES, JAVA)
- BIOS: /mnt/SDCARD/BIOS/
- Saves & States: /mnt/SDCARD/Saves/
- RetroArch Config: /mnt/SDCARD/RetroArch/retroarch.cfg (và thư mục /mnt/SDCARD/RetroArch/config/)"""

if old_sys_struct in content:
    content = content.replace(old_sys_struct, new_sys_struct)
    print("Updated system prompt structure section!")
else:
    print("Could not find old_sys_struct!")

# 2. Update sendDeviceInfoToAI function
old_send_info = """        async function sendDeviceInfoToAI() {
            const btn = document.getElementById('btn-send-info');
            if(btn) { btn.disabled = true; btn.innerHTML = '⏳ Đang quét...'; }
            
            const cmd = "echo '--- SYSTEM INFO ---'; uname -a; echo ''; echo '--- RAM ---'; free -m; echo ''; echo '--- DISK ---'; df -h; echo ''; echo '--- ROOT DIR ---'; ls -la /mnt/SDCARD | head -n 30; echo ''; echo '--- ROMS DIRS ---'; ls -d /mnt/SDCARD/Roms/*/; echo ''; echo '--- CÁC FILE LOG QUAN TRỌNG TRÊN MÁY ---'; find /mnt/SDCARD /tmp -maxdepth 5 -type f \\( -iname \"*.log\" -o -iname \"*.out\" -o -iname \"*loi.txt\" \\) 2>/dev/null | grep -iE \"retro|hub|gameweb|nohup|imgrun\" | head -n 30";
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                const outLog = data.output || '(Lỗi đọc dữ liệu)';
                const plainText = 'Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:\n```\n' + outLog + '\n```';
                
                appendChatMessage('user', "Hãy cập nhật thông tin phần cứng và cấu trúc thư mục thực tế của máy TrimUI của tôi dưới đây để làm cơ sở tư vấn chính xác nhất.");
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
                
                const plainText = 'Đây là toàn bộ thông tin phần cứng, danh sách giả lập đã cài (/mnt/SDCARD/Emus, RetroArch Cores, Apps), cấu trúc thư mục và các file log thực tế trên máy TrimUI:\n```\n' + outLog + '\n```\nHãy ghi nhớ các giả lập và file log này để tư vấn chính xác.';
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

if old_send_info in content:
    content = content.replace(old_send_info, new_send_info)
    print("Updated sendDeviceInfoToAI successfully!")
else:
    print("Could not find old_send_info!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Saved gameweb.py successfully!")
