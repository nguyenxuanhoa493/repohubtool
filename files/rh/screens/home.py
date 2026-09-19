# -*- coding: utf-8 -*-
"""Home Main Menu Screen."""

from .. import state
from ..i18n import tr
from .base import BaseScreen


class HomeScreen(BaseScreen):
    """Main dashboard menu of RetroHub."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0

    def on_enter(self, params=None):
        self.scroll_top = 0
        self.items = [
            {"id": "nav_library", "title": tr("home_item_library")},
            {"id": "nav_youtube", "title": tr("home_item_youtube")},
            {"id": "nav_retro_store", "title": tr("home_item_retro_store")},
            {"id": "nav_gameweb", "title": "Retrohub AI"},
            {"id": "nav_netplay", "title": tr("home_item_netplay")},
            {"id": "nav_network", "title": tr("home_item1")},
            {"id": "nav_utilities", "title": tr("home_item3")},
            {"id": "nav_donate", "title": tr("home_item_donate")},
            {"id": "nav_settings", "title": tr("home_item_settings")},
            {"id": "exit", "title": tr("home_item5")},
        ]
        # Number items
        for idx, it in enumerate(self.items):
            it["title"] = f"{idx + 1}. {it['title']}"

    def get_header_title(self):
        return tr("app_title")

    def get_footer_actions(self):
        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
            ("B", tr("footer_exit"), (255, 75, 75), (220, 225, 235), False),
        ]

    def handle_input(self, inputs):
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")
        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")

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

        if btn_b:
            from ..modals.common import ExitModal
            self.engine.open_modal(ExitModal(self.engine))
            return True

        if btn_a:
            item = self.items[self.selected_idx]
            item_id = item.get("id")

            if item_id == "nav_library":
                self.engine.push_screen("library")
            elif item_id == "nav_youtube":
                self.engine.push_screen("youtube")
            elif item_id == "nav_retro_store":
                self.engine.push_screen("retro_store")
            elif item_id == "nav_gameweb":
                from ..modals.common import RetroHubWebModal
                self.engine.open_modal(RetroHubWebModal(self.engine))
            elif item_id == "nav_netplay":
                from ..modals.netplay import NetplayModal
                self.engine.open_modal(NetplayModal(self.engine))
            elif item_id == "nav_network":
                self.engine.push_screen("network")
            elif item_id == "nav_utilities":
                self.engine.push_screen("utilities")
            elif item_id == "nav_donate":
                from ..modals.common import TwoColInfoModal
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": tr("donate_title"),
                    "rows": [
                        (tr("donate_bank"), "Techcombank"),
                        (tr("donate_holder"), "NGUYEN XUAN HOA"),
                        (tr("donate_acct"), "1732 8888 88"),
                        ("BuyMeACoffee", "buymeacoffee.com/xuanhoa493"),
                    ]
                })
            elif item_id == "nav_settings":
                self.engine.push_screen("settings")
            elif item_id == "exit":
                from ..modals.common import ExitModal
                self.engine.open_modal(ExitModal(self.engine))
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
