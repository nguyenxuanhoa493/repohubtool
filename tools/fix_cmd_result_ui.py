with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update /api/run_cmd in gameweb.py
old_run_cmd = """    if path == "/api/run_cmd":
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
      return"""

new_run_cmd = """    if path == "/api/run_cmd":
      try:
        payload = json.loads(self.rfile.read(content_len).decode("utf-8"))
        cmd_str = payload.get("cmd", "")
        import subprocess
        p = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        out = (p.stdout + p.stderr).strip()
        self.send_json({"output": out, "code": p.returncode, "cmd": cmd_str})
      except Exception as e:
        self.send_json({"error": str(e), "code": -1}, status=500)
      return"""

if old_run_cmd in content:
    content = content.replace(old_run_cmd, new_run_cmd)
    print("Updated /api/run_cmd successfully!")
else:
    print("Could not find old_run_cmd!")

# 2. Update appendChatMessage to handle isCard
old_append = """        function appendChatMessage(role, text, skipEscape = false) {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
            
            const bubble = document.createElement('div');
            bubble.style.maxWidth = '85%';
            bubble.style.padding = '8px 12px';
            bubble.style.borderRadius = '12px';
            bubble.style.fontSize = '14px';
            bubble.style.lineHeight = '1.4';
            bubble.style.whiteSpace = 'pre-wrap';
            bubble.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            
            if (role === 'user') {
                bubble.style.background = '#0284c7';
                bubble.style.color = '#fff';
                bubble.style.borderBottomRightRadius = '4px';
                bubble.style.border = '1px solid #0369a1';
            } else {
                bubble.style.background = '#1e293b';
                bubble.style.color = '#f8fafc';
                bubble.style.borderBottomLeftRadius = '4px';
                bubble.style.border = '1px solid #334155';
            }"""

new_append = """        function appendChatMessage(role, text, skipEscape = false, isCard = false) {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
            
            const bubble = document.createElement('div');
            bubble.style.maxWidth = '85%';
            bubble.style.fontSize = '14px';
            bubble.style.lineHeight = '1.4';
            bubble.style.whiteSpace = 'pre-wrap';
            bubble.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            
            if (isCard) {
                bubble.style.background = 'transparent';
                bubble.style.padding = '0';
                bubble.style.border = 'none';
                bubble.style.boxShadow = 'none';
            } else if (role === 'user') {
                bubble.style.background = '#0284c7';
                bubble.style.color = '#fff';
                bubble.style.padding = '8px 12px';
                bubble.style.borderRadius = '12px';
                bubble.style.borderBottomRightRadius = '4px';
                bubble.style.border = '1px solid #0369a1';
            } else {
                bubble.style.background = '#1e293b';
                bubble.style.color = '#f8fafc';
                bubble.style.padding = '8px 12px';
                bubble.style.borderRadius = '12px';
                bubble.style.borderBottomLeftRadius = '4px';
                bubble.style.border = '1px solid #334155';
            }"""

if old_append in content:
    content = content.replace(old_append, new_append)
    print("Updated appendChatMessage successfully!")
else:
    print("Could not find old_append!")

# 3. Update executeAllAiCommands and executeAiCommand
old_exec_all = """        async function executeAllAiCommands(e, b64Cmds) {
            const cmds = JSON.parse(decodeURIComponent(atob(b64Cmds)));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            
            let combinedOutput = "";
            for(let i=0; i<cmds.length; i++) {
                const cmd = cmds[i];
                try {
                    const res = await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: cmd})
                    });
                    const data = await res.json();
                    const outLog = data.output || '(Không có kết quả trả về)';
                    combinedOutput += `--- Kết quả lệnh ${i+1}/${cmds.length}: ${cmd} ---\\n${outLog}\\n\\n`;
                } catch(err) {
                    combinedOutput += `--- Lỗi lệnh ${i+1}/${cmds.length}: ${cmd} ---\\n${err.message}\\n\\n`;
                }
            }
            
            btn.innerHTML = '✅';
            btn.style.background = 'rgba(56, 189, 248, 0.15)';
            btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            btn.style.color = '#38bdf8';
            
            const systemPromptText = `[System Execution Result]\\n${combinedOutput.trim()}`;
            const safeCombined = combinedOutput.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const htmlText = `<details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px;">
                <summary style="cursor: pointer; font-size: 13px; font-weight: bold; color: #facc15; outline: none;">✅ Đã thực thi ${cmds.length} lệnh (Nhấn để xem kết quả)</summary>
                <div style="margin-top: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 200px; overflow-y: auto; color: #cbd5e1;">${safeCombined}</div>
            </details>`;
            appendChatMessage('user', htmlText, true);
            aiChatHistory.push({ role: 'user', content: systemPromptText });
            
            document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
            document.getElementById('chat-submit-btn').disabled = true;
            doHeadlessAiFetch();
        }"""

