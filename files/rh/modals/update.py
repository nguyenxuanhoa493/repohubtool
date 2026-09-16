# -*- coding: utf-8 -*-
"""OTA Self-Update Modal Dialog."""

import os
import threading
from .. import state
from ..i18n import tr
from ..paths import APP_DIR
from ..version import APP_VERSION, is_newer
from ..updater import (apply_catalog, apply_runtime, apply_update,
                      CATALOG_FAILED, catalog_entry, catalog_pending, CatalogError,
                      check_for_update, download_catalog, download_runtime, download_update,
                      release_note, request_restart, RUNTIME_FAILED, runtime_pending,
                      RuntimeUpdateError, skip_version)
from ..storage import human_bytes
from ..j2me import ensure_latest_j2me_installed
from .base import BaseModal


class UpdateModal(BaseModal):
    """Full-featured OTA Update Dialog."""

    def __init__(self, engine=None):
        super().__init__(engine)
        self.manifest = None
        self.files = []
        self.selected_opt = 0  # 0: Install, 1: Later, 2: Skip
        self.busy = False
        self.failed = False
        self.restart = False
        self.status = ""
        self.cat_only = False
        self.scroll_top = 0
        self.progress_pct = 0.0
        self.progress_done = 0
        self.progress_total = 0
        self.progress_file = ""
        self.phase_title = ""

    def open(self, data=None):
        data = data or {}
        self.manifest = data.get("manifest")
        self.files = data.get("files") or []
        self.cat_only = data.get("cat_only", False)
        if self.manifest and not self.cat_only:
            self.cat_only = not is_newer(self.manifest.get("version", ""), APP_VERSION)
        self.selected_opt = 0
        self.busy = False
        self.failed = False
        self.restart = False
        self.status = ""
        self.scroll_top = 0
        self.progress_pct = 0.0
        self.progress_done = 0
        self.progress_total = len(self.files) if self.files else 0
        self.progress_file = ""
        self.phase_title = ""
        super().open(data)

    def get_labels(self):
        return [tr("upd_install_now"), tr("upd_remind_later"), tr("upd_skip_version")]

    def run_update_thread(self):
        m = self.manifest
        files = self.files
        total_steps = len(files)
        self.progress_total = total_steps
        self.progress_done = 0
        self.progress_pct = 0.0
        self.phase_title = "Đang tải tệp cập nhật..."

        def prog(done, total, path):
            self.progress_done = done
            self.progress_total = total
            self.progress_file = os.path.basename(path) if path else ""
            if total > 0:
                self.progress_pct = min(0.92, done / total)
            self.status = f"Tải {done}/{total}: {self.progress_file}"

        ok = False
        try:
            if download_update(m, files, progress=prog):
                self.phase_title = "Đang cài đặt & thay thế tệp..."
                self.status = tr("upd_installing")
                self.progress_pct = 0.95
                ok = apply_update(m, files)
        except Exception as e:
            print(f"Update error: {e}")

        if ok:
            try:
                rt_pending = runtime_pending(m)
            except Exception as e:
                print(f"Runtime check error: {e}")
                rt_pending = []
            if rt_pending:
                def rt_prog(done, total, path):
                    self.phase_title = "Đang tải môi trường Runtime..."
                    self.progress_file = os.path.basename(path) if path else ""
                    self.status = f"{tr('upd_rt_downloading')} {done}/{total}"
                    if total > 0:
                        self.progress_pct = 0.95 + min(0.03, (done / total) * 0.03)
                try:
                    download_runtime(rt_pending, progress=rt_prog)
                    self.status = tr("upd_rt_installing")
                    if not apply_runtime(rt_pending):
                        raise RuntimeUpdateError(RUNTIME_FAILED, "cai dat that bai")
                except RuntimeUpdateError as re_:
                    print(f"Runtime update failed: {re_}")
                    state.pending_catalog_notice = tr(re_.key)
                except Exception as e:
                    print(f"Runtime update error: {e}")
                    state.pending_catalog_notice = tr(RUNTIME_FAILED)

            try:
                ensure_latest_j2me_installed()
            except Exception as e:
                print(f"Error ensuring latest J2ME runtime after update: {e}")

        if ok and catalog_pending(m):
            def enter_unpack():
                self.phase_title = "Đang giải nén Cơ sở dữ liệu Kho game..."
                self.status = tr("upd_cat_unpacking")
                self.progress_pct = 0.98

            def cat_prog(done, total, path):
                self.phase_title = "Đang tải Cơ sở dữ liệu Kho game..."
                self.status = f"{tr('upd_cat_downloading')} {done}/{total}"
                if total > 0:
                    self.progress_pct = 0.95 + min(0.04, (done / total) * 0.04)

            try:
                staged_cat = download_catalog(m, progress=cat_prog, on_phase=enter_unpack)
                if not staged_cat or not apply_catalog(m, staged_cat):
                    raise CatalogError(CATALOG_FAILED, "doi ten that bai")
            except CatalogError as ce:
                print(f"Catalog update failed: {ce}")
                state.pending_catalog_notice = tr(ce.key)
            except Exception as e:
                print(f"Catalog update error: {e}")
                state.pending_catalog_notice = tr(CATALOG_FAILED)

        if ok:
            self.progress_pct = 1.0
            self.phase_title = "🎉 Cập nhật thành công!"
            self.status = tr("upd_done")
            state.pending_update = m.get("version", "")
            state.save_settings()
            request_restart()
            self.restart = True
            import time
            time.sleep(1.2)
            if self.engine:
                self.engine.running = False
        else:
            self.failed = True
            self.phase_title = "❌ Cập nhật thất bại"
            self.status = tr("upd_failed")
        self.busy = False

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")
        btn_up = inputs.get("btn_up")
        btn_down = inputs.get("btn_down")

        if self.restart:
            if btn_a or btn_b:
                self.close()
                if self.engine:
                    self.engine.running = False
            return True

        if self.busy:
            return True

        if self.failed:
            if btn_a or btn_b:
                self.close()
            return True

        if btn_b:
            self.close()
            return True

        if btn_up:
            if self.scroll_top > 0:
                self.scroll_top -= 1
            return True
        elif btn_down:
            self.scroll_top += 1
            return True

        labels = self.get_labels()
        if btn_left:
            self.selected_opt = (self.selected_opt - 1) % len(labels)
            return True
        elif btn_right:
            self.selected_opt = (self.selected_opt + 1) % len(labels)
            return True

        if btn_a:
            if self.selected_opt == 0:
                self.busy = True
                self.failed = False
                self.status = tr("upd_downloading")
                threading.Thread(target=self.run_update_thread, daemon=True).start()
            elif self.selected_opt == 1:
                self.close()
            elif self.selected_opt == 2:
                v = (self.manifest or {}).get("version")
                if v:
                    skip_version(v)
                self.close()
            return True

        return True

    def render(self, engine):
        if not self.active:
            return

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 225)
        mw = min(1180, state.SCREEN_W - 60)
        mh = min(650, state.SCREEN_H - 50)
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Main Modal Container
        engine.fill_rect(mx, my, mw, mh, 14, 20, 34, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)

        # Header Bar
        hdr_h = 66
        engine.fill_rect(mx + 3, my + 3, mw - 6, hdr_h, 22, 32, 54, 255)
        engine.fill_rect(mx + 3, my + hdr_h + 1, mw - 6, 2, 0, 246, 246, 255)
        engine.draw_text(tr("upd_title"), engine.font_title, mx + 30, my + hdr_h // 2,
                         0, 246, 246, center_y=True)

        um = self.manifest or {}
        new_v = um.get("version", "?")
        ver_badge = f"v{APP_VERSION}  ➔  v{new_v}"
        engine.draw_text(ver_badge, engine.font_item, mx + mw - 30, my + hdr_h // 2,
                         255, 215, 0, right_align=True, center_y=True)

        # Main Body Split: Left Info Cards (300px), Right Changelog (Rest)
        body_y = my + hdr_h + 16
        body_h = mh - hdr_h - 106
        left_w = 310
        gap = 18

        # --- LEFT PANEL: Summary Cards ---
        lx = mx + 20
        ly = body_y
        card_h = 68
        card_gap = 10

        # Calculate download size
        tot_bytes = sum(f.get("size", 0) for f in self.files) if self.files else 0
        size_str = human_bytes(tot_bytes) if tot_bytes > 0 else ""

        # Left Info Items
        left_items = [
            (tr("upd_new"), f"v{new_v}", (0, 255, 200)),
            (tr("upd_current"), f"v{APP_VERSION}", (180, 200, 225)),
            (tr("upd_files"), f"{len(self.files)} tệp" + (f" ({size_str})" if size_str else ""), (255, 215, 80)),
            ("Kênh phát hành", "Chính thức (CDN)", (140, 220, 255))
        ]
        if self.cat_only:
            cat = catalog_entry(um) or {}
            c_sz = human_bytes(cat.get("size", 0)) if cat else ""
            left_items[0] = (tr("upd_cat_new"), "Database", (0, 255, 200))
            left_items[2] = (tr("game_size"), c_sz, (255, 215, 80))

        for idx, (lbl, val, col) in enumerate(left_items):
            cy = ly + idx * (card_h + card_gap)
            engine.fill_rect(lx, cy, left_w, card_h, 20, 28, 46, 255)
            engine.draw_rect(lx, cy, left_w, card_h, 38, 54, 85, 255, thickness=1)
            engine.draw_text(lbl, engine.font_sub, lx + 16, cy + 18, 140, 165, 195)
            engine.draw_text(val, engine.font_item, lx + 16, cy + 44, *col)

        # Safety Note at bottom of left panel
        tip_y = ly + len(left_items) * (card_h + card_gap) + 4
        tip_h = body_h - (tip_y - body_y)
        if tip_h > 40:
            engine.fill_rect(lx, tip_y, left_w, tip_h, 16, 24, 38, 255)
            engine.draw_rect(lx, tip_y, left_w, tip_h, 0, 180, 220, 120, thickness=1)
            engine.draw_text("🔒 An toàn dữ liệu", engine.font_sub, lx + 16, tip_y + 16, 0, 246, 246)
            tip_msg = "Game và Save trên thẻ nhớ được bảo vệ an toàn 100%."
            tip_lines = engine.wrap_text_to_width(tip_msg, engine.font_sub, left_w - 32, max_lines=2)
            for t_idx, tl in enumerate(tip_lines):
                engine.draw_text(tl, engine.font_sub, lx + 16, tip_y + 38 + t_idx * 20, 150, 175, 200)

        # --- RIGHT PANEL: Changelog & Release Notes ---
        rx = lx + left_w + gap
        rw = mw - left_w - gap - 40
        rh_ = body_h

        engine.fill_rect(rx, body_y, rw, rh_, 10, 16, 28, 255)
        engine.draw_rect(rx, body_y, rw, rh_, 0, 200, 240, 180, thickness=1)
        engine.fill_rect(rx + 2, body_y + 2, rw - 4, 38, 18, 28, 48, 255)
        engine.draw_text("✨ NỘI DUNG NÂNG CẤP & TÍNH NĂNG MỚI", engine.font_sub,
                         rx + 20, body_y + 19, 0, 246, 246, center_y=True)

        # Changelog lines
        rel_note = release_note(um, state.current_lang)
        all_lines = []
        if rel_note:
            raw_sections = rel_note.split("\n")
            for sec in raw_sections:
                sec = sec.strip()
                if not sec:
                    continue
                wrapped = engine.wrap_text_to_width(sec, engine.font_item, rw - 44, max_lines=10)
                for w in wrapped:
                    all_lines.append(w)
        else:
            all_lines.append("• Bản cập nhật tối ưu hóa hiệu năng và sửa các lỗi phát sinh.")

        visible_lines_cnt = max(1, (rh_ - 54) // 30)
        max_scroll = max(0, len(all_lines) - visible_lines_cnt)
        self.scroll_top = max(0, min(self.scroll_top, max_scroll))

        line_y = body_y + 50
        for l_idx in range(self.scroll_top, min(len(all_lines), self.scroll_top + visible_lines_cnt)):
            line_str = all_lines[l_idx]
            is_bullet = line_str.startswith("•") or line_str.startswith("-") or line_str.startswith("*")
            col = (255, 235, 170) if is_bullet else (210, 225, 245)
            engine.draw_text(line_str, engine.font_item, rx + 22, line_y, *col)
            line_y += 30

        # Scrollbar Indicator if content exceeds
        if max_scroll > 0:
            sb_h = max(24, int((visible_lines_cnt / len(all_lines)) * (rh_ - 50)))
            sb_y = body_y + 44 + int((self.scroll_top / max_scroll) * (rh_ - 50 - sb_h))
            engine.fill_rect(rx + rw - 8, body_y + 44, 4, rh_ - 50, 25, 35, 55, 255)
            engine.fill_rect(rx + rw - 8, sb_y, 4, sb_h, 0, 246, 246, 255)

        # --- BOTTOM ACTION / PROGRESS AREA ---
        bot_y = my + mh - 80
        bot_h = 68

        if self.busy or self.failed or self.restart:
            prog_h = 78
            prog_y = my + mh - prog_h - 14
            engine.fill_rect(mx + 20, prog_y, mw - 40, prog_h, 14, 22, 38, 255)
            engine.draw_rect(mx + 20, prog_y, mw - 40, prog_h, 0, 246, 246, 255, thickness=2)

            # Row 1: Phase Title (Left) + Percentage (Right)
            stat_col = (255, 100, 100) if self.failed else ((0, 255, 180) if self.restart else (0, 246, 246))
            engine.draw_text(self.phase_title or self.status, engine.font_item, mx + 38, prog_y + 16, *stat_col)

            pct_val = int(min(1.0, max(0.0, self.progress_pct)) * 100)
            pct_txt = f"{pct_val}%"
            engine.draw_text(pct_txt, engine.font_title, mx + mw - 38, prog_y + 16, 255, 215, 0, right_align=True)

            # Row 2: Heavy Glowing Progress Bar
            pbar_x = mx + 38
            pbar_y = prog_y + 36
            pbar_w = mw - 76
            pbar_h = 16
            engine.fill_rect(pbar_x, pbar_y, pbar_w, pbar_h, 24, 34, 54, 255)
            engine.draw_rect(pbar_x, pbar_y, pbar_w, pbar_h, 45, 65, 95, 255, thickness=1)

            fill_w = max(0, min(pbar_w, int(pbar_w * self.progress_pct)))
            if self.restart:
                engine.fill_rect(pbar_x + 1, pbar_y + 1, pbar_w - 2, pbar_h - 2, 0, 255, 180, 255)
            elif self.failed:
                engine.fill_rect(pbar_x + 1, pbar_y + 1, pbar_w - 2, pbar_h - 2, 255, 80, 80, 255)
            elif fill_w > 0:
                engine.fill_rect(pbar_x + 1, pbar_y + 1, fill_w - 2, pbar_h - 2, 0, 246, 246, 255)
                if fill_w < pbar_w - 4:
                    engine.fill_rect(pbar_x + fill_w - 4, pbar_y + 1, 4, pbar_h - 2, 255, 255, 255, 255)

            # Row 3: Current file & step details
            if self.failed or self.restart:
                engine.draw_text("[A/B] OK", engine.font_sub, mx + mw - 38, prog_y + 58, 220, 235, 255, right_align=True)
            elif self.status:
                engine.draw_text(self.status, engine.font_sub, mx + 38, prog_y + 58, 140, 170, 205)
        else:
            labels = self.get_labels()
            bw = (mw - 40 - (len(labels) - 1) * 14) // len(labels)
            bh = 54
            for i, lbl in enumerate(labels):
                bx = mx + 20 + i * (bw + 14)
                sel = (i == self.selected_opt)
                if sel:
                    engine.fill_rect(bx, bot_y + 4, bw, bh, 0, 140, 150, 255)
                    engine.draw_rect(bx, bot_y + 4, bw, bh, 0, 246, 246, 255, thickness=3)
                    engine.draw_text(lbl, engine.font_badge, bx + bw // 2, bot_y + 4 + bh // 2,
                                     255, 255, 255, center_x=True, center_y=True)
                else:
                    engine.fill_rect(bx, bot_y + 4, bw, bh, 24, 34, 52, 255)
                    engine.draw_rect(bx, bot_y + 4, bw, bh, 45, 60, 90, 255, thickness=1)
                    engine.draw_text(lbl, engine.font_badge, bx + bw // 2, bot_y + 4 + bh // 2,
                                     190, 205, 225, center_x=True, center_y=True)
