with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_cmd = "const cmd = \"echo '--- SYSTEM INFO ---'; uname -a; echo ''; echo '--- RAM ---'; free -m; echo ''; echo '--- DISK ---'; df -h; echo ''; echo '--- ROOT DIR ---'; ls -la /mnt/SDCARD | head -n 30; echo ''; echo '--- ROMS DIRS ---'; ls -d /mnt/SDCARD/Roms/*/\";"

new_cmd = "const cmd = \"echo '--- SYSTEM INFO ---'; uname -a; echo ''; echo '--- RAM ---'; free -m; echo ''; echo '--- DISK ---'; df -h; echo ''; echo '--- ROOT DIR ---'; ls -la /mnt/SDCARD | head -n 30; echo ''; echo '--- ROMS DIRS ---'; ls -d /mnt/SDCARD/Roms/*/; echo ''; echo '--- CÁC FILE LOG QUAN TRỌNG TRÊN MÁY ---'; find /mnt/SDCARD /tmp -maxdepth 5 -type f \\\\( -iname \\\"*.log\\\" -o -iname \\\"*.out\\\" -o -iname \\\"*loi.txt\\\" \\\\) 2>/dev/null | grep -iE \\\"retro|hub|gameweb|nohup|imgrun\\\" | head -n 30\";"

if old_cmd in content:
    content = content.replace(old_cmd, new_cmd)
    with open("files/gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated log search!")
else:
    print("Could not find old_cmd")

