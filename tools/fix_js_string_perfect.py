import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r'const plainText = "Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:[\s\S]*?outLog \+ "[\s\S]*?";',
    'const plainText = "Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:\\n```\\n" + outLog + "\\n```";',
    content
)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
