#!/bin/sh
LOGFILE="/mnt/SDCARD/RetroHub-java.log"
exec > "$LOGFILE" 2>&1
echo "=== RetroHub Java Game Launch ==="
echo "Date: $(date 2>/dev/null || echo 'N/A')"
echo "Launch cmd: $0 $*"

# Optimize Wi-Fi & CPU performance to prevent network stalls during map transitions
/usr/sbin/iw dev wlan0 set power_save off 2>/dev/null
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null

cd /mnt/SDCARD/Emus/JAVA/zulu17/bin || exit 1
chmod +x ./sdl_interface ./java 2>/dev/null
[ ! -e /usr/lib/libGLES_CM.so ] && [ -f /usr/lib/libGLESv1_CM.so ] && ln -sf /usr/lib/libGLESv1_CM.so /usr/lib/libGLES_CM.so 2>/dev/null

# Safe persistent user save & config directories outside JRE runtime directory
SAFE_RMS="/mnt/SDCARD/Emus/JAVA/rms"
SAFE_CONFIG="/mnt/SDCARD/Emus/JAVA/config"
SAFE_BACKUP="/mnt/SDCARD/Emus/JAVA/saves_backup"
mkdir -p "$SAFE_RMS" "$SAFE_CONFIG" "$SAFE_BACKUP" ./rms ./config

# Recover any orphaned stash folders from previous crashes
for orphan in /mnt/SDCARD/Emus/JAVA/.rh_j2me_*; do
    if [ -d "$orphan/bin/rms" ]; then
        echo "Recovering orphaned save data from $orphan..."
        cp -ru "$orphan/bin/rms/"* "$SAFE_RMS/" 2>/dev/null
        rm -rf "$orphan" 2>/dev/null
    fi
done

# Sync persistent saves and config into runtime working directory before starting
if [ -d "$SAFE_RMS" ]; then
    cp -ru "$SAFE_RMS/"* ./rms/ 2>/dev/null
fi
if [ -d "$SAFE_CONFIG" ]; then
    cp -ru "$SAFE_CONFIG/"* ./config/ 2>/dev/null
fi

JAVA_HOME='/mnt/SDCARD/Emus/JAVA/zulu17'
export JAVA_HOME
PATH="$JAVA_HOME/bin:$PATH"
export PATH

CLASSPATH="$JAVA_HOME/lib:$CLASSPATH"
export CLASSPATH
LD_LIBRARY_PATH="$JAVA_HOME/lib:/usr/trimui/lib:/usr/lib64:/usr/lib:/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH

mkdir -p ./.java/.systemPrefs ./.java/.userPrefs 2>/dev/null
chmod -R 755 ./.java 2>/dev/null

TIMIDITY_CFG="/mnt/SDCARD/Emus/JAVA/timidity/timidity.cfg"
export TIMIDITY_CFG

# Read default phone keypad profile (N=Nokia default, P=Plain, E=SE, S=Siemens, M=Motorola)
DEF_PHONE="n"
if [ -f /mnt/SDCARD/Emus/JAVA/default_phone.cfg ]; then
    DEF_PHONE=$(head -n 1 /mnt/SDCARD/Emus/JAVA/default_phone.cfg | tr -d '\r\n ' | tr '[:upper:]' '[:lower:]')
elif [ -f ./default_phone.cfg ]; then
    DEF_PHONE=$(head -n 1 ./default_phone.cfg | tr -d '\r\n ' | tr '[:upper:]' '[:lower:]')
fi
[ -z "$DEF_PHONE" ] && DEF_PHONE="n"
echo "Default phone key profile: $DEF_PHONE"

JAVA_TOOL_OPTIONS="-Xverify:none -Xms64m -Xmx256m -Dfreej2me.phone=$DEF_PHONE -Djava.util.prefs.systemRoot=./.java -Djava.util.prefs.userRoot=./.java/.userPrefs -Djava.awt.headless=true -Dsun.jnu.encoding=UTF-8 -Dfile.encoding=UTF-8 -Djava.library.path=/mnt/SDCARD/Emus/JAVA/zulu17/lib"
export JAVA_TOOL_OPTIONS
ROM_PATH="$*"
if [ -z "$ROM_PATH" ]; then
    echo "Error: No ROM path specified."
    exit 1
fi

# Detect screen resolution from folder path or filename
W=240
H=320

case "$ROM_PATH" in
    *240320*|*240x320*|*240X320*|*240_320*)
        W=240; H=320 ;;
    *320240*|*320x240*|*320X240*|*320_240*)
        W=320; H=240 ;;
    *176220*|*176x220*|*176X220*|*176_220*)
        W=176; H=220 ;;
    *176208*|*176x208*|*176X208*|*176_208*)
        W=176; H=208 ;;
    *128160*|*128x160*|*128X160*|*128_160*)
        W=128; H=160 ;;
    *128128*|*128x128*|*128X128*|*128_128*)
        W=128; H=128 ;;
    *240400*|*240x400*|*240X400*|*240_400*)
        W=240; H=400 ;;
    *640360*|*640x360*|*640X360*|*640_360*)
        W=640; H=360 ;;
    *360640*|*360x640*|*360X640*|*360_640*)
        W=360; H=640 ;;
    *)
        # Default fallback to 240x320 instead of refusing to start
        W=240; H=320 ;;
esac

echo "Selected resolution: ${W}x${H}"

# FreeJ2ME uses java.net.URI without percent-encoding; spaces or brackets cause URI crashes.
# If path contains unsafe URI characters, create a clean symlink in /tmp to run.
RUN_JAR="$ROM_PATH"
case "$ROM_PATH" in
    *[[:space:]\<\>\"\#\%\{\}\|\\\^\`\[\]]*)
        TMP_JAR="/tmp/j2me_runner.jar"
        rm -f "$TMP_JAR"
        ln -sf "$ROM_PATH" "$TMP_JAR"
        if [ -f "$TMP_JAR" ]; then
            RUN_JAR="$TMP_JAR"
            echo "Created safe symlink: $TMP_JAR -> $ROM_PATH"
        fi
        ;;
esac

echo "Executing FreeJ2ME: ./java -jar freej2me-sdl.jar \"$RUN_JAR\" $W $H 100"
/mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$RUN_JAR" "$W" "$H" 100
GAME_EXIT_CODE=$?

# Post-game safe sync: write user saves and configs back to persistent storage and SD card
echo "Game exited with code $GAME_EXIT_CODE. Performing safe save game persistence..."
if [ -d ./rms ]; then
    cp -ru ./rms/* "$SAFE_RMS/" 2>/dev/null
    cp -ru ./rms/* "$SAFE_BACKUP/" 2>/dev/null
fi
if [ -d ./config ]; then
    cp -ru ./config/* "$SAFE_CONFIG/" 2>/dev/null
fi
# Flush OS filesystem buffers to physical SD card flash immediately
sync 2>/dev/null
echo "Save game backup & sync complete."
exit $GAME_EXIT_CODE
