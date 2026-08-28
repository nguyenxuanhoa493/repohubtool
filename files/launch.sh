#!/bin/sh

cd "$(dirname "$0")"

export SDCARD_PATH="/mnt/SDCARD"
export PATH="$SDCARD_PATH/System/bin:$PATH"
export LD_LIBRARY_PATH="$SDCARD_PATH/System/lib:/usr/trimui/lib:/usr/lib:$LD_LIBRARY_PATH"
export PYSDL2_DLL_PATH="/usr/trimui/lib"

# The Brick ships python3 in its firmware. The Brick Pro (TG4040) ships none at
# all - not in the rootfs, not on the card, not in busybox - so the app carries
# its own interpreter under python/. Prefer whatever the device already has,
# fall back to the bundled runtime.
PY="$(command -v python3 2>/dev/null)"
if [ -z "$PY" ] && [ -x ./python/bin/python3 ]; then
    PY=./python/bin/python3
fi
if [ -z "$PY" ]; then
    echo "Khong tim thay Python tren may va ban cai khong co thu muc python/." >&2
    echo "Hay tai ban cai co kem Python cho Brick Pro." >&2
    exit 1
fi

while true; do
    rm -f /tmp/launch_game.sh
    "$PY" app.py

    if [ -f /tmp/launch_game.sh ]; then
        sh /tmp/launch_game.sh
        rm -f /tmp/launch_game.sh
    else
        break
    fi
done
