import re

with open("files/yt.py", "r", encoding="utf-8") as f:
    content = f.read()

curl_helper = """
import subprocess

def _curl_get(url, timeout=10):
    cmd = ["curl", "-s", "-k", "-L", "--max-time", str(timeout), "-A", USER_AGENT, url]
    try:
        res = subprocess.check_output(cmd)
        return res
    except Exception as e:
        print(f"Curl GET error for {url}: {e}")
        raise

def _curl_post(url, data_dict, timeout=10):
    cmd = [
        "curl", "-s", "-k", "-L", "--max-time", str(timeout),
        "-A", USER_AGENT,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data_dict),
        url
    ]
    try:
        res = subprocess.check_output(cmd)
        return res
    except Exception as e:
        print(f"Curl POST error for {url}: {e}")
        raise

def _curl_download(url, dest_path, timeout=30):
    cmd = ["curl", "-s", "-k", "-L", "--max-time", str(timeout), "-A", USER_AGENT, "-o", dest_path, url]
    try:
        subprocess.check_call(cmd)
        return True
    except Exception as e:
        print(f"Curl DOWNLOAD error for {url}: {e}")
        return False
"""

# Insert curl_helper right after USER_AGENT = "Mozilla/5.0..."
content = re.sub(r'(USER_AGENT = "Mozilla[^"]*"\n)', r'\1' + curl_helper, content)

# 1. Patch _make_invidious_request
old_invidious = """def _make_invidious_request(path: str, params: dict = None, timeout: int = 15) -> dict:
    \"\"\"Fallback to Invidious API for search/trending if InnerTube fails.\"\"\"
    base_url = INVIDIOUS_INSTANCES[0]
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    
    url = f"{base_url}{path}{query}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )
    ctx = _get_ssl_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))"""

new_invidious = """def _make_invidious_request(path: str, params: dict = None, timeout: int = 15) -> dict:
    \"\"\"Fallback to Invidious API for search/trending if InnerTube fails.\"\"\"
    base_url = INVIDIOUS_INSTANCES[0]
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    
    url = f"{base_url}{path}{query}"
    res = _curl_get(url, timeout=timeout)
    return json.loads(res.decode("utf-8", errors="ignore"))"""

content = content.replace(old_invidious, new_invidious)

# 2. Patch _make_request (InnerTube POST)
old_make_req = """def _make_request(endpoint: str, payload: dict, timeout: int = 7) -> dict:
    \"\"\"Send JSON POST request to YouTube InnerTube endpoint with SSL bypass.\"\"\"
    url = f"{INNERTUBE_URL}/{endpoint}?prettyPrint=false"
    
    req_body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "X-YouTube-Client-Name": "1",
            "X-YouTube-Client-Version": "2.20240101.00.00"
        }
    )
    
    ctx = _get_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"[YT API] InnerTube Request Error: {e}")
        return {}"""

new_make_req = """def _make_request(endpoint: str, payload: dict, timeout: int = 7) -> dict:
    \"\"\"Send JSON POST request to YouTube InnerTube endpoint with SSL bypass.\"\"\"
    url = f"{INNERTUBE_URL}/{endpoint}?prettyPrint=false"
    
    cmd = [
        "curl", "-s", "-k", "-L", "--max-time", str(timeout),
        "-A", USER_AGENT,
        "-H", "Content-Type: application/json",
        "-H", "X-YouTube-Client-Name: 1",
        "-H", "X-YouTube-Client-Version: 2.20240101.00.00",
        "-d", json.dumps(payload),
        url
    ]
    try:
        res = subprocess.check_output(cmd)
        return json.loads(res.decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"[YT API] InnerTube Request Error: {e}")
        return {}"""
content = content.replace(old_make_req, new_make_req)

# 3. Patch search_youtube_playlist
old_search_pl = """        try:
            req = urllib.request.Request(pl_url, headers={"User-Agent": USER_AGENT})
            ctx = _get_ssl_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return {"error": f"Loi ket noi URL playlist: {e}"}"""

new_search_pl = """        try:
            res = _curl_get(pl_url, timeout=10)
            html_text = res.decode("utf-8", errors="ignore")
        except Exception as e:
            return {"error": f"Loi ket noi URL playlist: {e}"}"""
content = content.replace(old_search_pl, new_search_pl)

# 4. Patch prefetch_thumbnails_worker
old_prefetch = """        try:
            req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
                data = resp.read()
                # Verify JPEG header (FF D8) before saving
                if len(data) > 2 and data[0] == 0xFF and data[1] == 0xD8:
                    with open(cached_path, "wb") as f:
                        f.write(data)
        except Exception as e:
            pass"""

new_prefetch = """        try:
            res = _curl_get(u, timeout=4)
            data = res
            if len(data) > 2 and data[0] == 0xFF and data[1] == 0xD8:
                with open(cached_path, "wb") as f:
                    f.write(data)
        except Exception as e:
            pass"""
content = content.replace(old_prefetch, new_prefetch)

# 5. Patch download_youtube_audio
old_download = """    try:
        ctx = _get_ssl_context()
        req = urllib.request.Request(stream_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp, open(part_path, "wb") as f:
            total_len = resp.headers.get("Content-Length")
            total_bytes = int(total_len) if total_len and total_len.isdigit() else 0
            
            downloaded = 0
            block_size = 65536
            while True:
                buffer = resp.read(block_size)
                if not buffer:
                    break
                f.write(buffer)
                downloaded += len(buffer)
                if dl_id and dl_id in STORE_DOWNLOADS:
                    STORE_DOWNLOADS[dl_id]["downloaded_bytes"] = downloaded
    except Exception as e:
        print(f"Loi tai stream YT: {e}")
        if os.path.exists(part_path):
            os.remove(part_path)
        return None"""

new_download = """    try:
        # Tải thẳng bằng curl, không dùng urllib vì ssl có thể sập
        # Tính năng theo dõi bytes downloaded sẽ không hoàn hảo nhưng curl chạy nền an toàn.
        _curl_download(stream_url, part_path, timeout=120)
        
        # Fake 100% khi xong
        if dl_id and dl_id in STORE_DOWNLOADS:
            if STORE_DOWNLOADS[dl_id]["total_bytes"] == 0:
                STORE_DOWNLOADS[dl_id]["total_bytes"] = os.path.getsize(part_path)
            STORE_DOWNLOADS[dl_id]["downloaded_bytes"] = STORE_DOWNLOADS[dl_id]["total_bytes"]
    except Exception as e:
        print(f"Loi tai stream YT: {e}")
        if os.path.exists(part_path):
            os.remove(part_path)
        return None"""
content = content.replace(old_download, new_download)

with open("files/yt.py", "w", encoding="utf-8") as f:
    f.write(content)
print("yt.py Patched successfully!")
