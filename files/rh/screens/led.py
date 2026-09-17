# -*- coding: utf-8 -*-
"""LED Light Controls and Themes Screen."""

from .. import state, led, ledconf, ledctl, ledthemes
from ..i18n import tr
from .base import BaseScreen


class LedScreen(BaseScreen):
    """LED lighting effects and theme selection screen."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.view_mode = "main"  # main or theme_pick
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0
        self.led_cfg = {}
        self.led_preview = None

    def on_enter(self, params=None):
        self.led_cfg = ledconf.load()
        self.led_cfg = ledctl.reconcile(self.led_cfg)
        self.show_main()

    def show_main(self):
        self.view_mode = "main"
        self.selected_idx = 0
        self.scroll_top = 0
        self.items = [
            {"id": "led_toggle", "title": tr("led_enable"), "type": "toggle", "state": self.led_cfg.get("enabled", False)},
            {"id": "nav_led_theme", "title": tr("led_theme"), "label": ledthemes.name(self.led_cfg.get("theme"), state.current_lang)},
            {"id": "led_brightness", "title": tr("led_brightness"), "label": f"{self.led_cfg.get('brightness', 60)}%"},
            {"id": "led_speed", "title": tr("led_speed"), "label": tr("led_speed_" + ledconf.speed_name(self.led_cfg.get("speed", 1.0)))},
            {"id": "back", "title": tr("back_home")}
        ]
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def show_themes(self):
        self.view_mode = "theme_pick"
        self.selected_idx = 0
        self.scroll_top = 0
        cur_theme = self.led_cfg.get("theme")
        self.items = []
        for t_id in ledthemes.THEME_ORDER:
            t_name = ledthemes.name(t_id, state.current_lang)
            self.items.append({
                "id": f"theme_{t_id}",
                "theme_id": t_id,
                "title": t_name,
                "label": tr("led_theme_cur") if t_id == cur_theme else ""
            })
        self.items.append({"id": "back", "title": tr("back_home")})
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def get_header_title(self):
        return tr("led_theme_title") if self.view_mode == "theme_pick" else tr("led_title")

    def get_footer_actions(self):
        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

        if btn_b:
            if self.view_mode == "theme_pick":
                # Revert preview
                ledconf.save(self.led_cfg)
                self.show_main()
            else:
                self.engine.pop_screen()
            return True

        num_items = len(self.items)
        if num_items == 0:
            return False
        max_visible = 6

        if btn_up:
            if self.selected_idx > 0:
                self.selected_idx -= 1
            else:
                self.selected_idx = num_items - 1
                self.scroll_top = max(0, num_items - max_visible)
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx
            if self.view_mode == "theme_pick":
                self.apply_live_preview()
            return True
        elif btn_down:
            if self.selected_idx < num_items - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
                self.scroll_top = 0
            if self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            if self.view_mode == "theme_pick":
                self.apply_live_preview()
            return True

        if btn_a and 0 <= self.selected_idx < len(self.items):
            item = self.items[self.selected_idx]
            it_id = item.get("id")

            if it_id == "back":
                if self.view_mode == "theme_pick":
                    ledconf.save(self.led_cfg)
                    self.show_main()
                else:
                    self.engine.pop_screen()
                return True

            if self.view_mode == "main":
                if it_id == "led_toggle":
                    en = not self.led_cfg.get("enabled", False)
                    self.led_cfg["enabled"] = en
                    ledconf.save(self.led_cfg)
                    if en and not ledctl.is_running():
                        ledctl.start()
                    elif not en and ledctl.is_running():
                        ledctl.stop()
                    self.show_main()
                elif it_id == "nav_led_theme":
                    self.show_themes()
                elif it_id == "led_brightness":
                    cur_b = self.led_cfg.get("brightness", 60)
                    new_b = 100 if cur_b <= 20 else (cur_b - 20)
                    self.led_cfg["brightness"] = new_b
                    ledconf.save(self.led_cfg)
                    self.show_main()
                elif it_id == "led_speed":
                    cur_s = self.led_cfg.get("speed", 1.0)
                    speeds = [0.5, 1.0, 2.0]
                    idx = speeds.index(cur_s) if cur_s in speeds else 1
                    new_s = speeds[(idx + 1) % len(speeds)]
                    self.led_cfg["speed"] = new_s
                    ledconf.save(self.led_cfg)
                    self.show_main()

            elif self.view_mode == "theme_pick":
                t_id = item.get("theme_id")
                if t_id:
                    self.led_cfg = ledconf.apply_theme(self.led_cfg, t_id)
                    ledconf.save(self.led_cfg)
                    self.engine.toast(f"Đã đổi bộ màu LED: {ledthemes.name(t_id, state.current_lang)}")
                    self.show_main()

            return True

        return False

    def apply_live_preview(self):
        if self.view_mode == "theme_pick" and 0 <= self.selected_idx < len(self.items):
            item = self.items[self.selected_idx]
            t_id = item.get("theme_id")
            if t_id and t_id != self.led_preview:
                self.led_preview = t_id
                if self.led_cfg.get("enabled") and not ledctl.is_running():
                    ledctl.start()
                ledconf.save(ledconf.apply_theme(self.led_cfg, t_id))

    def render(self, engine):
        num_items = len(self.items)
        panel_margin = 40
        panel_x = panel_margin
        panel_w = state.SCREEN_W - (panel_margin * 2)

        card_h = 76
        gap = 10
        start_y = 64 + 14
        max_visible = 6

        max_scroll = max(0, num_items - max_visible)
        if self.selected_idx < self.scroll_top:
            self.scroll_top = self.selected_idx
        elif self.selected_idx >= self.scroll_top + max_visible:
            self.scroll_top = self.selected_idx - max_visible + 1
        self.scroll_top = max(0, min(max_scroll, self.scroll_top))

        visible_items = self.items[self.scroll_top : self.scroll_top + max_visible]

        for i, item in enumerate(visible_items):
            actual_idx = self.scroll_top + i
            cy = start_y + i * (card_h + gap)
            is_sel = (actual_idx == self.selected_idx)

            if is_sel:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 28, 44, 75, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                text_r, text_g, text_b = 255, 255, 255
            else:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 19, 26, 42, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 40, 54, 85, 255, thickness=1)
                text_r, text_g, text_b = 200, 210, 225

            engine.draw_text(item["title"], engine.font_item, panel_x + 28, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

            if item.get("type") == "toggle":
                sw_x = panel_x + panel_w - 110 - 24
                sw_y = cy + (card_h - 48) // 2
                engine.draw_toggle(sw_x, sw_y, item.get("state", False))
            elif item.get("label"):
                badge_w = 150
                badge_h = 46
                badge_x = panel_x + panel_w - badge_w - 24
                badge_y = cy + (card_h - badge_h) // 2
                engine.fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                engine.draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                engine.draw_text(item["label"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 230, 255, center_x=True, center_y=True)
