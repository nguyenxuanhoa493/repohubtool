import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the System Prompt with the new log paths
old_prompt_section = r"\[TÀI NGUYÊN HỆ THỐNG & ĐƯỜNG DẪN QUAN TRỌNG\].*?\[CÁC TRƯỜNG HỢP"
new_prompt_section = """[TÀI NGUYÊN HỆ THỐNG & ĐƯỜNG DẪN QUAN TRỌNG]
- Thẻ nhớ gốc: /mnt/SDCARD/
- Thư mục ROMs game: /mnt/SDCARD/Roms/<tên_hệ_máy>/ (Ví dụ: GBA, PS, SNES)
- Thư mục BIOS: /mnt/SDCARD/BIOS/
- Thư mục File Save (.srm) & State (.state): /mnt/SDCARD/Saves/
- Cấu hình RetroArch: /mnt/SDCARD/RetroArch/retroarch.cfg
- Cấu hình Core RetroArch: /mnt/SDCARD/RetroArch/config/
- Log RetroArch (rất quan trọng khi văng game): /mnt/SDCARD/RetroArch/.retroarch/logs/
- Ứng dụng RetroHub: /mnt/SDCARD/Apps/RetroHub/
- Log của RetroHub App (Web Server): /mnt/SDCARD/Apps/RetroHub/gameweb.log hoặc nohup.out

[CÁC TRƯỜNG HỢP"""
content = re.sub(old_prompt_section, new_prompt_section, content, flags=re.DOTALL)

# 2. Fix the [CMD] Parsing Logic
# It currently has: safeText = safeText.replace(/\[CMD\]([\s\S]*?)\[\/CMD\]/g, ...
# Let's replace the whole block starting from // Format [CMD] blocks up to bubble.innerHTML = safeText;

old_cmd_block = r"                // Format \[CMD\] blocks.*?bubble\.innerHTML = safeText;"
new_cmd_block = """                // Format [CMD] blocks
                let cmdCount = 0;
                let allCmds = [];
                safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]/g, (match, cmdText) => {
                    cmdCount++;
                    const rawCmd = cmdText.trim();
                    allCmds.push(rawCmd);
                    const b64Cmd = btoa(encodeURIComponent(rawCmd));
                    return `<div style="display: inline-flex; align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 4px; padding: 2px 4px 2px 8px; margin: 4px 0; gap: 6px; max-width: 100%;">
                        <code style="font-family: monospace; color: #38bdf8; font-size: 13px; white-space: pre-wrap; word-break: break-all;">${rawCmd}</code>
                        <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh" style="background: transparent; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; color: #10b981; flex-shrink: 0; border-left: 1px solid #334155; outline: none;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                    </div>`;
                });
                
                if (cmdCount > 1) {
                    const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                    safeText += `<div style="margin-top:8px;">
                        <button onclick="executeAllAiCommands(event, '${b64Cmds}')" class="btn btn-sm" style="background:#eab308; color:#000; border-radius:4px; padding:4px 12px; font-weight:bold; border:none; display:inline-flex; align-items:center; gap:6px; cursor:pointer;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                            Thực thi tất cả (${cmdCount} lệnh)
                        </button>
                    </div>`;
                }

                bubble.innerHTML = safeText;"""
content = re.sub(old_cmd_block, new_cmd_block, content, flags=re.DOTALL)


# 3. Replace the entire execute JS block
# From `async function executeAiCommand` to the end of the script tag.
old_exec_block = r"        async function executeAiCommand\(e, cmd\).*?</script>"
new_exec_block = """        async function executeAllAiCommands(e, b64Cmds) {
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
            
            btn.innerHTML = '✅ Đã chạy tất cả';
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
                const systemPromptText = `[System Execution Result]\\n${outLog}`;
                
                btn.innerHTML = '✅';
                btn.style.width = 'auto';
                btn.style.color = '#10b981';
                
                appendChatMessage('user', outLog, true);
                aiChatHistory.push({ role: 'user', content: systemPromptText });
                
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                doHeadlessAiFetch();
            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
            }
        }
    </script>"""
content = re.sub(old_exec_block, new_exec_block, content, flags=re.DOTALL)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Final fix applied successfully!")
