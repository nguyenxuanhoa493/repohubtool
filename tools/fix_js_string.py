with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

bad_str = "const plainText = `Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:\n```\n${outLog}\n````;"
good_str = 'const plainText = "Đây là thông tin hệ thống và cấu trúc thư mục hiện tại của máy TrimUI:\\n```\\n" + outLog + "\\n```";'

content = content.replace(bad_str, good_str)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
