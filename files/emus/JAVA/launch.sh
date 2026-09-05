#!/bin/sh
echo $0 $*
progdir=`dirname "$0"`


cd /mnt/SDCARD/Emus/JAVA/zulu17/bin
chmod +x ./sdl_interface ./java 2>/dev/null
[ ! -e /usr/lib/libGLES_CM.so ] && [ -f /usr/lib/libGLESv1_CM.so ] && ln -sf /usr/lib/libGLESv1_CM.so /usr/lib/libGLES_CM.so 2>/dev/null
mkdir -p ./rms ./config

JAVA_HOME='/mnt/SDCARD/Emus/JAVA/zulu17'
export JAVA_HOME
PATH="$JAVA_HOME/bin:$PATH"
export PATH

CLASSPATH="$JAVA_HOME/lib:$CLASSPATH"
export CLASSPATH
LD_LIBRARY_PATH="$JAVA_HOME/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH

mkdir -p ./.java/.systemPrefs
mkdir ./.java/.userPrefs
chmod -R 755 ./.java

TIMIDITY_CFG="/mnt/SDCARD/Emus/JAVA/timidity/timidity.cfg"
export TIMIDITY_CFG


JAVA_TOOL_OPTIONS='-Xverify:none -Djava.util.prefs.systemRoot=./.java -Djava.util.prefs.userRoot=./.java/.userPrefs -Djava.awt.headless=true -Dsun.jnu.encoding=UTF-8 -Dfile.encoding=UTF-8 -Djava.library.path=/mnt/SDCARD/Emus/JAVA/zulu17/lib'
export JAVA_TOOL_OPTIONS

gamedir=`dirname "$*"`


if echo $gamedir | grep "240320" > /dev/null
then

	/mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$*" 240 320 100

elif echo $gamedir | grep "320240" > /dev/null
then
	
	/mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$*" 320 240 100

elif echo $gamedir | grep "128128" > /dev/null
then

	/mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$*" 128 128 100
	
elif echo $gamedir | grep "176208" > /dev/null
then

	/mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$*" 176 208 100

elif echo $gamedir | grep "640360" > /dev/null
then

	/mnt/SDCARD/Emus/JAVA/zulu17/bin/java -jar /mnt/SDCARD/Emus/JAVA/zulu17/bin/freej2me-sdl.jar "$*" 640 360 100

else
	echo "none"
fi
