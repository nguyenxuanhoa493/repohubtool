#!/bin/sh

cd "$(dirname "$0")"

export SDCARD_PATH="/mnt/SDCARD"
export PATH="$SDCARD_PATH/System/bin:$PATH"
export LD_LIBRARY_PATH="$SDCARD_PATH/System/lib:/usr/trimui/lib:/usr/lib:$LD_LIBRARY_PATH"
export PYSDL2_DLL_PATH="/usr/trimui/lib"

while true; do
    rm -f /tmp/launch_game.sh
    python3 app.pyc
    
    if [ -f /tmp/launch_game.sh ]; then
        sh /tmp/launch_game.sh
        rm -f /tmp/launch_game.sh
    else
        break
    fi
done
