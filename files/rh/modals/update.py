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
        self.rt_only = False
        if self.manifest and not self.cat_only:
            is_new = is_newer(self.manifest.get("version", ""), APP_VERSION)
            if not is_new:
                if catalog_pending(self.manifest) and not self.files and not runtime_pending(self.manifest):
                    self.cat_only = True
                elif runtime_pending(self.manifest) and not self.files:
                    self.rt_only = True
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
        return [tr("upd_install"), tr("upd_later"), tr("upd_skip")]

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
            if not files:
                ok = True
            elif download_update(m, files, progress=prog):
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
                    self.status = f"{tr('upd_failed')}: {tr(re_.key)}"
                    ok = False
                except Exception as e:
                    print(f"Runtime update error: {e}")
                    state.pending_catalog_notice = tr(RUNTIME_FAILED)
                    self.status = f"{tr('upd_failed')}: Runtime"
                    ok = False

            try:
                ensure_latest_j2me_installed()
            except Exception as e:
                print(f"Error ensuring latest J2ME runtime after update: {e}")

        if ok and catalog_pending(m):
            is_cat_only = getattr(self, "cat_only", False) or not files

            def enter_unpack():
                self.phase_title = "Đang giải nén Cơ sở dữ liệu Kho game..."
                self.status = tr("upd_cat_unpacking")
                self.progress_pct = 0.50 if is_cat_only else 0.96

            def cat_prog(done, total, path):
                if total > 0:
                    fraction = min(1.0, done / total)
                    d_str = human_bytes(done)
                    t_str = human_bytes(total)
                    if path.endswith(".gz"):
                        self.phase_title = "Đang tải Cơ sở dữ liệu..."
                        self.progress_file = "roms_store.sqlite3.gz"
                        self.status = f"Tải {d_str} / {t_str}"
                        self.progress_pct = fraction * 0.50 if is_cat_only else 0.92 + fraction * 0.04
                    else:
                        self.phase_title = "Đang giải nén Cơ sở dữ liệu..."
                        self.progress_file = "roms_store.sqlite3"
                        self.status = f"Bung nén {d_str} / {t_str}"
                        self.progress_pct = 0.50 + fraction * 0.48 if is_cat_only else 0.96 + fraction * 0.03

            try:
                staged_cat = download_catalog(m, progress=cat_prog, on_phase=enter_unpack)
                if not staged_cat or not apply_catalog(m, staged_cat):
                    raise CatalogError(CATALOG_FAILED, "doi ten that bai")
            except CatalogError as ce:
                print(f"Catalog update failed: {ce}")
                state.pending_catalog_notice = tr(ce.key)
                self.status = f"{tr('upd_failed')}: {tr(ce.key)}"
                ok = False
            except Exception as e:
                print(f"Catalog update error: {e}")
                state.pending_catalog_notice = tr(CATALOG_FAILED)
                self.status = f"{tr('upd_failed')}: Database"
                ok = False

        if ok:
            self.progress_pct = 1.0
            self.phase_title = "Cập nhật thành công!"
            self.status = tr("upd_done")
            state.pending_update = m.get("version", "")
            state.pending_catalog_notice = ""
            state.save_settings()
            request_restart()
            self.restart = True
            import time
            time.sleep(1.2)
            if self.engine:
                self.engine.running = False
        else:
            self.failed = True
            self.phase_title = "Cập nhật thất bại"
            if not self.status:
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
        mh = min(660, state.SCREEN_H - 40)
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        # Main Modal Container
        engine.fill_rect(mx, my, mw, mh, 14, 20, 34, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=2)

        # Header Bar
        hdr_h = 60
        engine.fill_rect(mx + 2, my + 2, mw - 4, hdr_h, 20, 28, 48, 255)
        engine.fill_rect(mx + 2, my + hdr_h, mw - 4, 2, 0, 246, 246, 255)
        engine.draw_text(tr("upd_title"), engine.font_title, mx + 24, my + hdr_h // 2,
                         0, 246, 246, center_y=True)

        um = self.manifest or {}
        new_v = um.get("version", "?")
        ver_badge = f"v{APP_VERSION}  ->  v{new_v}"
        engine.draw_text(ver_badge, engine.font_item, mx + mw - 24, my + hdr_h // 2,
                         255, 215, 0, right_align=True, center_y=True)

        # Body & Footer dimensions with strict separation
        bot_h = 100
        body_y = my + hdr_h + 16
        body_h = mh - hdr_h - bot_h - 44
        left_w = 260
        gap = 32

        # --- LEFT PANEL: Clean Typography & Generous Line Spacing ---
        lx = mx + 24
        tot_bytes = sum(f.get("size", 0) for f in self.files) if self.files else 0
        size_str = human_bytes(tot_bytes) if tot_bytes > 0 else ""

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
        elif getattr(self, "rt_only", False):
            rt_p = runtime_pending(um)
            rt_sz = human_bytes(sum(f.get("size", 0) for f in rt_p)) if rt_p else ""
            left_items[0] = (tr("upd_new"), "Runtime", (0, 255, 200))
            left_items[2] = (tr("upd_files"), f"{len(rt_p)} tệp" + (f" ({rt_sz})" if rt_sz else ""), (255, 215, 80))

        engine.draw_text("THÔNG TIN PHIÊN BẢN", engine.font_sub, lx, body_y + 4, 0, 246, 246)
        item_y = body_y + 36
        for lbl, val, col in left_items:
            engine.draw_text(lbl, engine.font_sub, lx, item_y, 130, 160, 190)
            engine.draw_text(val, engine.font_item, lx, item_y + 24, *col)
            item_y += 58

        # Safety Note at bottom of left column (fits cleanly inside left_w)
        safe_y = body_y + body_h - 40
        engine.draw_text("Bảo vệ dữ liệu:", engine.font_sub, lx, safe_y, 0, 246, 246)
        engine.draw_text("ROM & Save an toàn 100%", engine.font_sub, lx, safe_y + 20, 0, 200, 220)

        # --- RIGHT PANEL: Changelog & Release Notes ---
        rx = lx + left_w + gap
        rw = mw - left_w - gap - 48
        rh_ = body_h

        engine.fill_rect(rx, body_y, rw, rh_, 10, 16, 28, 255)
        engine.draw_rect(rx, body_y, rw, rh_, 35, 52, 78, 255, thickness=1)
        engine.draw_text("NỘI DUNG NÂNG CẤP & TÍNH NĂNG MỚI", engine.font_sub,
                         rx + 18, body_y + 14, 0, 246, 246)
        engine.fill_rect(rx + 16, body_y + 36, rw - 32, 1, 35, 50, 75, 255)

        # Changelog lines with generous line height (34px)
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
            all_lines.append("- Bản cập nhật tối ưu hóa hiệu năng và sửa các lỗi phát sinh.")

        visible_lines_cnt = max(1, (rh_ - 60) // 34)
        max_scroll = max(0, len(all_lines) - visible_lines_cnt)
        self.scroll_top = max(0, min(self.scroll_top, max_scroll))

        line_y = body_y + 50
        for l_idx in range(self.scroll_top, min(len(all_lines), self.scroll_top + visible_lines_cnt)):
            line_str = all_lines[l_idx]
            is_bullet = line_str.startswith("•") or line_str.startswith("-") or line_str.startswith("*")
            col = (255, 235, 170) if is_bullet else (210, 225, 245)
            engine.draw_text(line_str, engine.font_item, rx + 18, line_y, *col)
            line_y += 34

        # Scrollbar Indicator
        if max_scroll > 0:
            sb_h = max(24, int((visible_lines_cnt / len(all_lines)) * (rh_ - 56)))
            sb_y = body_y + 48 + int((self.scroll_top / max_scroll) * (rh_ - 56 - sb_h))
            engine.fill_rect(rx + rw - 6, body_y + 48, 3, rh_ - 56, 25, 35, 55, 255)
            engine.fill_rect(rx + rw - 6, sb_y, 3, sb_h, 0, 246, 246, 255)

        # --- BOTTOM ACTION / PROGRESS AREA ---
        bot_y = my + mh - bot_h - 14
        # Divider Line clearly separating Body and Footer
        engine.fill_rect(mx + 20, bot_y - 10, mw - 40, 1, 35, 50, 75, 255)

        if self.busy or self.failed or self.restart:
            # Row 1: Phase Title (Left) + Percentage (Right) with font_item
            stat_col = (255, 100, 100) if self.failed else ((0, 255, 180) if self.restart else (0, 246, 246))
            engine.draw_text(self.phase_title or self.status, engine.font_item, mx + 24, bot_y + 8, *stat_col)

            pct_val = int(min(1.0, max(0.0, self.progress_pct)) * 100)
            pct_txt = f"{pct_val}%"
            engine.draw_text(pct_txt, engine.font_item, mx + mw - 24, bot_y + 8, 255, 215, 0, right_align=True)

            # Row 2: Clean Glowing Progress Bar (placed 34px below Row 1)
            pbar_x = mx + 24
            pbar_y = bot_y + 42
            pbar_w = mw - 48
            pbar_h = 14
            engine.fill_rect(pbar_x, pbar_y, pbar_w, pbar_h, 20, 28, 46, 255)
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

            # Row 3: Current file & step details (placed comfortably below the bar)
            if self.failed or self.restart:
                engine.draw_text("[A/B] OK", engine.font_sub, mx + mw - 24, bot_y + 68, 220, 235, 255, right_align=True)
            elif self.status:
                engine.draw_text(self.status, engine.font_sub, mx + 24, bot_y + 68, 140, 170, 205)
        else:
            labels = self.get_labels()
            bw = (mw - 48 - (len(labels) - 1) * 14) // len(labels)
            bh = 52
            for i, lbl in enumerate(labels):
                bx = mx + 24 + i * (bw + 14)
                sel = (i == self.selected_opt)
                if sel:
                    engine.fill_rect(bx, bot_y + 16, bw, bh, 0, 140, 150, 255)
                    engine.draw_rect(bx, bot_y + 16, bw, bh, 0, 246, 246, 255, thickness=2)
                    engine.draw_text(lbl, engine.font_badge, bx + bw // 2, bot_y + 16 + bh // 2,
                                     255, 255, 255, center_x=True, center_y=True)
                else:
                    engine.fill_rect(bx, bot_y + 16, bw, bh, 20, 28, 46, 255)
                    engine.draw_rect(bx, bot_y + 16, bw, bh, 40, 55, 80, 255, thickness=1)
                    engine.draw_text(lbl, engine.font_badge, bx + bw // 2, bot_y + 16 + bh // 2,
                                     190, 205, 225, center_x=True, center_y=True)
