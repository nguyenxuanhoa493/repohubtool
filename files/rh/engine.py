# -*- coding: utf-8 -*-
"""Core RetroHub Graphics Engine, Event Dispatcher, and Screen Orchestrator."""

import os
import sys
import time
import math
import ctypes
import sdl2
import sdl2.ext
import sdl2.sdlttf as sdlttf
import sdl2.sdlimage as sdlimage

from . import state
from .paths import SDCARD_PATH, SPLASH_TEMP_PREVIEW
from .fonts import VIET_PROBE, font_candidates, pick_font
from .i18n import tr
from .version import APP_VERSION
from .ui.primitives import (fill_rect, draw_rect, draw_line, draw_text,
                           measure_text, wrap_text_to_width,
                           draw_action_vector_icon, draw_toggle, draw_footer_btn)
from .ui.boxart import (SYS_BADGE, resolve_game_img_path,
                       draw_proportional_boxart, draw_default_boxart_avatar)
from .ui.toast import ToastManager
from .inputs import InputManager
from .downloader import dl_state, pop_notification
from .updater import check_for_update
from .modals.update import UpdateModal



def is_screen_blanked():
    """Returns True if physical display is blanked/off by OS (standby/sleep)."""
    try:
        if os.path.exists("/sys/class/graphics/fb0/blank"):
            with open("/sys/class/graphics/fb0/blank", "r") as f:
                val = f.read().strip()
                if val and val != "0":
                    return True
    except Exception:
        pass
    return False

