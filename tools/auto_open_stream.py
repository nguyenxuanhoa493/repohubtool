import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_toggle = """                } else {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'nohup /mnt/SDCARD/System/bin/python3 /mnt/SDCARD/Apps/RetroHub/streamer.py > /dev/null 2>&1 &'})
                    });
                }
                setTimeout(checkStreamStatus, 1500);"""

new_toggle = """                } else {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'nohup /mnt/SDCARD/System/bin/python3 /mnt/SDCARD/Apps/RetroHub/streamer.py > /dev/null 2>&1 &'})
                    });
                    
                    // Tự động mở tab mới khi bật stream thành công (sau 1.5s để server kịp khởi động)
                    setTimeout(() => {
                        window.open('http://' + window.location.hostname + ':8088', '_blank');
                    }, 1500);
                }
                setTimeout(checkStreamStatus, 1500);"""

content = content.replace(old_toggle, new_toggle)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated auto-open stream tab!")
