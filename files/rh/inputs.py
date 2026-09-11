# -*- coding: utf-8 -*-
"""Input abstraction and device mapping for RetroHub.

Translates SDL2 events (GameController, raw Joystick, and Keyboard)
into unified virtual actions (btn_a, btn_b, btn_up, etc.) with
smooth hold-to-scroll autorepeat.
"""

import json
import os
import sys

try:
    import sdl2
except ImportError:
    _app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _vendor = os.path.join(_app_dir, "vendor")
    if os.path.isdir(_vendor) and _vendor not in sys.path:
        sys.path.insert(0, _vendor)
    import sdl2

from .paths import SDCARD_PATH

# Default Raw Joystick mappings when SDL GameController is unavailable:
DEFAULT_JOY_PROFILES = {
    "trimui": {
        "a": [1],
        "b": [0],
        "x": [3],
        "y": [2],
        "l1": [4, 6],
        "r1": [5, 7],
        "up": [8, 11, 13],
        "down": [9, 12, 14],
        "start": [9],
        "f1": [10],
    },
    "anbernic": {
        "a": [0],
        "b": [1],
        "x": [2],
        "y": [3],
        "l1": [4],
        "r1": [5],
        "up": [13],
        "down": [14],
        "left": [11],
        "right": [12],
        "start": [7],
        "f1": [6],
    },
    "miyoo": {
        "a": [0],
        "b": [1],
        "x": [2],
        "y": [3],
        "l1": [4],
        "r1": [5],
        "start": [7],
        "f1": [6, 8],
    },
}


def detect_device_profile():
    """Detect handheld profile for raw joystick button fallback."""
    env_prof = os.environ.get("RETROHUB_INPUT_PROFILE")
    if env_prof and env_prof in DEFAULT_JOY_PROFILES:
        return env_prof

    if os.path.exists("/usr/trimui") or os.path.isdir(os.path.join(SDCARD_PATH, "trimui")):
        return "trimui"
    if os.path.exists("/opt/muos") or os.path.isdir(os.path.join(SDCARD_PATH, "Anbernic")):
        return "anbernic"
    if os.path.isdir(os.path.join(SDCARD_PATH, ".tmp_update")) or os.path.isdir(os.path.join(SDCARD_PATH, "miyoo")):
        return "miyoo"
    return "trimui"


