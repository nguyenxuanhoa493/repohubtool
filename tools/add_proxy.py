import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject Python Route
python_route = """    if path == "/api/chat":
      post_data = self.rfile.read(content_len)
      try:
        req = urllib.request.Request('https://ai.xuanhoa493.com/v1/chat/completions', data=post_data, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2'
        }, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = response.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(result)
      except Exception as e:
        self.send_json({"error": str(e)}, status=500)
      return

    if path == "/api/stream/start":"""

content = content.replace('    if path == "/api/stream/start":', python_route)

# 2. Update JS fetch
old_fetch = """            try {
                const res = await fetch('https://ai.xuanhoa493.com/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2'
                    },"""

new_fetch = """            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },"""
content = content.replace(old_fetch, new_fetch)

# Just in case API returns error json containing 'error', handle it softly
old_reply = """                const data = await res.json();
                if (data.choices && data.choices.length > 0) {"""
new_reply = """                const data = await res.json();
                if (data.error) {
                    throw new Error(data.error);
                }
                if (data.choices && data.choices.length > 0) {"""
content = content.replace(old_reply, new_reply)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated with proxy!")
