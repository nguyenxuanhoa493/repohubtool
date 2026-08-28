#!/bin/sh
#
# Find a usable Python, then run the app.
#
# The Brick ships python3 in its firmware. The Brick Pro (TG4040) ships none at
# all - not in the rootfs, not on the card, no busybox applet - so a fixed
# `python3 app.py` died there with "python3: not found" and the menu just
# bounced back, showing nothing. Every layer below exists because one of them
# can be missing on some device:
#
#   1. the device's own python3
#   2. the interpreter bundled with this install, under python/
#   3. one left by an earlier run of this script, or by PortMaster
#   4. failing all that, download it
#
# Nothing here may assume Python exists: this script is the one part of RetroHub
# that runs before it.

# Parameter expansion, not dirname: this script runs before anything else is
# known to exist, and one less external command is one less way to fail.
case "$0" in
    */*) cd "${0%/*}" || exit 1 ;;
esac
APP="$(pwd)"

export SDCARD_PATH="/mnt/SDCARD"
export PATH="$SDCARD_PATH/System/bin:$PATH"
export LD_LIBRARY_PATH="$SDCARD_PATH/System/lib:/usr/trimui/lib:/usr/lib:$LD_LIBRARY_PATH"
export PYSDL2_DLL_PATH="/usr/trimui/lib"

# Kept outside the app folder so reinstalling or updating RetroHub does not
# throw away a runtime that took a download to get.
CACHE_DIR="$SDCARD_PATH/.retrohub"
CACHE_PY="$CACHE_DIR/python/bin/python3"
RUNTIME_URL="https://github.com/nguyenxuanhoa493/repohubtool/releases/download/runtime-python-3.11.16-aarch64/python-3.11.16-aarch64.tar.gz"
RUNTIME_SHA="da6c91a90a4dc81677286b1fba74ebb14af1b36287447fc97b8f37a2e1f2173a"
RUNTIME_MB=20

# There is no console on a handheld: stdout vanishes and the menu redraws over
# everything. A file at the root of the card is the only message the user can
# actually find, so anything fatal goes there.
ERRLOG="$SDCARD_PATH/RetroHub-loi.txt"

log() { echo "[RetroHub] $*"; }

fatal() {
    log "$1"
    {
        echo "RetroHub khong khoi dong duoc / RetroHub could not start"
        echo "$(date 2>/dev/null)"
        echo
        echo "$1"
        echo
        echo "$2"
    } > "$ERRLOG" 2>/dev/null
    exit 1
}

# A candidate only counts if it starts. -x says nothing useful here: a partial
# copy missing its stdlib, a truncated download and a build for the wrong
# architecture all pass the executable test and then fail at run time. The
# version gate keeps an ancient firmware python from getting halfway in.
usable() {
    [ -n "$1" ] && [ -f "$1" ] || return 1
    [ -x "$1" ] || chmod +x "$1" 2>/dev/null
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null
}

find_python() {
    for c in \
        "$(command -v python3 2>/dev/null)" \
        "$APP/python/bin/python3" \
        "$CACHE_PY" \
        "$SDCARD_PATH/System/bin/python3" \
        "$SDCARD_PATH/Apps/PortMaster/PortMaster/exlibs/python3" \
        /usr/bin/python3 \
        /usr/local/bin/python3
    do
        if usable "$c"; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

# Only reached when the install shipped without python/ and the device has none.
# Wants Wi-Fi, so it is the last resort rather than the plan.
download_python() {
    log "Khong tim thay Python. Dang tai ban chay ve (~${RUNTIME_MB}MB)..."

    free_kb="$(df -k "$SDCARD_PATH" 2>/dev/null | awk 'NR==2 {print $4}')"
    case "$free_kb" in
        ''|*[!0-9]*) : ;;
        *) [ "$free_kb" -lt 204800 ] && return 1 ;;
    esac

    rm -rf "$CACHE_DIR/python" "$CACHE_DIR/py.tar.gz"
    mkdir -p "$CACHE_DIR" || return 1
    tgz="$CACHE_DIR/py.tar.gz"

    # busybox wget is the usual one here and takes neither -q nor --tries the
    # way GNU wget does, so each form is tried on its own. The certificate
    # bypass comes last: a stock handheld often has no CA bundle at all, and a
    # checksum-verified download over a bad certificate still beats no app.
    ok=1
    if command -v wget >/dev/null 2>&1; then
        wget -O "$tgz" "$RUNTIME_URL" && ok=0
        [ $ok -ne 0 ] && wget --no-check-certificate -O "$tgz" "$RUNTIME_URL" && ok=0
    fi
    if [ $ok -ne 0 ] && command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$tgz" "$RUNTIME_URL" && ok=0
        [ $ok -ne 0 ] && curl -fsSLk -o "$tgz" "$RUNTIME_URL" && ok=0
    fi
    [ $ok -ne 0 ] && { rm -f "$tgz"; return 1; }

    # Verified when the device has sha256sum, skipped with a note when it does
    # not - refusing to run at all would be worse than running an archive that
    # unpacked cleanly and whose interpreter starts.
    if command -v sha256sum >/dev/null 2>&1; then
        got="$(sha256sum "$tgz" 2>/dev/null | awk '{print $1}')"
        if [ "$got" != "$RUNTIME_SHA" ]; then
            log "Tai ve bi loi (sha256 khong khop). Bo qua."
            rm -f "$tgz"
            return 1
        fi
    else
        log "May khong co sha256sum, bo qua buoc kiem tra."
    fi

    tar xzf "$tgz" -C "$CACHE_DIR" 2>/dev/null || { rm -rf "$tgz" "$CACHE_DIR/python"; return 1; }
    rm -f "$tgz"
    chmod +x "$CACHE_PY" 2>/dev/null

    # An archive that unpacked but will not run - wrong architecture, a missing
    # loader - is 60MB of card wasted on something no later launch can use.
    if usable "$CACHE_PY"; then
        return 0
    fi
    log "Ban chay tai ve khong chay duoc tren may nay."
    rm -rf "$CACHE_DIR/python"
    return 1
}

PY="$(find_python)"
if [ -z "$PY" ]; then
    if download_python; then
        PY="$CACHE_PY"
        log "Da cai Python vao $CACHE_DIR/python"
    else
        fatal "May khong co Python va tai ban chay ve khong thanh cong." \
"Hay lam mot trong hai cach sau:

1. Tai ban cai day du cua RetroHub (da kem san Python) tai
   https://retrohub.xuanhoa493.com va chep de len thu muc Apps/RetroHub.

2. Noi may vao Wi-Fi roi mo lai RetroHub - app se tu tai ban chay ve.

--
The device has no Python and downloading the runtime failed.
Either reinstall RetroHub from the full package (Python included) at
https://retrohub.xuanhoa493.com, or connect the device to Wi-Fi and
open RetroHub again so it can fetch the runtime itself."
    fi
fi

# Got this far, so the previous failure - if any - is stale.
rm -f "$ERRLOG" 2>/dev/null

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
