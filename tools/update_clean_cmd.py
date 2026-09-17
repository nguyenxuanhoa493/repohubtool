with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

old_cmd_pattern = r'const cmd = \'echo "--- SYSTEM INFO ---"[\s\S]*?head -n 30\';'

new_cmd_str = r"""const cmd = 'echo "--- SYSTEM INFO ---"; uname -a; echo ""; echo "--- RAM ---"; free -m; echo ""; echo "--- DISK ---"; df -h; echo ""; echo "--- ROOT DIR ---"; ls -la /mnt/SDCARD | head -n 30; echo ""; echo "--- ROMS DIRS ---"; ls -d /mnt/SDCARD/Roms/*/ 2>/dev/null; echo ""; echo "--- GIẢ LẬP ĐÃ CÀI (/mnt/SDCARD/Emus) ---"; ls -d /mnt/SDCARD/Emus/*/ 2>/dev/null; echo ""; echo "--- APPS (/mnt/SDCARD/Apps) ---"; ls -d /mnt/SDCARD/Apps/*/ 2>/dev/null; echo ""; echo "--- RETROARCH CORES (.so) ---"; ls /mnt/SDCARD/RetroArch/.retroarch/cores/*.so 2>/dev/null | awk -F/ "{print \\$NF}"; echo ""; echo "--- CÁC FILE LOG THỰC TẾ TRÊN MÁY ---"; find /mnt/SDCARD /tmp -maxdepth 5 -type f 2>/dev/null | grep -iE "\\.(log|out)$|loi\\.txt$" | grep -v "\\._" | head -n 30';"""

content = re.sub(old_cmd_pattern, new_cmd_str, content)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated cmd to clean find command!")
