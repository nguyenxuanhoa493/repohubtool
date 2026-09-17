import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update switchMainTab
old_switch = """        function switchMainTab(tab) {
            currentTab = tab;"""
new_switch = """        function switchMainTab(tab) {
            currentTab = tab;
            window.history.replaceState(null, '', '#' + tab);"""
content = content.replace(old_switch, new_switch)

# 2. Update initialization
old_init = """        // Khởi động trang web
        loadStorageStatus();
        loadSystems();"""
new_init = """        // Khởi động trang web
        const initialTab = window.location.hash.replace('#', '');
        const validTabs = ['games', 'store', 'youtube', 'stream', 'files', 'chat'];
        if (validTabs.includes(initialTab)) {
            switchMainTab(initialTab);
        } else {
            switchMainTab('games');
        }
        
        loadStorageStatus();
        loadSystems();"""
content = content.replace(old_init, new_init)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Added URL hash sync!")
