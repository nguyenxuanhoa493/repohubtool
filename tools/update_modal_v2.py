import re

with open("files/rh/modals/common.py", "r", encoding="utf-8") as f:
    content = f.read()

new_modal_code = """class RetroHubWebModal(BaseModal):
    \"\"\"Modal to manage and view RetroHub Web status.\"\"\"

    def __init__(self, engine=None):
        super().__init__(engine)
        self.ip = "127.0.0.1"
        self.is_running = False

    def open(self, data=None):
        super().open(data)
        from ..services import is_gameweb_running, toggle_gameweb, get_ip
        self.ip = get_ip()
        self.is_running = is_gameweb_running()
        if not self.is_running:
            toggle_gameweb()
            self.is_running = is_gameweb_running()

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

        if btn_b:
            self.close()
            return True

        if btn_a:
            from ..services import toggle_gameweb, is_gameweb_running
            msg = toggle_gameweb()
            self.is_running = is_gameweb_running()
            if self.engine:
                self.engine.toast(msg)
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        # Dim backdrop
        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 220)

        vi = state.current_lang == "VI"
        
        head_h = 58
        foot_h = 48
        
        mw = min(state.SCREEN_W - 64, 820)
        mh = 240 # Extra compact height

        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Outer Container & Glow Border
        engine.fill_rect(mx, my, mw, mh, 14, 20, 34, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        engine.fill_rect(mx + 2, my + 2, mw - 4, head_h - 4, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + head_h - 2, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text("RETROHUB WEB MANAGER", engine.font_title, mx + 28, my + head_h // 2, 0, 246, 246, center_y=True)

        # Content Area
        cx = mx + 24
        cw = mw - 48
        
        # 1. Row: Just the HUGE IP Address
        cy = my + head_h + 16
        card1_h = 80
        engine.fill_rect(cx, cy, cw, card1_h, 18, 26, 44, 255)
        engine.draw_rect(cx, cy, cw, card1_h, 40, 56, 88, 255, thickness=1)
        
        # Accent stripe
        stripe_col = (0, 230, 150) if self.is_running else (255, 75, 75)
        engine.fill_rect(cx + 2, cy + 2, 4, card1_h - 4, stripe_col[0], stripe_col[1], stripe_col[2], 255)

        ip_url = f"http://{self.ip}:8888" if self.is_running else ("Dịch vụ đang tắt" if vi else "Service is stopped")
        ip_col = (255, 220, 0) if self.is_running else (150, 150, 150)
        
        # IP text huge! Centered perfectly inside card
        font_ip = engine.font_huge if self.is_running else engine.font_item
        engine.draw_text(ip_url, font_ip, cx + cw // 2, cy + card1_h // 2, ip_col[0], ip_col[1], ip_col[2], center_x=True, center_y=True)

        # 2. Row: Connect Info Compact
        cy += card1_h + 12
        card2_h = 56
        engine.fill_rect(cx, cy, cw, card2_h, 18, 26, 44, 255)
        engine.draw_rect(cx, cy, cw, card2_h, 40, 56, 88, 255, thickness=1)
        
        lbl_conn = "Cách kết nối:" if vi else "How to Connect:"
        val_conn = "Mở trình duyệt trên máy tính, điện thoại chung Wi-Fi" if vi else "Open Chrome/Safari/Edge on PC/phone on same Wi-Fi"
        engine.draw_text(lbl_conn, engine.font_badge, cx + 18, cy + card2_h // 2, 185, 210, 245, center_y=True)
        engine.draw_text(val_conn, engine.font_sub, cx + 185, cy + card2_h // 2, 255, 255, 255, center_y=True)

        # Footer Bar
        fy = my + mh - foot_h
        engine.fill_rect(mx + 2, fy, mw - 4, foot_h - 2, 16, 22, 36, 255)
        engine.fill_rect(mx + 2, fy, mw - 4, 1, 38, 52, 80, 255)

        fx = mx + 24
        toggle_label = "Tắt dịch vụ" if self.is_running else "Bật dịch vụ"
        if not vi:
            toggle_label = "Stop Web" if self.is_running else "Start Web"
        btn_col = (255, 75, 75) if self.is_running else (0, 230, 150)
        
        fx = engine.draw_footer_btn(fx, fy, foot_h - 2, "A", toggle_label, btn_col, is_dark_btn=False)

        # Close button B (Yellow)
        engine.draw_footer_btn(mx + mw - 145, fy, foot_h - 2, "B", "Đóng" if vi else "Close", btn_color=(255, 220, 0), text_color=(20, 20, 20), is_dark_btn=False)
"""

pattern = r"class RetroHubWebModal\(BaseModal\):.*"
new_content = re.sub(pattern, new_modal_code, content, flags=re.DOTALL)

with open("files/rh/modals/common.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated RetroHubWebModal with v2 changes!")
