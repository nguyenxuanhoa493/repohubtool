#!/bin/sh
# Remote SSH over Internet via Pinggy Tunnel for TrimUI Smart Pro / Linux Handhelds
# Usage: Run directly on TrimUI via Terminal, Dingux Commander, or SSH.

echo "=================================================="
echo "    RETROHUB: KHOI DONG SSH OVER INTERNET        "
echo "=================================================="

# 1. Start local SSH server if not running
if ! pidof sshd >/dev/null 2>&1 && ! pidof dropbear >/dev/null 2>&1; then
    echo "[*] Dang bat SSH Server noi bo..."
    /etc/init.d/sshd start 2>/dev/null || /usr/sbin/sshd -D &
    /etc/init.d/dropbear start 2>/dev/null || dropbear -R -B &
    sleep 1
fi

echo "[*] Dang ket noi toi Pinggy Tunnel qua cong 443..."
echo "[*] Vui long doi vai giay de lay dia chi ket noi cong khai..."
echo ""

# 2. Run SSH reverse tunnel using OpenSSH or Dropbear client
if command -v ssh >/dev/null 2>&1; then
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -p 443 \
        -R0:localhost:22 \
        tcp@a.pinggy.io
elif [ -x /mnt/SDCARD/System/bin/dbclient ] || command -v dbclient >/dev/null 2>&1; then
    DB_BIN="/mnt/SDCARD/System/bin/dbclient"
    [ ! -x "$DB_BIN" ] && DB_BIN="dbclient"
    
    KEY_OPT=""
    if [ -f /etc/dropbear/dropbear_ed25519_host_key ]; then
        KEY_OPT="-i /etc/dropbear/dropbear_ed25519_host_key"
    elif [ -f /etc/dropbear/dropbear_rsa_host_key ]; then
        KEY_OPT="-i /etc/dropbear/dropbear_rsa_host_key"
    elif [ -f ~/.ssh/id_dropbear ]; then
        KEY_OPT="-i ~/.ssh/id_dropbear"
    fi
    
    $DB_BIN -T -y -y $KEY_OPT -K 30 -p 443 -R 0:localhost:22 tcp@a.pinggy.io
else
    echo "[-] Loi: Khong tim thay client ssh hoac dbclient tren may!"
    exit 1
fi
