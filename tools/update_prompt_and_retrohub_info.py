with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

# 1. Update the AI System Prompt to purely focus on core working rules & principles
old_prompt_pattern = r'(let aiChatHistory = \[\s*\{\s*role:\s*"system",\s*content:\s*`)([\s\S]*?)(`\s*\}\s*\];)'

new_prompt_content = """Bạn là trợ lý AI chuyên gia điều hành hệ sinh thái RetroHub và thiết bị TrimUI Smart Pro (Linux/Busybox aarch64).
Bạn có quyền thực thi lệnh trực tiếp trên máy thông qua shell bằng cách đề xuất lệnh cho người dùng bấm chạy.

QUY TẮC LÀM VIỆC CỐT LÕI (BẮT BUỘC TUÂN THỦ):
1. LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT, ngắn gọn, súc tích, đi thẳng vào giải pháp kỹ thuật.
2. TUYỆT ĐỐI KHÔNG ĐOÁN MÒ: Không tự suy diễn đường dẫn file, file log hay cấu hình hệ thống khi chưa được cung cấp hoặc chưa kiểm chứng. Mọi thông tin chưa rõ PHẢI được điều tra bằng câu lệnh thực tế.
3. HÀNH ĐỘNG BẰNG CÂU LỆNH: Mọi thao tác kiểm tra, chẩn đoán, đọc log, sửa lỗi PHẢI viết dưới dạng câu lệnh shell trong block \\`\\`\\`bash ... \\`\\`\\` (hoặc [CMD]...[/CMD]) để người dùng bấm chạy, sau đó dựa vào kết quả thực tế để tư vấn tiếp.
4. KHÔNG dùng cú pháp LaTeX (như $\\rightarrow$, $\\textbf{}$), chỉ dùng ký tự Unicode (->, →, **bold**).

ĐẶC THÙ HỆ THỐNG CẦN NHỚ:
- Python 3 trên máy KHÔNG hỗ trợ module SSL: Tuyệt đối không dùng code Python import ssl. Các tác vụ mạng HTTPS phải dùng \\`curl -s -k\\`.
- Môi trường Shell là Busybox/Ash: Ưu tiên các lệnh tiêu chuẩn, tránh dùng các flag nâng cao không được Busybox hỗ trợ.
- Khi người dùng gửi "Thông tin máy", hãy đọc kỹ phần cứng, danh sách giả lập (/Emus), Apps, RetroArch Cores, cấu trúc RetroHub và các file log thực tế để đưa ra câu lệnh chính xác 100%."""

def repl_prompt(match):
    return match.group(1) + new_prompt_content + match.group(3)

content = re.sub(old_prompt_pattern, repl_prompt, content, count=1)

# 2. Update sendDeviceInfoToAI command to include RetroHub structure
old_cmd_pattern = r'const cmd = \'echo "--- SYSTEM INFO ---"[\s\S]*?head -n 30\';'

new_cmd_str = r"""const cmd = 'echo "--- SYSTEM INFO ---"; uname -a; echo ""; echo "--- RAM ---"; free -m; echo ""; echo "--- DISK ---"; df -h; echo ""; echo "--- ROOT DIR ---"; ls -la /mnt/SDCARD | head -n 30; echo ""; echo "--- ROMS DIRS ---"; ls -d /mnt/SDCARD/Roms/*/ 2>/dev/null; echo ""; echo "--- GIẢ LẬP ĐÃ CÀI (/mnt/SDCARD/Emus) ---"; ls -d /mnt/SDCARD/Emus/*/ 2>/dev/null; echo ""; echo "--- APPS (/mnt/SDCARD/Apps) ---"; ls -d /mnt/SDCARD/Apps/*/ 2>/dev/null; echo ""; echo "--- CẤU TRÚC APP RETROHUB ---"; find /mnt/SDCARD/Apps/RetroHub -maxdepth 2 2>/dev/null | grep -v "/\\._" | head -n 45; echo ""; echo "--- RETROARCH CORES (.so) ---"; ls /mnt/SDCARD/RetroArch/.retroarch/cores/*.so 2>/dev/null | awk -F/ "{print \\$NF}"; echo ""; echo "--- CÁC FILE LOG THỰC TẾ TRÊN MÁY ---"; find /mnt/SDCARD /tmp -maxdepth 5 -type f 2>/dev/null | grep -iE "\\.(log|out)$|loi\\.txt$" | grep -v "\\._" | head -n 30';"""

content = re.sub(old_cmd_pattern, new_cmd_str, content, count=1)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Prompt & command updated successfully!")
