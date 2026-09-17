import re

with open("gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove browseFiles call in switchMainTab
pattern1 = r"\} else if \(tab === 'files'\) \{\s*browseFiles\(currentFilePath \|\| ''\);\s*\}"
content = re.sub(pattern1, "} else if (tab === 'files') {\n                // no init needed\n            }", content)

# 2. Remove File Manager JS block
pattern2 = r"        // ==================== QUẢN LÝ FILE \(FILE MANAGER\) ====================.*?// Khởi động trang web"
content = re.sub(pattern2, "        // Khởi động trang web", content, flags=re.DOTALL)

with open("gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated JS successfully!")
