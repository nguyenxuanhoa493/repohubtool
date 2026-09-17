with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the replacement template for executable code blocks
old_block = """            // Format executable blocks FIRST ([CMD] or ```bash)
            let cmdCount = 0;
            let allCmds = [];
            safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]|```(?:[a-zA-Z0-9]+)?\\n?([\\s\\S]*?)```/gi, (match, cmd1, cmd2) => {
                const cmdText = cmd1 || cmd2;
                cmdCount++;
                const rawCmd = cmdText.trim();
                allCmds.push(rawCmd);
                const b64Cmd = btoa(encodeURIComponent(rawCmd));
                
                return `<div style="display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 6px; margin: 8px 0; max-width: 100%; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <div style="background: #1e293b; padding: 6px 12px; font-size: 11px; color: #94a3b8; font-weight: bold; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
                        <span style="display:flex; align-items:center; gap:6px;">💻 BẢNG ĐIỀU KHIỂN TERMINAL</span>
                        <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh này" style="background: #10b981; border: none; cursor: pointer; padding: 4px 12px; border-radius: 4px; color: #fff; font-size: 11px; font-weight: bold; display: flex; align-items: center; gap: 4px; outline: none; transition: background 0.2s; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);">
                            ▶ CHẠY LỆNH
                        </button>
                    </div>
                    <code style="font-family: monospace; color: #38bdf8; font-size: 13.5px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; padding: 12px; display: block; background: #070a13;">${rawCmd}</code>
                </div>`;
            });
            
            // Format standard non-executable code blocks
            safeText = safeText.replace(/```(?:[a-zA-Z0-9]+)?\\n?([\\s\\S]*?)```/gi, (match, code) => {
                return `<div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px; margin: 6px 0; font-family: monospace; font-size: 13px; line-height: 1.4; white-space: pre-wrap; overflow-x: auto; max-height: 180px; overflow-y: auto;">${code.trim()}</div>`;
            });
            
            // Format inline code (`)
            safeText = safeText.replace(/`([^`\\n]+)`/g, `<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 4px; font-size: 13px; color: #38bdf8;">$1</code>`);
            
            if (cmdCount > 1) {
                const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                safeText += `<div style="display: flex; justify-content: flex-end; margin-top: 12px;">
                    <button onclick="executeAllAiCommands(event, '${b64Cmds}')" title="Thực thi tất cả theo thứ tự" style="background: #eab308; border: none; cursor: pointer; padding: 6px 16px; border-radius: 6px; color: #000; font-size: 12px; font-weight: bold; display: flex; align-items: center; gap: 6px; outline: none; box-shadow: 0 4px 6px rgba(234, 179, 8, 0.3);">
                        ⚡ CHẠY TẤT CẢ (${cmdCount} LỆNH)
                    </button>
                </div>`;
            }"""

new_block = """            // Format executable blocks FIRST ([CMD] or ```bash)
            let cmdCount = 0;
            let allCmds = [];
            safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]|```(?:[a-zA-Z0-9]+)?\\n?([\\s\\S]*?)```/gi, (match, cmd1, cmd2) => {
                const cmdText = cmd1 || cmd2;
                cmdCount++;
                const rawCmd = cmdText.trim();
                allCmds.push(rawCmd);
                const b64Cmd = btoa(encodeURIComponent(rawCmd));
                
                return `<div style="display: flex; flex-direction: column; background: #090d16; border: 1px solid #1e293b; border-radius: 6px; margin: 6px 0; max-width: 100%; overflow: hidden;">
                    <div style="background: #111827; padding: 3px 8px; font-size: 11px; color: #64748b; font-weight: 600; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
                        <span style="display:inline-flex; align-items:center; gap:4px; font-family: monospace; color: #94a3b8;">💻 bash</span>
                        <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); cursor: pointer; padding: 2px 8px; border-radius: 4px; color: #34d399; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; outline: none; transition: all 0.2s;">
                            ▶ Chạy
                        </button>
                    </div>
                    <code style="font-family: monospace; color: #38bdf8; font-size: 12.5px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; padding: 8px 10px; display: block; background: #060911;">${rawCmd}</code>
                </div>`;
            });
            
            // Format inline code (`)
            safeText = safeText.replace(/`([^`\\n]+)`/g, `<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 4px; font-size: 13px; color: #38bdf8;">$1</code>`);
            
            if (cmdCount > 1) {
                const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                safeText += `<div style="display: flex; justify-content: flex-end; margin-top: 6px;">
                    <button onclick="executeAllAiCommands(event, '${b64Cmds}')" title="Thực thi tất cả theo thứ tự" style="background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.4); cursor: pointer; padding: 3px 10px; border-radius: 4px; color: #facc15; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; outline: none; transition: all 0.2s;">
                        ⚡ Chạy tất cả (${cmdCount})
                    </button>
                </div>`;
            }"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Replaced code block rendering successfully!")
else:
    print("Could not find old_block in content!")

# 2. Update executeAiCommand button states
old_exec = """        async function executeAiCommand(e, b64Cmd) {
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
                
                btn.innerHTML = '✅';"""

new_exec = """        async function executeAiCommand(e, b64Cmd) {
            const cmd = decodeURIComponent(atob(b64Cmd));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳ Chạy...';
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
                
                btn.innerHTML = '✅ Xong';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';"""

if old_exec in content:
    content = content.replace(old_exec, new_exec)
    print("Replaced executeAiCommand successfully!")
else:
    print("Could not find old_exec in content!")

# 3. Update executeAllAiCommands button states and details
old_all = """        async function executeAllAiCommands(e, b64Cmds) {
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
            
            btn.textContent = '✅ Đã chạy tất cả';
            
            btn.style.background = '#22c55e';
            btn.style.color = '#fff';
            
            const systemPromptText = `[System Execution Result]\\n${combinedOutput.trim()}`;
            appendChatMessage('user', combinedOutput.trim(), true);"""

new_all = """        async function executeAllAiCommands(e, b64Cmds) {
            const cmds = JSON.parse(decodeURIComponent(atob(b64Cmds)));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳ Đang chạy...';
            
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
            
            btn.textContent = '✅ Đã chạy xong';
            btn.style.background = 'rgba(56, 189, 248, 0.15)';
            btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            btn.style.color = '#38bdf8';
            
            const systemPromptText = `[System Execution Result]\\n${combinedOutput.trim()}`;
            const safeCombined = combinedOutput.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const htmlText = `<details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px;">
                <summary style="cursor: pointer; font-size: 13px; font-weight: bold; color: #facc15; outline: none;">✅ Đã thực thi ${cmds.length} lệnh (Nhấn để xem kết quả)</summary>
                <div style="margin-top: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 200px; overflow-y: auto; color: #cbd5e1;">${safeCombined}</div>
            </details>`;
            appendChatMessage('user', htmlText, true);"""

if old_all in content:
    content = content.replace(old_all, new_all)
    print("Replaced executeAllAiCommands successfully!")
else:
    print("Could not find old_all in content!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Finished refinement!")
