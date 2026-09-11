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

# 2. Run SSH reverse tunnel
ssh -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -p 443 \
    -R0:localhost:22 \
    tcp@a.pinggy.io
