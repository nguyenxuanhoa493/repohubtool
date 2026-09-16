# -*- coding: utf-8 -*-
"""Network & Remote Services Management Screen."""

from .. import state
from ..i18n import tr
from ..services import (is_ssh_running, toggle_ssh, get_ssh_guide_rows,
                       is_sftpgo_running, toggle_sftpgo, get_sftp_guide_rows,
                       is_adb_running, toggle_adb,
                       is_mtp_running, toggle_mtp,
                       is_streamer_running, toggle_streamer, get_stream_guide_rows,
                       is_gameweb_running, toggle_gameweb, get_gameweb_guide_rows,
                       send_ssh_info_to_telegram)
from ..sysinfo import get_device_info_rows
from ..modals.common import TwoColInfoModal
from .base import BaseScreen


class NetworkScreen(BaseScreen):
    """Network and background services dashboard."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.items = []
        self.selected_idx = 0
        self.scroll_top = 0

    def on_enter(self, params=None):
        self.scroll_top = 0
        self.refresh_services()

    def refresh_services(self):
        self.items = [
            {"id": "gameweb_toggle", "title": tr("net_gameweb_toggle"), "type": "toggle", "state": is_gameweb_running()},
            {"id": "gameweb_guide", "title": tr("net_gameweb_guide"), "label": tr("view"), "sub": True},
            {"id": "ssh_toggle", "title": tr("net_ssh_toggle"), "type": "toggle", "state": is_ssh_running()},
            {"id": "ssh_guide", "title": tr("net_ssh_guide"), "label": tr("view"), "sub": True},
            {"id": "ssh_telegram", "title": tr("net_ssh_telegram"), "label": tr("view"), "sub": True},
            {"id": "stream_toggle", "title": tr("net_stream_toggle"), "type": "toggle", "state": is_streamer_running()},
            {"id": "stream_guide", "title": tr("net_stream_guide"), "label": tr("view"), "sub": True},
            {"id": "sftpgo_toggle", "title": tr("net_sftp_toggle"), "type": "toggle", "state": is_sftpgo_running()},
            {"id": "sftpgo_guide", "title": tr("net_sftp_guide"), "label": tr("view"), "sub": True},
            {"id": "adb_toggle", "title": tr("net_adb_toggle"), "type": "toggle", "state": is_adb_running()},
            {"id": "mtp_toggle", "title": tr("net_mtp_toggle"), "type": "toggle", "state": is_mtp_running()},
            {"id": "device_info", "title": tr("device_info"), "label": tr("view")},
            {"id": "back", "title": tr("back_home")}
        ]
        main_num = 1
        for it in self.items:
            if not it.get("sub") and it.get("id") != "back":
                it["title"] = f"{main_num}. {it['title']}"
                main_num += 1

    def get_header_title(self):
        return tr("net_title")

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

            if it_id == "gameweb_toggle":
                msg = toggle_gameweb()
                self.engine.toast(msg)
                self.refresh_services()
            elif it_id == "gameweb_guide":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": "HƯỚNG DẪN GAMEWEB 8090",
                    "rows": get_gameweb_guide_rows(),
                    "style": "big"
                })
            elif it_id == "ssh_toggle":
                msg = toggle_ssh()
                self.engine.toast(msg)
                self.refresh_services()
            elif it_id == "ssh_guide":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": "HƯỚNG DẪN KẾT NỐI SSH",
                    "rows": get_ssh_guide_rows(),
                    "style": "big"
                })
            elif it_id == "ssh_telegram":
                self.engine.toast("Đang gửi thông tin sang Telegram...")
                import threading
                def _bg_send():
                    res = send_ssh_info_to_telegram()
                    msg = res[1] if isinstance(res, tuple) else res
                    self.engine.toast(msg)
                threading.Thread(target=_bg_send, daemon=True).start()
            elif it_id == "stream_toggle":
                msg = toggle_streamer()
                self.engine.toast(msg)
                self.refresh_services()
            elif it_id == "stream_guide":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": "HƯỚNG DẪN STREAMING",
                    "rows": get_stream_guide_rows(),
                    "style": "big"
                })
            elif it_id == "sftpgo_toggle":
                msg = toggle_sftpgo()
                self.engine.toast(msg)
                self.refresh_services()
            elif it_id == "sftpgo_guide":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": "HƯỚNG DẪN SFTPGO",
                    "rows": get_sftp_guide_rows(),
                    "style": "big"
                })
            elif it_id == "adb_toggle":
                msg = toggle_adb()
                self.engine.toast(msg)
                self.refresh_services()
            elif it_id == "mtp_toggle":
                msg = toggle_mtp()
                self.engine.toast(msg)
                self.refresh_services()
            elif it_id == "device_info":
                self.engine.open_modal(TwoColInfoModal(self.engine), {
                    "title": tr("device_info"),
                    "rows": get_device_info_rows(),
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

            if item.get("type") == "toggle":
                sw_x = panel_x + panel_w - 110 - 24
                sw_y = cy + (card_h - 48) // 2
                engine.draw_toggle(sw_x, sw_y, item.get("state", False))
            elif item.get("label"):
                badge_w = 130
                badge_h = 46
                badge_x = panel_x + panel_w - badge_w - 24
                badge_y = cy + (card_h - badge_h) // 2
                engine.fill_rect(badge_x, badge_y, badge_w, badge_h, 30, 42, 68, 255)
                engine.draw_rect(badge_x, badge_y, badge_w, badge_h, 65, 90, 135, 255, thickness=1)
                engine.draw_text(item["label"], engine.font_badge, badge_x + badge_w // 2, badge_y + badge_h // 2, 0, 230, 255, center_x=True, center_y=True)
