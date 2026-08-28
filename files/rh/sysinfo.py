# -*- coding: utf-8 -*-
"""Read-only facts about the device: network, processes, RAM, storage, battery."""

import os
import shutil
import subprocess

from .paths import SDCARD_PATH
from . import state
from .i18n import tr

def get_ip():
    try:
        out = subprocess.check_output("ip -4 addr show wlan0 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1", shell=True).decode().strip()
        if not out:
            out = subprocess.check_output("ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d: -f2", shell=True).decode().strip()
        return out if out else tr("not_connected")
    except:
        return tr("not_connected")

def is_proc_running(name_patterns):
    if isinstance(name_patterns, str):
        name_patterns = [name_patterns]
    try:
        for pid_dir in os.listdir('/proc'):
            if pid_dir.isdigit():
                try:
                    with open(f'/proc/{pid_dir}/comm', 'r') as f:
                        comm = f.read().strip()
                    for pat in name_patterns:
                        if pat in comm:
                            return True
                    with open(f'/proc/{pid_dir}/cmdline', 'rb') as f:
                        cmdline = f.read().decode('utf-8', errors='ignore')
                    for pat in name_patterns:
                        if pat in cmdline:
                            return True
                except Exception:
                    continue
    except Exception:
        pass
    return False

def is_port_listening(port_int):
    hex_port = f"{port_int:04X}"
    for tcp_file in ['/proc/net/tcp', '/proc/net/tcp6']:
        if os.path.exists(tcp_file):
            try:
                with open(tcp_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            local_addr = parts[1]
                            state = parts[3]
                            if ':' in local_addr:
                                p_hex = local_addr.split(':')[1]
                                if p_hex.upper() == hex_port and state == '0A':
                                    return True
            except Exception:
                pass
    return False
def is_sftpgo_running():
    return is_proc_running(['sftpgo']) or is_port_listening(8080) or is_port_listening(2022)

def is_ssh_running():
    return is_proc_running(['sshd', 'dropbear']) or is_port_listening(22)

def is_adb_running():
    return is_proc_running(['adbd']) or is_port_listening(5037)

def is_mtp_running():
    return is_proc_running(['MtpDaemon', 'mtp-server'])

def is_streamer_running():
    return is_proc_running(['streamer', 'ustreamer', 'mjpg_streamer']) or is_port_listening(8088)

def get_mac_address():
    try:
        mac = subprocess.check_output("cat /sys/class/net/wlan0/address 2>/dev/null || echo 'N/A'", shell=True).decode().strip()
        return mac if mac else "N/A"
    except Exception:
        return "N/A"

def get_ram_info():
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_data = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().split()[0]
                mem_data[key] = int(val) // 1024
        
        total = mem_data.get("MemTotal", 975)
        avail = mem_data.get("MemAvailable", mem_data.get("MemFree", 0))
        used = total - avail
        pct = int((used / total) * 100) if total > 0 else 0
        return f"{used} / {total} MB ({pct}% đã dùng)" if state.current_lang == "VI" else f"{used} / {total} MB ({pct}% used)"
    except Exception:
        return "N/A"
    
def detect_device_platform():
    if os.path.exists("/mnt/SDCARD"):
        if os.path.exists("/usr/trimui") or os.path.exists("/mnt/SDCARD/trimui"):
            return "TrimUI Handheld (Smart Pro / Brick)"
        elif os.path.exists("/mnt/SDCARD/.tmp_update") or os.path.exists("/mnt/SDCARD/miyoo"):
            return "Miyoo Handheld (Mini / Plus / A30)"
        elif os.path.exists("/mnt/SDCARD/Anbernic"):
            return "Anbernic Handheld (Linux OS)"
        return "Universal Linux Retro Handheld"
    return "Universal Retro Handheld"

def get_device_info_rows():
    ip = get_ip()
    mac = get_mac_address()
    mem_str = get_ram_info()
    sftp_st = "BẬT (8080/2022)" if is_sftpgo_running() else "TẮT"
    ssh_st = "BẬT (Cổng 22)" if is_ssh_running() else "TẮT"
    adb_st = "BẬT" if is_adb_running() else "TẮT"
    mtp_st = "BẬT" if is_mtp_running() else "TẮT"
    stm_st = "BẬT (8088)" if is_streamer_running() else "TẮT"

    services_summary = f"SFTP: {sftp_st} | SSH: {ssh_st} | ADB: {adb_st} | MTP: {mtp_st} | Stream: {stm_st}"
    plat_str = f"{detect_device_platform()}  |  RetroHub"

    if state.current_lang == "VI":
        return [
            ("1. Địa chỉ IP Wi-Fi & MAC", f"IP: {ip}  |  MAC: {mac}"),
            ("2. Tình trạng các Dịch vụ", services_summary),
            ("3. Bộ nhớ RAM Hệ thống", mem_str),
            ("4. Thiết bị & Nền tảng", plat_str)
        ]
    else:
        return [
            ("1. IP & MAC Address", f"IP: {ip}  |  MAC: {mac}"),
            ("2. Services Status", services_summary),
            ("3. System RAM", mem_str),
            ("4. Device Platform", plat_str)
        ]

def format_storage_bytes(bytes_val):
    if bytes_val >= 1024 * 1024 * 1024:
        return f"{bytes_val / (1024**3):.1f} GB"
    elif bytes_val >= 1024 * 1024:
        return f"{bytes_val / (1024**2):.1f} MB"
    else:
        return f"{bytes_val // 1024} KB"

def get_storage_info_rows():
    rows = []
    
    # 1. Main SD Card Storage
    sd_target = SDCARD_PATH if os.path.exists(SDCARD_PATH) else "/"
    total_b, used_b, free_b = 0, 0, 0
    try:
        total_b, used_b, free_b = shutil.disk_usage(sd_target)
        used_pct = int((used_b / total_b) * 100) if total_b > 0 else 0
        free_pct = 100 - used_pct
        
        sd_total_str = format_storage_bytes(total_b)
        sd_used_str = format_storage_bytes(used_b)
        sd_free_str = format_storage_bytes(free_b)
        
        if state.current_lang == "VI":
            rows.append({
                "title": f"1. Thẻ nhớ chính (SDCARD) — {used_pct}% đã dùng",
                "sub": f"Đã dùng {sd_used_str} / {sd_total_str} • Còn trống {sd_free_str} ({free_pct}%)",
                "pct": used_pct
            })
        else:
            rows.append({
                "title": f"1. Main SD Card Storage — {used_pct}% used",
                "sub": f"Used {sd_used_str} / {sd_total_str} • Free {sd_free_str} ({free_pct}%)",
                "pct": used_pct
            })
    except Exception:
        pass

    # 2. Roms folder statistics
    rom_dir = f"{SDCARD_PATH}/Roms"
    try:
        if os.path.exists(rom_dir):
            rom_systems = [d for d in os.listdir(rom_dir) if os.path.isdir(os.path.join(rom_dir, d)) and not d.startswith(".")]
            rom_count = 0
            rom_bytes = 0
            for d in rom_systems:
                dp = os.path.join(rom_dir, d)
                try:
                    files = os.listdir(dp)
                    rom_count += len(files)
                    for f in files:
                        fp = os.path.join(dp, f)
                        if os.path.isfile(fp):
                            rom_bytes += os.path.getsize(fp)
                except: pass
            
            rom_pct = int((rom_bytes / total_b) * 100) if total_b > 0 and rom_bytes > 0 else 0
            rom_sz_str = format_storage_bytes(rom_bytes)
            
            if state.current_lang == "VI":
                rows.append({
                    "title": f"2. Kho Game Đã Cài (/Roms) — {rom_sz_str}",
                    "sub": f"{len(rom_systems)} hệ máy • {rom_count} tệp ROM • Chiếm {rom_pct}% thẻ nhớ",
                    "pct": max(5, rom_pct) if rom_count > 0 else 0
                })
            else:
                rows.append({
                    "title": f"2. Installed Game Library (/Roms) — {rom_sz_str}",
                    "sub": f"{len(rom_systems)} systems • {rom_count} ROMs • Takes {rom_pct}% SD",
                    "pct": max(5, rom_pct) if rom_count > 0 else 0
                })
    except: pass

    # 3. System Flash / Root partition
    try:
        root_total, root_used, root_free = shutil.disk_usage("/")
        r_used_pct = int((root_used / root_total) * 100) if root_total > 0 else 0
        if state.current_lang == "VI":
            rows.append({
                "title": f"3. Bộ nhớ trong (Flash OS / Root) — {r_used_pct}%",
                "sub": f"Đã dùng {format_storage_bytes(root_used)} / {format_storage_bytes(root_total)} • Phân vùng Linux OS",
                "pct": r_used_pct
            })
        else:
            rows.append({
                "title": f"3. Internal Flash (OS / Root) — {r_used_pct}%",
                "sub": f"Used {format_storage_bytes(root_used)} / {format_storage_bytes(root_total)} • Linux OS Partition",
                "pct": r_used_pct
            })
    except: pass

    # 4. RAM / Memory
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_data = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().split()[0]
                mem_data[key] = int(val) // 1024
        m_total = mem_data.get("MemTotal", 975)
        m_avail = mem_data.get("MemAvailable", mem_data.get("MemFree", 0))
        m_used = m_total - m_avail
        m_pct = int((m_used / m_total) * 100) if m_total > 0 else 0

        if state.current_lang == "VI":
            rows.append({
                "title": f"4. Bộ nhớ RAM Hệ thống — {m_pct}% đang dùng",
                "sub": f"Đang dùng {m_used} MB / {m_total} MB RAM • Còn trống {m_avail} MB",
                "pct": m_pct
            })
        else:
            rows.append({
                "title": f"4. System RAM Memory — {m_pct}% in use",
                "sub": f"In Use {m_used} MB / {m_total} MB RAM • Free {m_avail} MB",
                "pct": m_pct
            })
    except: pass

    return rows
def get_battery_info():
    """Returns (capacity_percent, is_charging)."""
    capacity = 100
    is_charging = False
    cap_paths = [
        "/sys/class/power_supply/battery/capacity",
        "/sys/class/power_supply/axp2202-battery/capacity",
        "/sys/class/power_supply/axp-battery/capacity"
    ]
    stat_paths = [
        "/sys/class/power_supply/battery/status",
        "/sys/class/power_supply/axp2202-battery/status"
    ]
    for p in cap_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    capacity = int(f.read().strip())
                    break
            except Exception:
                pass
                
    for p in stat_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    st = f.read().strip().lower()
                    if "charging" in st:
                        is_charging = True
                    break
            except Exception:
                pass
                
    return capacity, is_charging
