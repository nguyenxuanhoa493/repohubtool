with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

content = re.sub(
    r"const plainText = 'Đây là toàn bộ thông tin[\s\S]*?Hãy ghi nhớ các giả lập và file log này để tư vấn chính xác\.';",
    r"const plainText = 'Đây là toàn bộ thông tin phần cứng, danh sách giả lập đã cài (/mnt/SDCARD/Emus, RetroArch Cores, Apps), cấu trúc thư mục và các file log thực tế trên máy TrimUI:\\n```\\n' + outLog + '\\n```\\nHãy ghi nhớ các giả lập và file log này để tư vấn chính xác.';",
    content
)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed plainText string escaping!")