class InputManager:
    """Encapsulates input event parsing and hold-to-scroll autorepeat."""

    def __init__(self, profile_name=None):
        self.profile_name = profile_name or detect_device_profile()
        self.profile = dict(DEFAULT_JOY_PROFILES.get(self.profile_name, DEFAULT_JOY_PROFILES["trimui"]))

        # Optional user override file: $SDCARD_PATH/.retrohub/keymap.json
        custom_keymap = os.path.join(SDCARD_PATH, ".retrohub", "keymap.json")
        if os.path.exists(custom_keymap):
            try:
                with open(custom_keymap, "r", encoding="utf-8") as f:
                    overrides = json.load(f)
                    if isinstance(overrides, dict):
                        self.profile.update(overrides)
            except Exception:
                pass

        self.key_held_state = {
            "up": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
            "down": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
            "left": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
            "right": {"pressed": False, "start_time": 0.0, "last_repeat": 0.0},
        }

        self.hold_delay = 0.26
        self.repeat_interval = 0.075

        self.reset()

    def reset(self):
        """Reset single-frame button trigger flags."""
        self.btn_up = False
        self.btn_down = False
        self.btn_left = False
        self.btn_right = False
        self.btn_l1 = False
        self.btn_r1 = False
        self.btn_a = False
        self.btn_b = False
        self.btn_x = False
        self.btn_y = False
        self.btn_start = False
        self.btn_f1 = False
        self.backspace = False

    def _press_dir(self, direction, now):
        opposite = {"up": "down", "down": "up", "left": "right", "right": "left"}.get(direction)
        if not self.key_held_state[direction]["pressed"]:
            setattr(self, f"btn_{direction}", True)
            self.key_held_state[direction] = {"pressed": True, "start_time": now, "last_repeat": now}
            if opposite:
                self.key_held_state[opposite]["pressed"] = False

    def _release_dir(self, direction):
        self.key_held_state[direction]["pressed"] = False

    def process_event(self, event, has_controller, now, current_screen=None):
        """Parse one SDL_Event and update button states."""
        etype = event.type

        # 1. GameController Buttons
        if etype == sdl2.SDL_CONTROLLERBUTTONDOWN:
            cbtn = event.cbutton.button
            if cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                self._press_dir("up", now)
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                self._press_dir("down", now)
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                self._press_dir("left", now)
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                self._press_dir("right", now)
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER:
                self.btn_l1 = True
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER:
                self.btn_r1 = True
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_B:  # Physical A (East)
                self.btn_a = True
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_A:  # Physical B (South)
                self.btn_b = True
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_Y:  # Physical X (North)
                self.btn_x = True
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_X:  # Physical Y (West)
                self.btn_y = True
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_START:
                self.btn_start = True
            elif cbtn in [sdl2.SDL_CONTROLLER_BUTTON_BACK, sdl2.SDL_CONTROLLER_BUTTON_GUIDE]:
                self.btn_f1 = True

        elif etype == sdl2.SDL_CONTROLLERBUTTONUP:
            cbtn = event.cbutton.button
            if cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP:
                self._release_dir("up")
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN:
                self._release_dir("down")
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT:
                self._release_dir("left")
            elif cbtn == sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT:
                self._release_dir("right")

        # 2. GameController Analog Sticks
        elif etype == sdl2.SDL_CONTROLLERAXISMOTION:
            val = event.caxis.value
            axis = event.caxis.axis
            if axis == sdl2.SDL_CONTROLLER_AXIS_LEFTY:
                if val < -15000:
                    self._press_dir("up", now)
                elif val > 15000:
                    self._press_dir("down", now)
                elif abs(val) <= 10000:
                    self._release_dir("up")
                    self._release_dir("down")
            elif axis == sdl2.SDL_CONTROLLER_AXIS_LEFTX:
                if val < -15000:
                    self._press_dir("left", now)
                elif val > 15000:
                    self._press_dir("right", now)
                elif abs(val) <= 10000:
                    self._release_dir("left")
                    self._release_dir("right")

        # 3. Raw Joystick Buttons (when GameController is not initialized)
        elif not has_controller and etype == sdl2.SDL_JOYBUTTONDOWN:
            jbtn = event.jbutton.button
            prof = self.profile
            if jbtn in prof.get("a", []):
                self.btn_a = True
            elif jbtn in prof.get("b", []):
                self.btn_b = True
            elif jbtn in prof.get("x", []):
                self.btn_x = True
            elif jbtn in prof.get("y", []):
                self.btn_y = True
            elif jbtn in prof.get("l1", []):
                self.btn_l1 = True
            elif jbtn in prof.get("r1", []):
                self.btn_r1 = True
            elif jbtn in prof.get("up", []):
                self._press_dir("up", now)
            elif jbtn in prof.get("down", []):
                self._press_dir("down", now)
            elif jbtn in prof.get("left", []):
                self._press_dir("left", now)
            elif jbtn in prof.get("right", []):
                self._press_dir("right", now)
            elif jbtn in prof.get("start", []):
                self.btn_start = True
            elif jbtn in prof.get("f1", []):
                self.btn_f1 = True

        elif not has_controller and etype == sdl2.SDL_JOYBUTTONUP:
            jbtn = event.jbutton.button
            prof = self.profile
            if jbtn in prof.get("up", []):
                self._release_dir("up")
            elif jbtn in prof.get("down", []):
                self._release_dir("down")
            elif jbtn in prof.get("left", []):
                self._release_dir("left")
            elif jbtn in prof.get("right", []):
                self._release_dir("right")

        # 4. Raw Joystick Axes
        elif etype == sdl2.SDL_JOYAXISMOTION:
            axis = event.jaxis.axis
            val = event.jaxis.value
            if axis == 1:  # Left Y
                if val < -15000:
                    self._press_dir("up", now)
                elif val > 15000:
                    self._press_dir("down", now)
                elif abs(val) <= 10000:
                    self._release_dir("up")
                    self._release_dir("down")
            elif axis == 0:  # Left X
                if val < -15000:
                    self._press_dir("left", now)
                elif val > 15000:
                    self._press_dir("right", now)
                elif abs(val) <= 10000:
                    self._release_dir("left")
                    self._release_dir("right")

        # 5. Raw Joystick Hats (D-pad on many standard controllers)
        elif etype == sdl2.SDL_JOYHATMOTION:
            hat_val = event.jhat.value
            if hat_val & sdl2.SDL_HAT_UP:
                self._press_dir("up", now)
            else:
                self._release_dir("up")

            if hat_val & sdl2.SDL_HAT_DOWN:
                self._press_dir("down", now)
            else:
                self._release_dir("down")

            if hat_val & sdl2.SDL_HAT_LEFT:
                self._press_dir("left", now)
            else:
                self._release_dir("left")

            if hat_val & sdl2.SDL_HAT_RIGHT:
                self._press_dir("right", now)
            else:
                self._release_dir("right")

        # 6. Keyboard (PC, Mac, and debugging)
        elif etype == sdl2.SDL_KEYDOWN:
            sym = event.key.keysym.sym
            if sym in [sdl2.SDLK_UP, sdl2.SDLK_w]:
                self._press_dir("up", now)
            elif sym in [sdl2.SDLK_DOWN, sdl2.SDLK_s]:
                self._press_dir("down", now)
            elif sym in [sdl2.SDLK_LEFT, sdl2.SDLK_a]:
                self._press_dir("left", now)
            elif sym in [sdl2.SDLK_RIGHT, sdl2.SDLK_d]:
                self._press_dir("right", now)
            elif sym in [sdl2.SDLK_PAGEUP, sdl2.SDLK_q]:
                self.btn_l1 = True
            elif sym in [sdl2.SDLK_PAGEDOWN, sdl2.SDLK_e]:
                self.btn_r1 = True
            elif sym in [sdl2.SDLK_RETURN, sdl2.SDLK_SPACE, sdl2.SDLK_z, sdl2.SDLK_j]:
                self.btn_a = True
            elif sym in [sdl2.SDLK_ESCAPE, sdl2.SDLK_k]:
                self.btn_b = True
            elif sym == sdl2.SDLK_BACKSPACE:
                if current_screen in ("search_input", "yt_search_input"):
                    self.backspace = True
                else:
                    self.btn_b = True
            elif sym == sdl2.SDLK_x:
                self.btn_x = True
            elif sym == sdl2.SDLK_y:
                self.btn_y = True
            elif sym in [sdl2.SDLK_F1, sdl2.SDLK_m]:
                self.btn_f1 = True

            if current_screen in ("search_input", "yt_search_input") and sym == sdl2.SDLK_RETURN:
                self.btn_start = True

        elif etype == sdl2.SDL_KEYUP:
            sym = event.key.keysym.sym
            if sym in [sdl2.SDLK_UP, sdl2.SDLK_w]:
                self._release_dir("up")
            elif sym in [sdl2.SDLK_DOWN, sdl2.SDLK_s]:
                self._release_dir("down")
            elif sym in [sdl2.SDLK_LEFT, sdl2.SDLK_a]:
                self._release_dir("left")
            elif sym in [sdl2.SDLK_RIGHT, sdl2.SDLK_d]:
                self._release_dir("right")

    def update_repeats(self, now):
        """Update hold-to-scroll autorepeat for directional navigation."""
        for k_dir, k_st in self.key_held_state.items():
            if k_st["pressed"]:
                if now - k_st["start_time"] > self.hold_delay:
                    if now - k_st["last_repeat"] > self.repeat_interval:
                        setattr(self, f"btn_{k_dir}", True)
                        k_st["last_repeat"] = now
