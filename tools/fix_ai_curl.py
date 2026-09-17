with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_code = """    if path == "/api/chat":
      post_data = self.rfile.read(content_len)
      try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request('https://ai.xuanhoa493.com/v1/chat/completions', data=post_data, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2'
        }, method='POST')
        with urllib.request.urlopen(req, timeout=45, context=ctx) as response:
            result = response.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(result)
      except Exception as e:
        self.send_json({"error": str(e)}, status_code=500)
      return"""

new_code = """    if path == "/api/chat":
      post_data = self.rfile.read(content_len)
      try:
        import subprocess
        cmd = [
            "curl", "-s", "-k", "-X", "POST",
            "https://ai.xuanhoa493.com/v1/chat/completions",
            "-H", "Content-Type: application/json",
            "-H", "Authorization: Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2",
            "-d", post_data.decode('utf-8')
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        if proc.returncode == 0:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(proc.stdout)
        else:
            self.send_json({"error": "Lỗi cURL: " + proc.stderr.decode('utf-8', errors='replace')}, status_code=500)
      except Exception as e:
        self.send_json({"error": "Lỗi máy chủ: " + str(e)}, status_code=500)
      return"""

content = content.replace(old_code, new_code)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed AI Proxy to use curl!")
