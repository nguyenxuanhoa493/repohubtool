# -*- coding: utf-8 -*-
"""Settings Screen (Language, View Mode, Wi-Fi Power, Updates, and Logs)."""

import threading
from .. import state
from ..i18n import tr
from ..services import toggle_wifi_awake
from ..updater import check_for_update
from ..version import APP_VERSION
from .base import BaseScreen


class SettingsScreen(BaseScreen):
    """Application configuration and settings dashboard."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0

    def on_enter(self, params=None):
        self.scroll_top = 0
        self.refresh_items()

    def refresh_items(self):
        v_mode_lbl = "Lưới (Grid)" if state.downloaded_view_mode == "grid" else "Danh sách (List)"
        lang_lbl = "Tiếng Việt" if state.current_lang == "VI" else "English"

        self.items = [
            {"id": "lang_toggle", "title": tr("set_lang_title"), "label": lang_lbl},
            {"id": "view_mode_toggle", "title": tr("set_view_title"), "label": v_mode_lbl},
            {"id": "wifi_awake", "title": tr("set_wifi_awake"), "type": "toggle", "state": state.wifi_awake},
            {"id": "auto_update", "title": tr("set_auto_upd"), "type": "toggle", "state": state.auto_update},
            {"id": "check_update", "title": tr("set_check_upd"), "label": f"v{APP_VERSION}"},
            {"id": "logging", "title": tr("set_logging"), "type": "toggle", "state": state.enable_logging},
            {"id": "device_id", "title": tr("set_dev_id"), "label": state.device_id},
            {"id": "back", "title": tr("back_home")}
        ]
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def get_header_title(self):
        return tr("set_title")

    def get_footer_actions(self):
        return [
            ("A", tr("footer_toggle"), (0, 230, 150), (220, 225, 235), True),
            ("B", tr("footer_back"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

        if btn_b:
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
            return True
        elif btn_down:
            if self.selected_idx < num_items - 1:
                self.selected_idx += 1
            else:
                self.selected_idx = 0
                self.scroll_top = 0
            if self.selected_idx >= self.scroll_top + max_visible:
                self.scroll_top = self.selected_idx - max_visible + 1
            return True

        if btn_a and 0 <= self.selected_idx < len(self.items):
            item = self.items[self.selected_idx]
            it_id = item.get("id")

            if it_id == "back":
                self.engine.pop_screen()
                return True

            if it_id == "lang_toggle":
                state.current_lang = "EN" if state.current_lang == "VI" else "VI"
                state.save_settings()
                self.refresh_items()
                self.engine.toast(f"Ngôn ngữ: {state.current_lang}")
            elif it_id == "view_mode_toggle":
                state.downloaded_view_mode = "list" if state.downloaded_view_mode == "grid" else "grid"
                state.save_settings()
                self.refresh_items()
            elif it_id == "wifi_awake":
                msg = toggle_wifi_awake()
                self.engine.toast(msg)
                self.refresh_items()
            elif it_id == "auto_update":
                state.auto_update = not state.auto_update
                state.save_settings()
                self.refresh_items()
            elif it_id == "logging":
                state.enable_logging = not state.enable_logging
                state.save_settings()
                self.refresh_items()
            elif it_id == "check_update":
                self.engine.toast(tr("upd_checking"))
                def _bg_check():
                    try:
                        found = check_for_update(force=True)
                        if found:
                            manifest, files = found
                            self.engine.open_modal(self.engine.update_modal, {"manifest": manifest, "files": files})
                        else:
                            self.engine.toast(tr("upd_latest"))
                    except Exception as e:
                        print(f"Manual update check error: {e}")
                        self.engine.toast(tr("upd_check_failed"))
                threading.Thread(target=_bg_check, daemon=True).start()

            return True

        return False

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
                badge_w = 160
                badge_h = 46
                badge_x = panel_x + panel_w - badge_w - 24
                badge_y = cy + (card_h - badge_h) // 2
                engine.fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                engine.draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                engine.draw_text(item["label"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 230, 255, center_x=True, center_y=True)
