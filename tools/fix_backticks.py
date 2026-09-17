import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace inner backticks inside the specific aiChatHistory block
# To be safe, we extract the block from `Bạn là trợ lý AI` to `tiếp!` }
pattern = r'(content:\s*`Bạn là trợ lý AI.*?)(`)(\s*\})'

def replace_inner(m):
    text = m.group(1)
    # the group(1) includes the first backtick? Wait, pattern says `Bạn...
    # Actually, `(.*?)` is dangerous.
    return m.group(0)

# Better: just replace the specific strings
content = content.replace("`cat /mnt/SDCARD/RetroArch/retroarch.log | tail -n 50`", "'cat /mnt/SDCARD/RetroArch/retroarch.log | tail -n 50'")
content = content.replace("(`ls -la /mnt/SDCARD/Saves/`)", "('ls -la /mnt/SDCARD/Saves/')")
content = content.replace("`ls -la /mnt/SDCARD/Roms/<hệ_máy>/`", "'ls -la /mnt/SDCARD/Roms/<hệ_máy>/'")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed backticks!")
