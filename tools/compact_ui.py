import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Make bubbles more compact
content = content.replace("bubble.style.padding = '10px 14px';", "bubble.style.padding = '8px 12px';")
content = content.replace("bubble.style.fontSize = '14.5px';", "bubble.style.fontSize = '14px';")
content = content.replace("bubble.style.lineHeight = '1.45';", "bubble.style.lineHeight = '1.4';")
content = content.replace("margin:12px 0", "margin:8px 0")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Compact UI applied!")
