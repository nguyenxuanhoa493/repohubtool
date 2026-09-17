import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_prompt_line = "- Log của RetroHub App (Web Server): /mnt/SDCARD/Apps/RetroHub/gameweb.log hoặc nohup.out"
new_prompt_line = "- Log của RetroHub App (Web Server & Main App): /mnt/SDCARD/Apps/RetroHub/gameweb.log, /mnt/SDCARD/RetroHub-loi.txt, /tmp/imgrun.log, hoặc /mnt/SDCARD/RetroHub_Debug_Report.txt"

content = content.replace(old_prompt_line, new_prompt_line)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated system prompt logs!")
