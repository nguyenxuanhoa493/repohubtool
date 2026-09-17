with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update appendChatMessage
old_format = """                // Format [CMD] blocks
                safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]/g, (match, cmdText) => {
                    const rawCmd = cmdText.trim();
                    const safeCmd = rawCmd.replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/\\n/g, ' ');
                    return `<div style="background:#0a0e1a; border:1px dashed #38bdf8; border-radius:8px; padding:12px; margin:12px 0;">
                        <div style="font-family:monospace; color:#38bdf8; margin-bottom:12px; white-space:pre-wrap; font-size:13px;">${rawCmd}</div>
                        <button onclick="executeAiCommand(event, '${safeCmd}')" class="btn btn-sm btn-primary" style="width:100%; border-radius:8px; padding:8px;">⚡ Thực thi lệnh này trên máy</button>
                    </div>`;
                });"""

new_format = """                // Format [CMD] blocks
                let cmdCount = 0;
                let allCmds = [];
                safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]/g, (match, cmdText) => {
                    cmdCount++;
                    const rawCmd = cmdText.trim();
                    allCmds.push(rawCmd);
                    const b64Cmd = btoa(encodeURIComponent(rawCmd));
                    return `<div style="background:#0a0e1a; border:1px dashed #38bdf8; border-radius:8px; padding:12px; margin:12px 0;">
                        <div style="font-family:monospace; color:#38bdf8; margin-bottom:12px; white-space:pre-wrap; font-size:13px;">${rawCmd}</div>
                        <button onclick="executeAiCommand(event, '${b64Cmd}')" class="btn btn-sm btn-primary" style="width:100%; border-radius:8px; padding:8px;">⚡ Thực thi (Chỉ lệnh này)</button>
                    </div>`;
                });
                
                if (cmdCount > 1) {
                    const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                    safeText += `<div style="margin-top:16px; border-top:1px solid #334155; padding-top:16px;">
                        <button onclick="executeAllAiCommands(event, '${b64Cmds}')" class="btn btn-sm" style="background:#eab308; color:#000; width:100%; border-radius:8px; padding:8px; font-weight:bold; border:none; box-shadow:0 0 10px rgba(234, 179, 8, 0.3);">⚡ Thực thi TẤT CẢ (${cmdCount} lệnh) tuần tự</button>
                    </div>`;
                }"""
if old_format in content:
    content = content.replace(old_format, new_format)
else:
    print("WARNING: Could not find old_format!")

# 2. Update executeAiCommand & add executeAllAiCommands
old_exec = """        async function executeAiCommand(e, cmd) {"""
new_exec = """        async function executeAllAiCommands(e, b64Cmds) {
            const cmds = JSON.parse(decodeURIComponent(atob(b64Cmds)));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.textContent = `Đang chạy ${cmds.length} lệnh... ⏳`;
            
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
            btn.className = 'btn btn-sm btn-green';
            btn.style.background = '#22c55e';
            btn.style.color = '#fff';
            
            const systemPromptText = `[System Execution Result]\\n${combinedOutput.trim()}`;
            appendChatMessage('user', combinedOutput.trim(), true);
            aiChatHistory.push({ role: 'user', content: systemPromptText });
            
            document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
            document.getElementById('chat-submit-btn').disabled = true;
            doHeadlessAiFetch();
        }

        async function executeAiCommand(e, b64Cmd) {
            const cmd = decodeURIComponent(atob(b64Cmd));"""
if old_exec in content:
    content = content.replace(old_exec, new_exec)
else:
    print("WARNING: Could not find old_exec!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated gameweb.py!")
