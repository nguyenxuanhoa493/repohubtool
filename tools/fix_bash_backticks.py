with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the specific line
old_line = "đặt trong block ```bash ... ``` (hoặc [CMD]"
new_line = r"đặt trong block \`\`\`bash ... \`\`\` (hoặc [CMD]"
content = content.replace(old_line, new_line)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed!")
