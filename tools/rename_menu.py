import re

# 1. Update home.py
with open("files/rh/screens/home.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace('"Retrohub Web"', '"Retrohub AI"')
content = content.replace('"RetroHub Web"', '"RetroHub AI"')
with open("files/rh/screens/home.py", "w", encoding="utf-8") as f:
    f.write(content)

# 2. Update i18n.py
with open("files/rh/i18n.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace('"Retrohub Web"', '"Retrohub AI"')
content = content.replace('"RetroHub Web"', '"RetroHub AI"')
with open("files/rh/i18n.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Renamed menu to Retrohub AI!")
