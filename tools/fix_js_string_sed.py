with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
# Find the assignment line to `const plainText` and replace it entirely.
# Currently it spans multiple lines.
content = re.sub(
    r'const plainText = "Đây là thông tin.*?\+ outLog \+ ".*?";',
    r"const plainText = 'Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:\\n```\\n' + outLog + '\\n```';",
    content,
    flags=re.DOTALL
)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
