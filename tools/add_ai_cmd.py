import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Backend Route
old_route = """    if path == "/api/chat":"""
new_route = """    if path == "/api/run_cmd":
      post_data = self.rfile.read(content_len)
      try:
          import subprocess
          import json
          req_json = json.loads(post_data.decode('utf-8'))
          cmd = req_json.get('cmd', '')
          output = subprocess.getoutput(cmd)
          self.send_json({"output": output})
      except Exception as e:
          self.send_json({"error": str(e)}, status_code=500)
      return

    if path == "/api/chat":"""
content = content.replace(old_route, new_route)

# 2. Update System Prompt
old_prompt = """        let aiChatHistory = [
            { role: "system", content: "You are a helpful AI assistant integrated into a RetroHub gaming device web manager. Answer in Vietnamese. Be concise and friendly." }
        ];"""
new_prompt = """        let aiChatHistory = [
            { role: "system", content: "You are an AI assistant integrated into a RetroHub gaming console (TrimUI Smart Pro, Linux). Answer in Vietnamese. If you need to run a bash command on the device to fix an issue, wrap the EXACT command inside [CMD] and [/CMD] tags on new lines. Example:\\n[CMD]\\nls -la /mnt/SDCARD/\\n[/CMD]\\nThe UI will create an Execute button for the user to click, and send you back the output." }
        ];"""
content = content.replace(old_prompt, new_prompt)

# 3. Update appendChatMessage & JS helper
old_append = """            bubble.textContent = text;
            wrapper.appendChild(bubble);
            container.appendChild(wrapper);"""
new_append = """            // Escape HTML
            let safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            // Format [CMD] blocks
            safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]/g, (match, cmdText) => {
                const rawCmd = cmdText.trim();
                const safeCmd = rawCmd.replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\\n/g, ' ');
                return `<div style="background:#0a0e1a; border:1px dashed #38bdf8; border-radius:8px; padding:12px; margin:12px 0;">
                    <div style="font-family:monospace; color:#38bdf8; margin-bottom:12px; white-space:pre-wrap; font-size:13px;">${rawCmd}</div>
                    <button onclick="executeAiCommand(event, '${safeCmd}')" class="btn btn-sm btn-primary" style="width:100%; border-radius:8px; padding:8px;">⚡ Thực thi lệnh này trên máy</button>
                </div>`;
            });
            
            bubble.innerHTML = safeText;
            wrapper.appendChild(bubble);
            container.appendChild(wrapper);"""
content = content.replace(old_append, new_append)

# 4. Inject executeAiCommand & fetchCore logic
js_add = """        async function executeAiCommand(e, cmd) {
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
                const resultText = `Đã thực thi lệnh trên TrimUI.\\nKết quả:\\n\`\`\`\\n${outLog}\\n\`\`\``;
                
                btn.textContent = '✅ Đã chạy';
                btn.className = 'btn btn-sm btn-green';
                btn.style.width = '100%';
                
                // Add to chat and send to AI
                appendChatMessage('user', resultText);
                aiChatHistory.push({ role: 'user', content: resultText });
                
                // Send headless request
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                
                doHeadlessAiFetch();
                
            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.textContent = '⚡ Thực thi lệnh này trên máy';
            }
        }
        
        async function doHeadlessAiFetch() {
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: 'auto', messages: aiChatHistory })
                });
                if (!res.ok) throw new Error('Mã lỗi API: ' + res.status);
                const data = await res.json();
                if (data.error) {
                    const errMsg = typeof data.error === 'object' ? (data.error.message || JSON.stringify(data.error)) : data.error;
                    throw new Error(errMsg);
                }
                if (data.choices && data.choices.length > 0) {
                    const reply = data.choices[0].message.content;
                    appendChatMessage('assistant', reply);
                    aiChatHistory.push({ role: 'assistant', content: reply });
                } else {
                    appendChatMessage('assistant', 'Lỗi: Phản hồi từ AI bị rỗng.');
                }
            } catch (err) {
                appendChatMessage('assistant', '⚠️ Lỗi khi phản hồi: ' + err.message);
            } finally {
                const btn = document.getElementById('chat-submit-btn');
                btn.disabled = false;
                btn.textContent = 'Gửi ✈️';
            }
        }
"""
content = content.replace("        function clearAIChat() {", js_add + "\n        function clearAIChat() {")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Added AI Command Executor!")
