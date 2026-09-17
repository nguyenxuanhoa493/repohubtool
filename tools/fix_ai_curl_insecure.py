import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_curl = """        cmd = [
            "curl", "-s", "-X", "POST","""
new_curl = """        cmd = [
            "curl", "-s", "-k", "-X", "POST","""

content = content.replace(old_curl, new_curl)

old_write = """        result = subprocess.run(cmd, capture_output=True, text=True)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(result.stdout.encode('utf-8'))"""

new_write = """        result = subprocess.run(cmd, capture_output=True, text=True)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        # If curl failed or returned empty stdout, return the stderr as a JSON error
        if not result.stdout.strip():
            err_msg = result.stderr if result.stderr else "Empty response from curl (Exit code: " + str(result.returncode) + ")"
            self.wfile.write(json.dumps({"error": "Curl Error: " + err_msg}).encode('utf-8'))
        else:
            self.wfile.write(result.stdout.encode('utf-8'))"""

content = content.replace(old_write, new_write)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed curl insecure and empty stdout handling!")
