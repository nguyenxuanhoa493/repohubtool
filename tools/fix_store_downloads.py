with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

import re

# 1. Replace background_download_store_game
old_dl_worker = r'def background_download_store_game\([\s\S]*?STORE_DOWNLOADS\[dl_id\]\["error_msg"\] = str\(e\)'

new_dl_worker = """def background_download_store_game(
    dl_id, sys_code, game_title, rom_url, filename, img_url
):
  with STORE_DOWNLOADS_LOCK:
    STORE_DOWNLOADS[dl_id] = {
        "id": dl_id,
        "title": game_title,
        "sys_code": sys_code,
        "filename": filename,
        "status": "downloading",
        "progress_pct": 0,
        "speed_str": "0 KB/s",
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "error_msg": "",
    }

  try:
    target_rom_dir = resolve_rom_dir(sys_code)
  except Exception:
    target_rom_dir = os.path.join(ROMS_DIR, sys_code)
  os.makedirs(target_rom_dir, exist_ok=True)
  target_rom_path = os.path.join(target_rom_dir, filename)

  target_img_dir = os.path.join(IMGS_DIR, sys_code)
  os.makedirs(target_img_dir, exist_ok=True)
  base_name = os.path.splitext(filename)[0]
  target_img_path = os.path.join(target_img_dir, base_name + ".png")

  # 1. Tải ảnh Box Art (nếu có)
  if img_url:
    try:
      download_image_to_file(img_url, target_img_path, timeout=10)
    except Exception as e:
      print(f"Store download boxart error: {e}")

  # 2. Tải ROM game bằng curl với theo dõi dung lượng và tốc độ thực tế
  temp_rom_path = target_rom_path + ".tmp_dl"
  if os.path.exists(temp_rom_path):
    try:
      os.remove(temp_rom_path)
    except Exception:
      pass

  try:
    # Lấy kích thước Content-Length trước qua curl HEAD
    total_sz = 0
    try:
      head_cmd = [
          "curl", "-s", "-I", "-k", "-L", "--max-time", "6",
          "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          "-e", rom_url,
          rom_url
      ]
      head_res = subprocess.run(head_cmd, capture_output=True, text=True)
      for line in head_res.stdout.splitlines():
        if line.lower().startswith("content-length:"):
          total_sz = int(line.split(":", 1)[1].strip())
    except Exception:
      total_sz = 0

    with STORE_DOWNLOADS_LOCK:
      STORE_DOWNLOADS[dl_id]["total_bytes"] = total_sz

    # Chạy tiến trình curl tải ROM
    dl_cmd = [
        "curl", "-s", "-k", "-L",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-e", rom_url,
        "-o", temp_rom_path,
        rom_url
    ]
    proc = subprocess.Popen(dl_cmd)

    t_last = time.time()
    b_last = 0

    # Vòng lặp theo dõi tiến độ ghi file vào thẻ nhớ
    while proc.poll() is None:
      time.sleep(0.3)
      if os.path.exists(temp_rom_path):
        cur_sz = os.path.getsize(temp_rom_path)
        now = time.time()
        elapsed = max(0.001, now - t_last)
        if elapsed >= 0.4:
          speed = (cur_sz - b_last) / elapsed
          speed_str = (
              f"{speed / (1024*1024):.1f} MB/s"
              if speed > 1024 * 1024
              else f"{int(speed / 1024)} KB/s"
          )
          pct = int((cur_sz / total_sz) * 100) if total_sz > 0 else min(95, int(cur_sz / (1024*1024) * 8))
          with STORE_DOWNLOADS_LOCK:
            STORE_DOWNLOADS[dl_id]["progress_pct"] = max(1, min(99, pct))
            STORE_DOWNLOADS[dl_id]["downloaded_bytes"] = cur_sz
            STORE_DOWNLOADS[dl_id]["speed_str"] = speed_str
          t_last = now
          b_last = cur_sz

    ret_code = proc.wait()
    if ret_code != 0:
      raise RuntimeError(f"Lỗi mạng khi tải (Curl exit code: {ret_code})")

    final_sz = os.path.getsize(temp_rom_path) if os.path.exists(temp_rom_path) else 0
    if final_sz < 64:
      raise RuntimeError("File tải về rỗng hoặc lỗi kết nối máy chủ")

    if os.path.exists(temp_rom_path):
      os.replace(temp_rom_path, target_rom_path)

    with STORE_DOWNLOADS_LOCK:
      STORE_DOWNLOADS[dl_id]["status"] = "completed"
      STORE_DOWNLOADS[dl_id]["progress_pct"] = 100
      STORE_DOWNLOADS[dl_id]["downloaded_bytes"] = final_sz
      STORE_DOWNLOADS[dl_id]["speed_str"] = "Xong"

  except Exception as e:
    print(f"Store download ROM error: {e}")
    if os.path.exists(temp_rom_path):
      try:
        os.remove(temp_rom_path)
      except Exception:
        pass
    with STORE_DOWNLOADS_LOCK:
      STORE_DOWNLOADS[dl_id]["status"] = "error"
      STORE_DOWNLOADS[dl_id]["error_msg"] = str(e)"""

content = re.sub(old_dl_worker, new_dl_worker, content, count=1)

