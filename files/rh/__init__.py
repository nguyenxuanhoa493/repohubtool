"""RetroHub internals, split out of the original single-file app."""

import os
import sys

_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sdcard = os.environ.get("SDCARD_PATH", "/mnt/SDCARD")

_exlibs = os.path.join(_sdcard, "Apps", "PortMaster", "PortMaster", "exlibs")
if os.path.exists(_exlibs) and _exlibs not in sys.path:
    sys.path.insert(0, _exlibs)

_vendor = os.path.join(_app_dir, "vendor")
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)

_libs = os.path.join(_app_dir, "libs")
_default_dlls = f"{_libs}:/usr/trimui/lib:/usr/lib64:/usr/lib"
if not os.environ.get("PYSDL2_DLL_PATH"):
    os.environ["PYSDL2_DLL_PATH"] = _default_dlls
