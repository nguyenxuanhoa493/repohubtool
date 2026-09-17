import re

with open("files/rh/modals/common.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace mh
content = re.sub(r'mh = 240 # Extra compact height', r'mh = 290 # Compact height', content)

# Replace button B drawing
old_btn = r'engine.draw_footer_btn\(mx \+ mw - 145, fy, foot_h - 2, "B", "Đóng" if vi else "Close", btn_color=\(255, 220, 0\), text_color=\(20, 20, 20\), is_dark_btn=False\)'
new_btn = r'engine.draw_footer_btn(mx + mw - 145, fy, foot_h - 2, "B", "Đóng" if vi else "Close", btn_color=(255, 220, 0), text_color=(255, 255, 255), is_dark_btn=True)'

content = re.sub(old_btn, new_btn, content)

with open("files/rh/modals/common.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated RetroHubWebModal with v3 changes!")