# 2. Replace download_image_to_file to use curl directly
old_img_func = r'def download_image_to_file\(img_url, target_path, timeout=15\):[\s\S]*?return False, str\(e2\)'

new_img_func = """def download_image_to_file(img_url, target_path, timeout=15):
  if img_url.startswith("//"):
    img_url = "https:" + img_url

  raw_data = None
  try:
    cmd = [
        "curl", "-s", "-L", "-k", "--max-time", str(timeout),
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-e", img_url,
        img_url
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and len(res.stdout) > 64:
      raw_data = res.stdout
  except Exception:
    pass

  if not raw_data or len(raw_data) < 64:
    return False, "Empty or invalid image data"

  try:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    save_boxart_png(raw_data, target_path)
    return True, ""
  except Exception as e:
    try:
      with open(target_path, "wb") as f:
        f.write(raw_data)
      return True, ""
    except Exception as e2:
      return False, str(e2)"""

content = re.sub(old_img_func, new_img_func, content, count=1)

# 3. Update frontend startStoreDownloadPolling
old_polling = """        function startStoreDownloadPolling() {
            const banner = document.getElementById('store-download-banner');
            banner.style.display = 'block';

            if (storeDlInterval) clearInterval(storeDlInterval);
            storeDlInterval = setInterval(async () => {
                try {
                    const res = await fetch('/api/store/download/status');
                    const data = await res.json();
                    if (data.ok && data.downloads && data.downloads.length > 0) {
                        const active = data.downloads[data.downloads.length - 1];
                        document.getElementById('store-dl-title').innerText = `Đang tải: ${active.title} (${active.sys_code})`;
                        document.getElementById('store-dl-pct').innerText = `${active.progress_pct}%`;
                        document.getElementById('store-dl-bar').style.width = `${active.progress_pct}%`;
                        document.getElementById('store-dl-speed').innerText = `Tốc độ: ${active.speed_str || '0 KB/s'}`;
                        document.getElementById('store-dl-status').innerText = active.status === 'completed' ? '✓ Đã tải xong và lưu vào thẻ nhớ!' : (active.status === 'error' ? 'Lỗi tải' : 'Đang nhận tệp...');

                        if (active.status === 'completed' || active.status === 'error') {
                            clearInterval(storeDlInterval);
                            setTimeout(() => { banner.style.display = 'none'; }, 4000);
                            loadStoreGames();
                            loadSystems();
                        }
                    } else {
                        clearInterval(storeDlInterval);
                        banner.style.display = 'none';
                    }
                } catch (e) {}
            }, 1000);
        }"""

new_polling = """        function startStoreDownloadPolling() {
            const banner = document.getElementById('store-download-banner');
            banner.style.display = 'block';

            if (storeDlInterval) clearInterval(storeDlInterval);
            storeDlInterval = setInterval(async () => {
                try {
                    const res = await fetch('/api/store/download/status');
                    const data = await res.json();
                    if (data.ok && data.downloads && data.downloads.length > 0) {
                        const active = data.downloads[data.downloads.length - 1];
                        const pct = active.progress_pct || 0;
                        document.getElementById('store-dl-title').innerText = `Đang tải: ${active.title} (${active.sys_code})`;
                        document.getElementById('store-dl-pct').innerText = `${pct}%`;
                        document.getElementById('store-dl-bar').style.width = `${pct}%`;
                        
                        let sizeInfo = '';
                        if (active.total_bytes > 0) {
                            const curMb = (active.downloaded_bytes / (1024 * 1024)).toFixed(1);
                            const totMb = (active.total_bytes / (1024 * 1024)).toFixed(1);
                            sizeInfo = ` (${curMb} / ${totMb} MB)`;
                        } else if (active.downloaded_bytes > 0) {
                            const curMb = (active.downloaded_bytes / (1024 * 1024)).toFixed(1);
                            sizeInfo = ` (${curMb} MB)`;
                        }

                        document.getElementById('store-dl-speed').innerText = `Tốc độ: ${active.speed_str || '0 KB/s'}${sizeInfo}`;
                        
                        if (active.status === 'completed') {
                            document.getElementById('store-dl-status').innerText = '✓ Đã tải xong và lưu vào thẻ nhớ!';
                            document.getElementById('store-dl-status').style.color = '#34d399';
                        } else if (active.status === 'error') {
                            document.getElementById('store-dl-status').innerText = `❌ ${active.error_msg || 'Lỗi tải game'}`;
                            document.getElementById('store-dl-status').style.color = '#f87171';
                        } else {
                            document.getElementById('store-dl-status').innerText = 'Đang nhận tệp...';
                            document.getElementById('store-dl-status').style.color = 'var(--text-sub)';
                        }

                        if (active.status === 'completed' || active.status === 'error') {
                            clearInterval(storeDlInterval);
                            setTimeout(() => { banner.style.display = 'none'; }, 4000);
                            loadStoreGames(false);
                            loadSystems();
                        }
                    } else {
                        clearInterval(storeDlInterval);
                        banner.style.display = 'none';
                    }
                } catch (e) {}
            }, 350);
        }"""

if old_polling in content:
    content = content.replace(old_polling, new_polling)
    print("Updated startStoreDownloadPolling JS function!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Applied fix_store_downloads successfully!")
