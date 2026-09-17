import re

with open("files/rh/modals/common.py", "r", encoding="utf-8") as f:
    content = f.read()

# Update mh to 320
content = re.sub(r'mh = 290 # Compact height', r'mh = 320 # Compact height', content)

# Replace the Card 2 drawing logic
old_card2 = r"""        # 2\. Row: Connect Info Compact.*?engine\.draw_text\(val_conn, engine\.font_sub, cx \+ 185, cy \+ card2_h // 2, 255, 255, 255, center_y=True\)"""

new_card2 = """        # 2. Row: Connect Info Compact
        cy += card1_h + 12
        card2_h = 80
        engine.fill_rect(cx, cy, cw, card2_h, 18, 26, 44, 255)
        engine.draw_rect(cx, cy, cw, card2_h, 40, 56, 88, 255, thickness=1)
        
        lbl_conn = "Cách kết nối:" if vi else "How to Connect:"
        val_conn_1 = "Mở trình duyệt trên máy tính," if vi else "Open a browser on PC or phone"
        val_conn_2 = "hoặc điện thoại chung mạng Wi-Fi" if vi else "connected to the same Wi-Fi"
        
        engine.draw_text(lbl_conn, engine.font_badge, cx + 18, cy + card2_h // 2, 185, 210, 245, center_y=True)
        engine.draw_text(val_conn_1, engine.font_sub, cx + 185, cy + 28, 255, 255, 255, center_y=True)
        engine.draw_text(val_conn_2, engine.font_sub, cx + 185, cy + 56, 255, 255, 255, center_y=True)"""

content = re.sub(old_card2, new_card2, content, flags=re.DOTALL)

with open("files/rh/modals/common.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated RetroHubWebModal with v4 (2 lines) changes!")
