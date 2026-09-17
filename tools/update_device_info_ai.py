import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the AI Prompt
old_prompt = r'(let aiChatHistory = \[\s*\{\s*role:\s*"system",\s*content:\s*`)([\s\S]*?)(`\s*\}\s*\];)'

new_prompt = """Bạn là trợ lý AI chuyên gia, trực tiếp điều hành RetroHub - hệ sinh thái quản lý game và thiết bị trên máy chơi game cầm tay TrimUI Smart Pro (nhân Linux/Busybox).
Bạn có khả năng THỰC THI LỆNH TRỰC TIẾP trên máy thông qua shell bằng cách đề xuất lệnh cho người dùng.

QUY TẮC CỐT LÕI (TUYỆT ĐỐI TUÂN THỦ):
1. LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT, ngắn gọn, đúng trọng tâm.
2. KHÔNG ĐƯỢC ĐOÁN MÒ cấu trúc file hay log. Nếu không chắc file nằm ở đâu, HÃY DÙNG LỆNH để tìm kiếm (VD: \\`find / -iname "*log*" | head -n 20\\`).
3. Mọi thao tác kiểm tra, chẩn đoán phải được chuyển thành CÂU LỆNH và đặt trong block [CMD]lệnh[/CMD] để người dùng bấm chạy, sau đó dựa vào kết quả thực tế để tư vấn tiếp.
4. KHÔNG dùng cú pháp LaTeX (như $\\rightarrow$, $\\textbf{}$), chỉ dùng Unicode (->, →, **bold**).

CẤU TRÚC HỆ THỐNG & ĐƯỜNG DẪN QUAN TRỌNG:
- Thẻ nhớ gốc: /mnt/SDCARD/
- Ứng dụng RetroHub: /mnt/SDCARD/Apps/RetroHub/
- ROMs Game: /mnt/SDCARD/Roms/<hệ_máy>/ (Ví dụ: GBA, PS, SNES)
- BIOS: /mnt/SDCARD/BIOS/
- Saves & States: /mnt/SDCARD/Saves/
- RetroArch Config: /mnt/SDCARD/RetroArch/retroarch.cfg (và thư mục /mnt/SDCARD/RetroArch/config/)

NHẬT KÝ (LOGS) & CHẨN ĐOÁN (DEBUGGING):
- Văng Game (RetroArch CRASH): Đọc /mnt/SDCARD/RetroArch/.retroarch/logs/retroarch.log 
  -> Lệnh: \\`cat /mnt/SDCARD/RetroArch/.retroarch/logs/retroarch.log | tail -n 60\\`
- Nếu cần tìm log hệ thống TrimUI/RetroHub: Hãy dùng lệnh \\`ls -la /tmp/\\` hoặc \\`find /mnt/SDCARD/Apps/RetroHub -iname "*log*"\\` để lấy danh sách file thực tế thay vì đoán bừa.
- Tiến trình & Hệ thống: \\`ps | grep retroarch\\`, \\`ps | grep gameweb\\`, \\`free -m\\` (xem RAM), \\`df -h\\` (xem dung lượng thẻ).

CÁC TRƯỜNG HỢP XỬ LÝ (PLAYBOOK):
- Python 3 trên TrimUI KHÔNG hỗ trợ module SSL. Nếu cần gọi HTTPS, phải dùng \\`curl -s -k\\`.
- Chết/Treo Web Server Port 8888: Dùng lệnh \\`kill -9 $(ps | awk '/[g]ameweb\\\\.py/ {print $1}')\\` để diệt tiến trình cũ rồi gọi lệnh chạy lại.
- Định vị file mất tích: Dùng lệnh \\`find /mnt/SDCARD/ -maxdepth 4 -iname "*từ_khóa*"\\` để tìm nhanh."""

def replacer(match):
    return match.group(1) + new_prompt + match.group(3)

content = re.sub(old_prompt, replacer, content)

# 2. Add the UI button
old_btns = """                <button class="btn btn-sm btn-secondary" style="margin-left:auto; font-size:13px; padding:8px 12px;" onclick="showSystemPrompt()" title="Xem khung nền kiến thức của AI">ℹ️ Xem Prompt</button>
                <button class="btn btn-sm btn-danger" style="margin-left:8px; font-size:13px; padding:8px 12px;" onclick="clearAIChat()">🗑️ Xóa log</button>"""

new_btns = """                <button id="btn-send-info" class="btn btn-sm btn-green" style="margin-left:auto; font-size:13px; padding:8px 12px;" onclick="sendDeviceInfoToAI()" title="Gửi cấu trúc máy cho AI">📡 Gửi thông tin máy</button>
                <button class="btn btn-sm btn-secondary" style="margin-left:8px; font-size:13px; padding:8px 12px;" onclick="showSystemPrompt()" title="Xem khung nền kiến thức của AI">ℹ️ Xem Prompt</button>
                <button class="btn btn-sm btn-danger" style="margin-left:8px; font-size:13px; padding:8px 12px;" onclick="clearAIChat()">🗑️ Xóa log</button>"""

content = content.replace(old_btns, new_btns)

# 3. Add the JS function
js_function = """
        async function sendDeviceInfoToAI() {
            const btn = document.getElementById('btn-send-info');
            if(btn) { btn.disabled = true; btn.innerHTML = '⏳ Đang quét...'; }
            
            const cmd = "echo '--- SYSTEM INFO ---'; uname -a; echo ''; echo '--- RAM ---'; free -m; echo ''; echo '--- DISK ---'; df -h; echo ''; echo '--- ROOT DIR ---'; ls -la /mnt/SDCARD | head -n 30; echo ''; echo '--- ROMS DIRS ---'; ls -d /mnt/SDCARD/Roms/*/";
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                const outLog = data.output || '(Lỗi đọc dữ liệu)';
                const plainText = `Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:\n\`\`\`\n${outLog}\n\`\`\``;
                
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
        }
"""

if "function sendDeviceInfoToAI()" not in content:
    content = content.replace("        async function executeAiCommand", js_function + "\n        async function executeAiCommand")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated prompt and injected Send Device Info button!")
