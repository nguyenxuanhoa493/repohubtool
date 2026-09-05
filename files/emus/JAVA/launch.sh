#!/bin/sh
LOGFILE="/mnt/SDCARD/RetroHub-java.log"
exec > "$LOGFILE" 2>&1
echo "=== RetroHub Java Game Launch ==="
echo "Date: $(date 2>/dev/null || echo 'N/A')"
echo "Launch cmd: $0 $*"

cd /mnt/SDCARD/Emus/JAVA/zulu17/bin || exit 1
chmod +x ./sdl_interface ./java 2>/dev/null
[ ! -e /usr/lib/libGLES_CM.so ] && [ -f /usr/lib/libGLESv1_CM.so ] && ln -sf /usr/lib/libGLESv1_CM.so /usr/lib/libGLES_CM.so 2>/dev/null
mkdir -p ./rms ./config

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

JAVA_TOOL_OPTIONS='-Xverify:none -Djava.util.prefs.systemRoot=./.java -Djava.util.prefs.userRoot=./.java/.userPrefs -Djava.awt.headless=true -Dsun.jnu.encoding=UTF-8 -Dfile.encoding=UTF-8 -Djava.library.path=/mnt/SDCARD/Emus/JAVA/zulu17/lib'
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
exec /mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$RUN_JAR" "$W" "$H" 100
