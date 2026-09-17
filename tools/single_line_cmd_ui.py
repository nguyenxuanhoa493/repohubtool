with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the replacement template for executable code blocks to 1 single line
old_block = """            // Format executable blocks FIRST ([CMD] or ```bash)
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

new_block = """            // Format executable blocks FIRST ([CMD] or ```bash) -> Single Row
            let cmdCount = 0;
            let allCmds = [];
            safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]|```(?:[a-zA-Z0-9]+)?\\n?([\\s\\S]*?)```/gi, (match, cmd1, cmd2) => {
                const cmdText = cmd1 || cmd2;
                cmdCount++;
                const rawCmd = cmdText.trim();
                allCmds.push(rawCmd);
                const b64Cmd = btoa(encodeURIComponent(rawCmd));
                
                return `<div style="display: flex; align-items: center; justify-content: space-between; background: #070a13; border: 1px solid #1e293b; border-radius: 6px; padding: 4px 6px 4px 10px; margin: 4px 0; gap: 8px; max-width: 100%;">
                    <code style="font-family: monospace; color: #38bdf8; font-size: 13px; line-height: 1.4; white-space: pre-wrap; word-break: break-all; flex: 1;">${rawCmd}</code>
                    <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); cursor: pointer; padding: 4px 6px; border-radius: 4px; color: #34d399; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; outline: none; transition: all 0.2s;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                </div>`;
            });
            
            // Format inline code (`)
            safeText = safeText.replace(/`([^`\\n]+)`/g, `<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 4px; font-size: 13px; color: #38bdf8;">$1</code>`);
            
            if (cmdCount > 1) {
                const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                safeText += `<div style="display: flex; justify-content: flex-end; margin-top: 6px;">
                    <div style="display: inline-flex; align-items: center; background: #070a13; border: 1px solid rgba(234, 179, 8, 0.35); border-radius: 6px; padding: 3px 6px 3px 10px; gap: 8px;">
                        <span style="font-family: monospace; color: #facc15; font-size: 12px; font-weight: 600;">⚡ Chạy tất cả (${cmdCount} lệnh)</span>
                        <button onclick="executeAllAiCommands(event, '${b64Cmds}')" title="Thực thi tất cả theo thứ tự" style="background: rgba(234, 179, 8, 0.15); border: none; cursor: pointer; padding: 3px 6px; border-radius: 4px; color: #facc15; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; outline: none; transition: all 0.2s;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                    </div>
                </div>`;
            }"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Replaced single line block successfully!")
else:
    print("Could not find old_block in content!")

# 2. Update executeAiCommand button states to icon-only
old_exec = """                btn.innerHTML = '✅ Xong';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';"""

new_exec = """                btn.innerHTML = '✅';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';"""

if old_exec in content:
    content = content.replace(old_exec, new_exec)
    print("Replaced executeAiCommand icon state successfully!")

# Also fix the starting state
content = content.replace("btn.innerHTML = '⏳ Chạy...';", "btn.innerHTML = '⏳';")

# 3. Update executeAllAiCommands button states to icon-only
old_all_btn = "btn.textContent = '✅ Đã chạy xong';"
new_all_btn = "btn.innerHTML = '✅';"

content = content.replace(old_all_btn, new_all_btn)
content = content.replace("btn.innerHTML = '⏳ Đang chạy...';", "btn.innerHTML = '⏳';")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Finished single-line update!")