class RetroHubEngine:
    """Main application engine managing SDL2, fonts, textures, screens, and the event loop."""

    def __init__(self):
        self.running = False
        self.window = None
        self.renderer = None
        self.input_mgr = None
        self.controllers = []
        self.joysticks = []
        self.toast_mgr = ToastManager()

        # Fonts
        self.font_title = None
        self.font_sub = None
        self.font_item = None
        self.font_badge = None
        self.font_grid_title = None
        self.font_footer = None
        self.font_btn_badge = None
        self.font_toast = None
        self.font_modal_lbl = None
        self.font_modal_val = None
        self.font_kb = None
        self.font_huge = None

        # Caches
        self.text_texture_cache = {}
        self.img_texture_cache = {}
        self.missing_img_cache = set()
        self.MAX_TEXT_CACHE = 280
        self.MAX_IMG_CACHE = 80

        # Screen management
        self.screens = {}
        self.screen_stack = []
        self.active_modal = None
        self.modal_stack = []
        self.update_modal = UpdateModal(self)

        # Activity tracking
        self.last_user_activity_time = time.time()

    def init_sdl(self):
        """Initialize SDL2 subsystems, window, renderer, and controllers."""
        # Bao ve chong loi crash/reboot do deep suspend tren TrimUI
        try:
            with open("/tmp/stay_alive", "w") as f:
                pass
        except Exception:
            pass

        sdl2.SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)
        sdlttf.TTF_Init()
        sdlimage.IMG_Init(sdlimage.IMG_INIT_PNG | sdlimage.IMG_INIT_JPG)

        display_mode = sdl2.SDL_DisplayMode()
        if sdl2.SDL_GetCurrentDisplayMode(0, display_mode) == 0:
            state.SCREEN_W = display_mode.w
            state.SCREEN_H = display_mode.h
        else:
            state.SCREEN_W = 1024
            state.SCREEN_H = 768

        for i in range(sdl2.SDL_NumJoysticks()):
            if sdl2.SDL_IsGameController(i) == sdl2.SDL_TRUE:
                pad = sdl2.SDL_GameControllerOpen(i)
                if pad:
                    self.controllers.append(pad)
            else:
                joy = sdl2.SDL_JoystickOpen(i)
                if joy:
                    self.joysticks.append(joy)

        self.window = sdl2.SDL_CreateWindow(
            b"RetroHub",
            0, 0,
            state.SCREEN_W,
            state.SCREEN_H,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_FULLSCREEN
        )
        if not self.window:
            self.window = sdl2.SDL_CreateWindow(b"RetroHub", 0, 0, state.SCREEN_W, state.SCREEN_H, sdl2.SDL_WINDOW_SHOWN)
        self.renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        self.input_mgr = InputManager()

    def init_fonts(self):
        """Load and verify Vietnamese UTF-8 compatible fonts."""
        def _font_has_vietnamese(path):
            probe = sdlttf.TTF_OpenFont(path.encode("utf-8"), 16)
            if not probe:
                return None
            try:
                return all(sdlttf.TTF_GlyphIsProvided(probe, cp) for cp in VIET_PROBE)
            finally:
                sdlttf.TTF_CloseFont(probe)

        picked = pick_font(font_candidates(), _font_has_vietnamese)
        if not picked:
            sys.stderr.write("\nRetroHub khong khoi dong duoc: khong mo duoc font .ttf nao.\n\n")
            return False
        font_path = picked.encode("utf-8")

        self.font_title = sdlttf.TTF_OpenFont(font_path, 40)
        self.font_sub = sdlttf.TTF_OpenFont(font_path, 26)
        self.font_item = sdlttf.TTF_OpenFont(font_path, 32)
        self.font_badge = sdlttf.TTF_OpenFont(font_path, 26)
        self.font_grid_title = sdlttf.TTF_OpenFont(font_path, 24)
        self.font_footer = sdlttf.TTF_OpenFont(font_path, 22)
        self.font_btn_badge = sdlttf.TTF_OpenFont(font_path, 24)
        self.font_toast = sdlttf.TTF_OpenFont(font_path, 24)
        self.font_modal_lbl = sdlttf.TTF_OpenFont(font_path, 26)
        self.font_modal_val = sdlttf.TTF_OpenFont(font_path, 24)
        self.font_kb = sdlttf.TTF_OpenFont(font_path, 28)
        self.font_huge = sdlttf.TTF_OpenFont(font_path, 54)
        return True

    # --------------------------------------------------------------------------
    # Texture Management
    # --------------------------------------------------------------------------
    def get_texture_and_size(self, path, force_reload=False):
        """Retrieve texture with LRU cache."""
        if not path:
            return None, 0, 0
        if not force_reload and path in self.missing_img_cache:
            return None, 0, 0
        if force_reload:
            self.missing_img_cache.discard(path)

        now_ts = time.time()
        if force_reload or path == SPLASH_TEMP_PREVIEW:
            if path in self.img_texture_cache:
                tex, _, _, _ = self.img_texture_cache.pop(path)
                sdl2.SDL_DestroyTexture(tex)
        elif path in self.img_texture_cache:
            item = self.img_texture_cache[path]
            item[3] = now_ts
            return item[0], item[1], item[2]

        if not os.path.exists(path):
            self.missing_img_cache.add(path)
            return None, 0, 0

        surf = sdlimage.IMG_Load(path.encode("utf-8"))
        if not surf:
            self.missing_img_cache.add(path)
            return None, 0, 0
        w = surf.contents.w
        h = surf.contents.h
        tex = sdl2.SDL_CreateTextureFromSurface(self.renderer, surf)
        sdl2.SDL_FreeSurface(surf)
        if tex:
            if len(self.img_texture_cache) >= self.MAX_IMG_CACHE:
                old_paths = sorted(self.img_texture_cache.keys(), key=lambda k: self.img_texture_cache[k][3])[:15]
                for op in old_paths:
                    it = self.img_texture_cache.pop(op, None)
                    if it and it[0]:
                        sdl2.SDL_DestroyTexture(it[0])
            self.img_texture_cache[path] = [tex, w, h, now_ts]
            return tex, w, h
        return None, 0, 0

    # --------------------------------------------------------------------------
    # Screen Registration & Navigation
    # --------------------------------------------------------------------------
    def register_screen(self, name, screen_instance):
        screen_instance.engine = self
        self.screens[name] = screen_instance

    def push_screen(self, name, params=None):
        if name in self.screens:
            self.screen_stack.append(name)
            self.screens[name].on_enter(params)

    def pop_screen(self):
        if len(self.screen_stack) > 1:
            curr_name = self.screen_stack.pop()
            if curr_name in self.screens:
                self.screens[curr_name].on_exit()
        elif self.current_screen_name != "home":
            curr_name = self.current_screen_name
            if curr_name in self.screens:
                self.screens[curr_name].on_exit()
            self.screen_stack = ["home"]
            if "home" in self.screens:
                self.screens["home"].on_enter()

    def switch_screen(self, name, params=None):
        if self.screen_stack:
            curr_name = self.screen_stack.pop()
            if curr_name in self.screens:
                self.screens[curr_name].on_exit()
        self.push_screen(name, params)

    @property
    def current_screen_name(self):
        return self.screen_stack[-1] if self.screen_stack else "home"

    @property
    def current_screen(self):
        name = self.current_screen_name
        return self.screens.get(name)

    # --------------------------------------------------------------------------
    # Modals
    # --------------------------------------------------------------------------
    def open_modal(self, modal, data=None):
        modal.engine = self
        modal.open(data)
        self.active_modal = modal

    def close_modal(self):
        if self.active_modal:
            self.active_modal.close()
            self.active_modal = None

    def toast(self, msg, duration=3.0, text_color=(0, 246, 246)):
        self.toast_mgr.show(msg, duration=duration, text_color=text_color)

    # --------------------------------------------------------------------------
    # Drawing Shortcuts
    # --------------------------------------------------------------------------
    def fill_rect(self, x, y, w, h, r, g, b, a=255):
        fill_rect(self.renderer, x, y, w, h, r, g, b, a)

    def draw_rect(self, x, y, w, h, r, g, b, a=255, thickness=1):
        draw_rect(self.renderer, x, y, w, h, r, g, b, a, thickness)

    def draw_line(self, x1, y1, x2, y2, r, g, b, a=255, thickness=1):
        draw_line(self.renderer, x1, y1, x2, y2, r, g, b, a, thickness)

    def draw_text(self, text, font, x, y, r, g, b, a=255, center_x=False, center_y=False, right_align=False):
        return draw_text(self.renderer, text, font, x, y, r, g, b, a, center_x, center_y, self.text_texture_cache, self.MAX_TEXT_CACHE, right_align=right_align)

    def measure_text(self, text, font):
        return measure_text(text, font)

    def wrap_text_to_width(self, text, font, max_w, max_lines=2):
        return wrap_text_to_width(text, font, max_w, max_lines)

    def draw_action_vector_icon(self, act_id, cx, cy, sz=70, r=255, g=255, b=255, a=255):
        draw_action_vector_icon(self.renderer, act_id, cx, cy, sz, r, g, b, a)

    def draw_toggle(self, x, y, is_on):
        draw_toggle(self.renderer, self.font_badge, x, y, is_on, self.text_texture_cache)

    def draw_footer_btn(self, x, foot_y, foot_h, key_char, label_str, btn_color=(0, 230, 150), text_color=(220, 225, 235), is_dark_btn=True):
        return draw_footer_btn(self.renderer, self.font_badge, self.font_footer, x, foot_y, foot_h, key_char, label_str, btn_color, text_color, is_dark_btn, self.text_texture_cache)

    def draw_proportional_boxart(self, path, box_x, box_y, box_w, box_h):
        return draw_proportional_boxart(self.renderer, self.get_texture_and_size, path, box_x, box_y, box_w, box_h)

    def draw_default_boxart_avatar(self, box_x, box_y, box_w, box_h, sys_code="ROM", game_title="Game"):
        return draw_default_boxart_avatar(self.renderer, self.font_badge, box_x, box_y, box_w, box_h, sys_code, game_title, self.text_texture_cache)

    # --------------------------------------------------------------------------
    # Main Loop
    # --------------------------------------------------------------------------
    def run(self):
        """Main execution loop with non-blocking event dispatching and 60 FPS limiter."""
        print("[DEBUG ENGINE] run() started")
        self.running = True
        self.push_screen("home")
        
        last_screen_file = "/tmp/rh_last_screen.txt"
        if os.path.exists(last_screen_file):
            init_screen = None
            try:
                with open(last_screen_file, "r", encoding="utf-8") as f:
                    saved = f.read().strip()
                if saved and saved in self.screens and saved != "home":
                    init_screen = saved
            except Exception:
                pass
            try:
                os.remove(last_screen_file)
            except Exception:
                pass
            if init_screen:
                self.push_screen(init_screen)
        print(f"[DEBUG ENGINE] Screen stack: {self.screen_stack}, current: {self.current_screen_name}")

        # Auto background update check
        if getattr(state, "auto_update", True):
            def _bg_auto_update_check():
                import time as _t
                _t.sleep(2.5)
                try:
                    found = check_for_update(force=False)
                    if found and self.running:
                        manifest, files = found
                        self.open_modal(self.update_modal, {"manifest": manifest, "files": files})
                except Exception as e:
                    print(f"[ENGINE] Auto update check error: {e}")

            import threading as _th
            _th.Thread(target=_bg_auto_update_check, daemon=True).start()

        header_h = 64
        foot_h = 56
        frame_cnt = 0

        while self.running:
            now = time.time()
            frame_cnt += 1
            if frame_cnt <= 5 or frame_cnt % 300 == 0:
                print(f"[DEBUG ENGINE] Loop frame {frame_cnt}, screen={self.current_screen_name}, modal={self.active_modal}")

            # Check if screen is off/blanked (standby) -> sleep low-power to avoid heat and panics
            if is_screen_blanked():
                time.sleep(0.2)
                continue

            # Poll input
            inputs = self.input_mgr.poll(has_controller=bool(self.controllers), current_screen=self.current_screen_name)
            if inputs.get("quit"):
                print("[DEBUG ENGINE] inputs['quit'] is True, stopping running loop")
                self.running = False
                break

            any_input = any(v for k, v in inputs.items() if k not in ("quit", "axis_x", "axis_y"))
            if any_input:
                self.last_user_activity_time = now

            # Poll download notification
            dl_notice = pop_notification()
            if dl_notice:
                self.toast(dl_notice)

            # Route input
            if self.active_modal and self.active_modal.is_active():
                self.active_modal.handle_input(inputs)
            elif self.current_screen:
                self.current_screen.handle_input(inputs)

            # Update
            if self.active_modal and self.active_modal.is_active():
                self.active_modal.update(0.016)
            elif self.current_screen:
                self.current_screen.update(0.016)

            # ------------------------------------------------------------------
            # Render Pass
            # ------------------------------------------------------------------
            self.fill_rect(0, 0, state.SCREEN_W, state.SCREEN_H, 13, 17, 28, 255)

            # 1. Screen Body
            if self.current_screen:
                self.current_screen.render(self)

            # 2. Header Bar
            if self.current_screen_name != "splash_preview":
                self.fill_rect(0, 0, state.SCREEN_W, header_h, 20, 28, 46, 255)
                self.fill_rect(0, header_h - 2, state.SCREEN_W, 2, 0, 246, 246, 255)
                head_title = self.current_screen.get_header_title() if self.current_screen else "RetroHub"
                self.draw_text(head_title, self.font_title, 40, header_h // 2, 255, 255, 255, center_y=True)
                if self.current_screen_name == "home":
                    tw = self.measure_text(head_title, self.font_title)
                    self.draw_text("v" + APP_VERSION, self.font_sub, 40 + tw + 14, header_h // 2 + 4, 120, 145, 180, center_y=True)

            # 3. Footer Bar
            if self.current_screen_name != "splash_preview":
                foot_y = state.SCREEN_H - foot_h
                self.fill_rect(0, foot_y, state.SCREEN_W, foot_h, 10, 14, 24, 255)
                self.fill_rect(0, foot_y, state.SCREEN_W, 2, 35, 45, 75, 255)
                actions = self.current_screen.get_footer_actions() if self.current_screen else []
                fx = 30
                for act in actions:
                    # act: (key_char, label_str, btn_col, text_col, is_dark)
                    btn_char, label_str = act[0], act[1]
                    b_col = act[2] if len(act) > 2 else (0, 230, 150)
                    t_col = act[3] if len(act) > 3 else (220, 225, 235)
                    is_dark = act[4] if len(act) > 4 else True
                    fx = self.draw_footer_btn(fx, foot_y, foot_h, btn_char, label_str, b_col, t_col, is_dark)

            # 4. Modals (Overlays)
            if self.active_modal and self.active_modal.is_active():
                self.active_modal.render(self)

            # 5. Topmost Toast Notifications
            self.toast_mgr.render(self.renderer, self.font_toast, self.text_texture_cache)

            sdl2.SDL_RenderPresent(self.renderer)

            # Adaptive 60 FPS vs 28 FPS idle sleep
            is_active = (now - self.last_user_activity_time < 1.0) or dl_state.get("active", False) or self.toast_mgr.is_active()
            if is_active:
                time.sleep(0.016)
            else:
                time.sleep(0.035)

        self.cleanup()

    def cleanup(self):
        """Free resources and shutdown SDL2."""
        for c in self.controllers:
            sdl2.SDL_GameControllerClose(c)
        for j in self.joysticks:
            sdl2.SDL_JoystickClose(j)

        for item in self.text_texture_cache.values():
            if item and item[0]:
                sdl2.SDL_DestroyTexture(item[0])

        for item in self.img_texture_cache.values():
            if item and item[0]:
                sdl2.SDL_DestroyTexture(item[0])

        for f in (self.font_title, self.font_sub, self.font_item, self.font_badge,
                  self.font_grid_title, self.font_footer, self.font_btn_badge,
                  self.font_toast, self.font_modal_lbl, self.font_modal_val,
                  self.font_kb, self.font_huge):
            if f:
                sdlttf.TTF_CloseFont(f)

        sdlimage.IMG_Quit()
        sdlttf.TTF_Quit()
        if self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()
        try:
            if os.path.exists("/tmp/stay_alive"):
                os.remove("/tmp/stay_alive")
        except Exception:
            pass
