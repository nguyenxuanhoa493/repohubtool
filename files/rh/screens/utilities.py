# -*- coding: utf-8 -*-
"""Utilities and System Tools Screen."""

from .. import state, led
from ..i18n import tr
from ..paths import is_nextui
from ..boxart_scraper import scraper_runner
from ..cheat_manager import cheat_runner
from ..save_manager import create_save_backup, restore_save_backup
from ..sysinfo import get_device_info_rows, get_storage_info_rows
from ..j2me import is_j2me_runtime_ready, runtime_is_stale, runtime_supports_renderer
from ..modals.j2me import J2meModal
from ..modals.common import TwoColInfoModal, BoxartScraperModal, CheatModal, SaveManagerModal
from .base import BaseScreen


class UtilitiesScreen(BaseScreen):
    """System utilities and batch management tools screen."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0

    def on_enter(self, params=None):
        self.scroll_top = 0
        self.refresh_items()

    def update(self, dt):
        if scraper_runner.is_running() or cheat_runner.is_running():
            self.refresh_items()

    def refresh_items(self):
        scrape_badge = f"{scraper_runner.progress_pct}%" if scraper_runner.is_running() else tr("view")
        cheat_badge = f"{cheat_runner.progress_pct}%" if cheat_runner.is_running() else tr("view")

        is_j2me_installed = is_j2me_runtime_ready()
        j2me_label = "ĐÃ CÓ" if is_j2me_installed else "TỰ CÀI"
        if state.current_lang != "VI":
            j2me_label = "READY" if is_j2me_installed else "AUTO"
        if is_j2me_installed and runtime_is_stale():
            j2me_label = tr("j2me_needs_upgrade")

        self.items = [
            {"id": "nav_splash", "title": tr("util_item_splash"), "label": tr("view")},
            {"id": "nav_auto_scrape", "title": tr("util_auto_scrape"), "label": scrape_badge},
            {"id": "nav_save_manager", "title": tr("util_save_manager"), "label": tr("view")},
            {"id": "nav_cheats", "title": tr("util_cheat_title"), "label": cheat_badge},
            {"id": "install_j2me_emu", "title": tr("util_j2me_title"), "label": j2me_label},
        ]

        if is_j2me_installed:
            can_render = runtime_supports_renderer()
            self.items.append({"id": "nav_j2me_render", "title": tr("util_j2me_render"),
                               "label": tr("view") if can_render else tr("j2me_render_old"),
                               "sub": True})

        if not is_nextui():
            self.items.append({"id": "nav_core_sys", "title": tr("util_core_title"), "label": tr("view")})

        if led.has_led():
            self.items.append({"id": "nav_led", "title": tr("util_item_led"), "label": tr("view")})

        self.items.append({"id": "device_info", "title": tr("device_info"), "label": tr("view")})
        self.items.append({"id": "storage_status", "title": tr("util_storage_item"), "label": tr("view")})
        self.items.append({"id": "back", "title": tr("back_home")})
        main_num = 1
        for it in self.items:
            if not it.get("sub") and it.get("id") != "back":
                it["title"] = f"{main_num}. {it['title']}"
                main_num += 1

    def get_header_title(self):
        return tr("util_title")

    def get_footer_actions(self):
        return [
            ("A", tr("footer_select"), (0, 230, 150), (220, 225, 235), True),
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

            if it_id == "nav_splash":
                self.engine.push_screen("splash")
            elif it_id == "nav_auto_scrape":
                self.engine.open_modal(BoxartScraperModal(self.engine))
            elif it_id == "nav_cheats":
                self.engine.open_modal(CheatModal(self.engine))
            elif it_id == "nav_save_manager":
                self.engine.open_modal(SaveManagerModal(self.engine))
            elif it_id == "install_j2me_emu":
                self.engine.open_modal(J2meModal(self.engine))
            elif it_id == "nav_led":
                self.engine.push_screen("led")
            elif it_id == "device_info":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": tr("device_info"),
                    "rows": get_device_info_rows(),
                    "style": "big"
                })
            elif it_id == "storage_status":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": tr("util_storage_item"),
                    "rows": get_storage_info_rows(),
                    "style": "big"
                })

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
            is_sub = item.get("sub", False)

            if is_sel:
                engine.fill_rect(panel_x, cy, panel_w, card_h, 28, 44, 75, 255)
                engine.draw_rect(panel_x, cy, panel_w, card_h, 0, 246, 246, 255, thickness=3)
                engine.fill_rect(panel_x + 3, cy + 6, 8, card_h - 12, 0, 246, 246, 255)
                text_r, text_g, text_b = 255, 255, 255
            else:
                if is_sub:
                    engine.fill_rect(panel_x, cy, panel_w, card_h, 15, 22, 36, 255)
                    engine.draw_rect(panel_x, cy, panel_w, card_h, 0, 180, 220, 160, thickness=1)
                    text_r, text_g, text_b = 0, 225, 245
                else:
                    engine.fill_rect(panel_x, cy, panel_w, card_h, 19, 26, 42, 255)
                    engine.draw_rect(panel_x, cy, panel_w, card_h, 40, 54, 85, 255, thickness=1)
                    text_r, text_g, text_b = 200, 210, 225

            engine.draw_text(item["title"], engine.font_item, panel_x + 28, cy + (card_h // 2), text_r, text_g, text_b, center_y=True)

            if item.get("label"):
                badge_w = 130
                badge_h = 46
                badge_x = panel_x + panel_w - badge_w - 24
                badge_y = cy + (card_h - badge_h) // 2
                engine.fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                engine.draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                engine.draw_text(item["label"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 230, 255, center_x=True, center_y=True)
