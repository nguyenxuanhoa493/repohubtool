#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RetroHub - Premium Retro Gaming Platform & Multi-Source ROM Store for TrimUI Handhelds."""

import os
import sys
import threading

# ------------------------------------------------------------------------------
# Library Paths (PortMaster exlibs, Vendor, and Custom DLLs)
# ------------------------------------------------------------------------------
EXLIBS_PATH = os.path.join(os.environ.get("SDCARD_PATH", "/mnt/SDCARD"), "Apps", "PortMaster", "PortMaster", "exlibs")
if os.path.exists(EXLIBS_PATH):
    sys.path.insert(0, EXLIBS_PATH)

VENDOR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(VENDOR_PATH):
    sys.path.insert(0, VENDOR_PATH)

_VENDOR_LIBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
_DEFAULT_DLL_PATHS = f"{_VENDOR_LIBS}:/usr/trimui/lib:/usr/lib64:/usr/lib"
os.environ["PYSDL2_DLL_PATH"] = os.environ.get("PYSDL2_DLL_PATH") or _DEFAULT_DLL_PATHS

# ------------------------------------------------------------------------------
# Core Engine & Subsystem Imports
# ------------------------------------------------------------------------------
from rh.logger import init_logger
from rh.netplay import is_netplay_tunnel_running, stop_netplay_tunnel
from rh.env import auto_check_and_supplement_environment
from rh.engine import RetroHubEngine

# Screen Controllers
from rh.screens.home import HomeScreen
from rh.screens.library import LibraryScreen
from rh.screens.store import StoreScreen
from rh.screens.youtube import YoutubeScreen
from rh.screens.watch import WatchScreen
from rh.screens.queue import QueueScreen
from rh.screens.keyboard import VirtualKeyboardScreen
from rh.screens.network import NetworkScreen
from rh.screens.settings import SettingsScreen
from rh.screens.utilities import UtilitiesScreen
from rh.screens.led import LedScreen
from rh.screens.splash import SplashScreen
from rh.screens.retro_store import RetroStoreScreen
from rh.screens.theme_store import ThemeStoreScreen
from rh.screens.icon_store import IconStoreScreen
from rh.screens.emu_store import EmuStoreScreen


def main():
    """Initialize subsystems, register screens, and start the engine loop."""
    init_logger()

    # Clean up any leftover Netplay tunnel from previous session
    try:
        if is_netplay_tunnel_running() or os.path.exists("/tmp/netplay_info.json"):
            stop_netplay_tunnel()
    except Exception:
        pass

    # Background silent environment repair (Java runtime, SegaCD, WiFi awake)
    threading.Thread(target=auto_check_and_supplement_environment, daemon=True).start()

    # Initialize Graphics & Event Engine
    engine = RetroHubEngine()
    engine.init_sdl()
    if not engine.init_fonts():
        sys.exit(1)

    # Register Screens
    engine.register_screen("home", HomeScreen(engine))
    engine.register_screen("library", LibraryScreen(engine))
    engine.register_screen("store", StoreScreen(engine))
    engine.register_screen("youtube", YoutubeScreen(engine))
    engine.register_screen("watch", WatchScreen(engine))
    engine.register_screen("queue", QueueScreen(engine))
    engine.register_screen("keyboard", VirtualKeyboardScreen(engine))
    engine.register_screen("network", NetworkScreen(engine))
    engine.register_screen("settings", SettingsScreen(engine))
    engine.register_screen("utilities", UtilitiesScreen(engine))
    engine.register_screen("led", LedScreen(engine))
    engine.register_screen("splash", SplashScreen(engine))
    engine.register_screen("retro_store", RetroStoreScreen(engine))
    engine.register_screen("theme_store", ThemeStoreScreen(engine))
    engine.register_screen("icon_store", IconStoreScreen(engine))
    engine.register_screen("emu_store", EmuStoreScreen(engine))

    # Run Main Loop
    engine.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import time
        import traceback
        err_msg = traceback.format_exc()
        sys.stderr.write(f"\n[RetroHub Crash]\n{err_msg}\n")
        try:
            _err_f = os.path.join(os.environ.get("SDCARD_PATH", "/mnt/SDCARD"), "RetroHub-loi.txt")
            with open(_err_f, "a", encoding="utf-8") as _ef:
                _ef.write(f"\n[RetroHub Crash at {time.strftime('%Y-%m-%d %H:%M:%S')}]\n{err_msg}\n")
        except Exception:
            pass
        raise
