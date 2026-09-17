import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

ai_routes = """    if path == "/api/chat":
      try:
        post_data = self.rfile.read(content_len).decode("utf-8")
        # Use curl to bypass Python's missing SSL module on TrimUI
        cmd = [
            "curl", "-s", "-X", "POST",
            "https://ai.xuanhoa493.com/v1/chat/completions",
            "-H", "Content-Type: application/json",
            "-H", "Authorization: Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2",
            "-d", post_data
        ]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(result.stdout.encode('utf-8'))
      except Exception as e:
        self.send_json({"error": str(e)}, status=500)
      return

    if path == "/api/run_cmd":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        cmd_str = payload.get("cmd", "")
        import subprocess
        # Run it via sh
        p = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        out = p.stdout + p.stderr
        self.send_json({"output": out})
      except Exception as e:
        self.send_json({"error": str(e)}, status=500)
      return

    if path == "/api/youtube/playlists/import":"""

if 'if path == "/api/chat":' not in content:
    content = content.replace('    if path == "/api/youtube/playlists/import":', ai_routes)
    
with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Routes added successfully")