new_exec_all = """        async function executeAllAiCommands(e, b64Cmds) {
            const cmds = JSON.parse(decodeURIComponent(atob(b64Cmds)));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            
            let combinedOutput = "";
            for(let i=0; i<cmds.length; i++) {
                const cmd = cmds[i];
                try {
                    const res = await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: cmd})
                    });
                    const data = await res.json();
                    const rawOut = (data.output || '').trim();
                    const code = (typeof data.code !== 'undefined') ? data.code : 0;
                    const outLog = rawOut || (code === 0 ? '(Thành công - Không có output)' : `(Mã lỗi: ${code})`);
                    combinedOutput += `--- [${i+1}/${cmds.length}] ${cmd} (Exit: ${code}) ---\\n${outLog}\\n\\n`;
                } catch(err) {
                    combinedOutput += `--- [${i+1}/${cmds.length}] ${cmd} (Lỗi) ---\\n${err.message}\\n\\n`;
                }
            }
            
            btn.innerHTML = '✅';
            btn.style.background = 'rgba(56, 189, 248, 0.15)';
            btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            btn.style.color = '#38bdf8';
            
            const systemPromptText = `[System Execution Result]\\n${combinedOutput.trim()}`;
            const safeCombined = combinedOutput.trim().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #facc15; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                    <span style="display: flex; align-items: center; gap: 6px;">
                        <span>⚡</span> Đã thực thi ${cmds.length} lệnh
                    </span>
                    <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem log)</span>
                </summary>
                <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeCombined}</div>
            </details>`;
            appendChatMessage('user', htmlText, true, true);
            aiChatHistory.push({ role: 'user', content: systemPromptText });
            
            document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
            document.getElementById('chat-submit-btn').disabled = true;
            doHeadlessAiFetch();
        }"""

if old_exec_all in content:
    content = content.replace(old_exec_all, new_exec_all)
    print("Updated executeAllAiCommands successfully!")
else:
    print("Could not find old_exec_all!")

# 4. Update executeAiCommand
old_exec_single = """        async function executeAiCommand(e, b64Cmd) {
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
                const safeLog = outLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px;">
                    <summary style="cursor: pointer; font-size: 13px; font-weight: bold; color: #38bdf8; outline: none;">✅ Đã thực thi lệnh (Nhấn để xem kết quả)</summary>
                    <div style="margin-top: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 200px; overflow-y: auto; color: #cbd5e1;">${safeLog}</div>
                </details>`;
                
                const plainText = `Đã thực thi lệnh trên TrimUI.\\nKết quả:\\n\\`\\`\\`\\n${outLog}\\n\\`\\`\\``;
                
                btn.innerHTML = '✅';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';
                
                // Add to chat and send to AI
                appendChatMessage('user', htmlText, true);
                aiChatHistory.push({ role: 'user', content: plainText });"""

new_exec_single = """        async function executeAiCommand(e, b64Cmd) {
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
                
                const rawOut = (data.output || '').trim();
                const code = (typeof data.code !== 'undefined') ? data.code : 0;
                let displayLog = rawOut;
                if (!displayLog) {
                    if (code === 0) {
                        displayLog = '✓ Lệnh đã thực thi thành công (Không có text xuất ra terminal / Exit code: 0)';
                    } else {
                        displayLog = `⚠️ Lệnh hoàn tất với mã lỗi (Exit code: ${code})`;
                    }
                }
                const safeLog = displayLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #38bdf8; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span style="color: #34d399;">✓</span> Kết quả thực thi
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem log)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeLog}</div>
                </details>`;
                
                const plainText = `Đã thực thi lệnh trên TrimUI: \\`${cmd}\\`\\nKết quả:\\n\\`\\`\\`\\n${rawOut || '(Lệnh hoàn tất - Không có output)'}\\n\\`\\`\\`\\nExit code: ${code}`;
                
                btn.innerHTML = '✅';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';
                
                // Add to chat and send to AI
                appendChatMessage('user', htmlText, true, true);
                aiChatHistory.push({ role: 'user', content: plainText });"""

if old_exec_single in content:
    content = content.replace(old_exec_single, new_exec_single)
    print("Updated executeAiCommand successfully!")
else:
    print("Could not find old_exec_single!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("All updates applied!")
