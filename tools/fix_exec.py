import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the executeAiCommand
old_js = r"""        async function executeAiCommand(e, b64Cmd) {
            const cmd = decodeURIComponent(atob(b64Cmd));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.textContent = 'Đang chạy lệnh... ⏳';
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                
                const outLog = data.output || '(Không có kết quả trả về)';
                // Note: The AI still sees it as a text response from the user.
                const systemPromptText = `\[System Execution Result\]\\n\$\{outLog\}`;
                
                btn.textContent = '✅ Đã chạy';
                btn.className = 'btn btn-sm btn-green';
                btn.style.width = '100%';
                
                // Add the result to history"""

new_js = r"""        async function executeAiCommand(e, b64Cmd) {
            const cmd = decodeURIComponent(atob(b64Cmd));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                
                const outLog = data.output || '(Không có kết quả trả về)';
                // Note: The AI still sees it as a text response from the user.
                const systemPromptText = `[System Execution Result]\n${outLog}`;
                
                btn.innerHTML = '✅';
                btn.style.width = 'auto';
                btn.style.color = '#10b981';
                
                // Add the result to history"""

content = re.sub(old_js, new_js, content)

# Fix the catch block
old_catch = r"""            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.textContent = '⚡ Thực thi lệnh này trên máy';
            }"""
new_catch = r"""            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
            }"""
content = re.sub(old_catch, new_catch, content)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed executeAiCommand JS!")
