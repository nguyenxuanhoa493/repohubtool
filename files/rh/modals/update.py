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
        super().open(data)

    def get_labels(self):
        return [tr("upd_install_now"), tr("upd_remind_later"), tr("upd_skip_version")]

    def run_update_thread(self):
        m = self.manifest
        files = self.files

        def prog(done, total, path):
            name = os.path.basename(path) if path else ""
            self.status = f"{done}/{total}  {name}".strip()

        ok = False
        try:
            if download_update(m, files, progress=prog):
                self.status = tr("upd_installing")
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
                    self.status = f"{tr('upd_rt_downloading')} {done}/{total}"
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
                self.status = tr("upd_cat_unpacking")

            def cat_prog(done, total, path):
                self.status = f"{tr('upd_cat_downloading')} {done}/{total}"

            try:
                download_catalog(m, progress=cat_prog, on_phase=enter_unpack)
                if not apply_catalog(m):
                    raise CatalogError(CATALOG_FAILED, "doi ten that bai")
            except CatalogError as ce:
                print(f"Catalog update failed: {ce}")
                state.pending_catalog_notice = tr(ce.key)
            except Exception as e:
                print(f"Catalog update error: {e}")
                state.pending_catalog_notice = tr(CATALOG_FAILED)

        if ok:
            self.status = tr("upd_done")
            state.pending_update = m.get("version", "")
            state.save_settings()
            request_restart()
            self.restart = True
        else:
            self.failed = True
            self.status = tr("upd_failed")
        self.busy = False

    def handle_input(self, inputs):
        if not self.active:
            return False

        btn_a = inputs.get("btn_a")
        btn_b = inputs.get("btn_b")
        btn_left = inputs.get("btn_left")
        btn_right = inputs.get("btn_right")

        if self.restart:
            if btn_a or btn_b:
                self.close()
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

        engine.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 0, 0, 0, 215)
        mw = min(760, state.SCREEN_W - 60)
        mh = 380
        mx = (state.SCREEN_W - mw) // 2
        my = (state.SCREEN_H - mh) // 2

        engine.fill_rect(mx, my, mw, mh, 16, 22, 38, 255)
        engine.draw_rect(mx, my, mw, mh, 0, 246, 246, 255, thickness=3)
        engine.fill_rect(mx + 3, my + 3, mw - 6, 70, 24, 34, 58, 255)
        engine.fill_rect(mx + 3, my + 71, mw - 6, 2, 0, 246, 246, 255)
        engine.draw_text(tr("upd_title"), engine.font_title, mx + mw // 2, my + 36,
                         0, 246, 246, center_x=True, center_y=True)

        um = self.manifest or {}
        rows_y = my + 100
        engine.draw_text(f"{tr('upd_current')} {APP_VERSION}", engine.font_item, mx + 45, rows_y, 200, 215, 235)
        if self.cat_only:
            cat = catalog_entry(um) or {}
            size_txt = human_bytes(cat["size"]) if cat else ""
            engine.draw_text(tr("upd_cat_new"), engine.font_item, mx + 45, rows_y + 40, 0, 246, 200)
            engine.draw_text(f"{tr('game_size')}{size_txt}", engine.font_sub, mx + 45, rows_y + 82, 150, 170, 200)
        else:
            engine.draw_text(f"{tr('upd_new')} {um.get('version', '?')}", engine.font_item, mx + 45, rows_y + 40, 0, 246, 200)
            engine.draw_text(f"{tr('upd_files')} {len(self.files)}", engine.font_sub, mx + 45, rows_y + 82, 150, 170, 200)

        note_y = rows_y + 116
        rel_note = release_note(um, state.current_lang)
        if rel_note:
            note_txt = f"• {rel_note}"
            limit = mw - 90
            lines = engine.wrap_text_to_width(note_txt, engine.font_sub, limit, max_lines=2)
            for nl in lines:
                engine.draw_text(nl, engine.font_sub, mx + 45, note_y, 0, 230, 180)
                note_y += 26
        engine.draw_text(tr("upd_note"), engine.font_sub, mx + 45, note_y, 150, 170, 200)

        if self.busy or self.failed or self.restart:
            colour = (255, 120, 120) if self.failed else (0, 230, 255)
            engine.draw_text(self.status, engine.font_item, mx + mw // 2, my + mh - 62,
                             *colour, center_x=True, center_y=True)
            if self.failed or self.restart:
                engine.draw_text("[A/B] OK", engine.font_sub, mx + mw // 2, my + mh - 26,
                                 200, 215, 235, center_x=True, center_y=True)
        else:
            labels = self.get_labels()
            bw = (mw - 100) // len(labels)
            bh = 52
            by = my + mh - 78
            for i, lbl in enumerate(labels):
                bx = mx + 40 + i * (bw + 10)
                sel = (i == self.selected_opt)
                if sel:
                    engine.fill_rect(bx, by, bw, bh, 0, 120, 130, 255)
                    engine.draw_rect(bx, by, bw, bh, 0, 246, 246, 255, thickness=3)
                else:
                    engine.fill_rect(bx, by, bw, bh, 30, 42, 66, 255)
                    engine.draw_rect(bx, by, bw, bh, 70, 90, 125, 255, thickness=1)
                engine.draw_text(lbl, engine.font_badge, bx + bw // 2, by + bh // 2,
                                 255, 255, 255, center_x=True, center_y=True)
