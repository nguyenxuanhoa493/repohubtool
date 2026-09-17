import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update switchMainTab to update hash
old_switch = """        function switchMainTab(tab) {
            currentTab = tab;"""
new_switch = """        function switchMainTab(tab) {
            currentTab = tab;
            // Cập nhật URL hash
            history.replaceState(null, null, '#' + tab);"""
content = content.replace(old_switch, new_switch)

# Read hash on boot
old_boot = """        // Khởi động trang web
        loadStorageStatus();
        loadSystems();"""
new_boot = """        // Khởi động trang web
        loadStorageStatus();
        
        // Đọc hash từ URL (ví dụ: /#chat)
        const initialTab = window.location.hash.replace('#', '');
        if (initialTab && document.getElementById(`nav-btn-${initialTab}`)) {
            switchMainTab(initialTab);
        } else {
            loadSystems(); // Mặc định
        }"""
content = content.replace(old_boot, new_boot)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated URL hash behavior!")
