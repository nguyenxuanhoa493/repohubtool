with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_str = r"safeText = safeText.replace(/\[CMD\]([\s\S]*?)\[\/CMD\]|```(?:bash|sh|shell|cmd)\n([\s\S]*?)```/gi"
new_str = r"safeText = safeText.replace(/\[CMD\]([\s\S]*?)\[\/CMD\]|```(?:[a-zA-Z0-9]+)?\n?([\s\S]*?)```/gi"

content = content.replace(old_str, new_str)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated!")
