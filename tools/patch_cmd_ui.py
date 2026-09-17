import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the single command block formatting
old_cmd_fmt = r"""                    return `<div style="background:#0a0e1a; border:1px dashed #38bdf8; border-radius:8px; padding:12px; margin:12px 0;">
                        <div style="font-family:monospace; color:#38bdf8; margin-bottom:12px; white-space:pre-wrap; font-size:13px;">\$\{rawCmd\}</div>
                        <button onclick="executeAiCommand\(event, '\$\{b64Cmd\}'\)" class="btn btn-sm btn-primary" style="width:100%; border-radius:8px; padding:8px;">⚡ Thực thi \(Chỉ lệnh này\)</button>
                    </div>`;"""

new_cmd_fmt = """                    return `<div style="display: inline-flex; align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 4px; padding: 2px 4px 2px 8px; margin: 4px 0; gap: 6px; max-width: 100%;">
                        <code style="font-family: monospace; color: #38bdf8; font-size: 13px; white-space: pre-wrap; word-break: break-all;">${rawCmd}</code>
                        <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh" style="background: transparent; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; color: #10b981; flex-shrink: 0; border-left: 1px solid #334155; outline: none;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                    </div>`;"""
content = re.sub(old_cmd_fmt, new_cmd_fmt, content)

# 2. Update the "Run All" block formatting
old_all_fmt = r"""                if \(cmdCount > 1\) \{
                    const b64Cmds = btoa\(encodeURIComponent\(JSON\.stringify\(allCmds\)\)\);
                    safeText \+= `<div style="margin-top:16px; border-top:1px solid #334155; padding-top:16px;">
                        <button onclick="executeAllAiCommands\(event, '\$\{b64Cmds\}'\)" class="btn btn-sm" style="background:#eab308; color:#000; width:100%; border-radius:8px; padding:8px; font-weight:bold; border:none; box-shadow:0 0 10px rgba\(234, 179, 8, 0\.3\);">⚡ Thực thi TẤT CẢ \(\$\{cmdCount\} lệnh\) tuần tự</button>
                    </div>`;
                \}"""

new_all_fmt = """                if (cmdCount > 1) {
                    const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                    safeText += `<div style="margin-top:8px;">
                        <button onclick="executeAllAiCommands(event, '${b64Cmds}')" class="btn btn-sm" style="background:#eab308; color:#000; border-radius:4px; padding:4px 12px; font-weight:bold; border:none; display:inline-flex; align-items:center; gap:6px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                            Thực thi tất cả (${cmdCount} lệnh)
                        </button>
                    </div>`;
                }"""
content = re.sub(old_all_fmt, new_all_fmt, content)

# 3. Update the execute logic for single command (button state update)
# Old logic:
#                btn.textContent = '✅ Đã chạy';
#                btn.className = 'btn btn-sm btn-green';
#                btn.style.width = '100%';
# And loading: btn.textContent = 'Đang chạy lệnh... ⏳';

old_single_exec = """        async function executeAiCommand(e, b64Cmd) {
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
                const systemPromptText = `[System Execution Result]\\n${outLog}`;
                
                btn.textContent = '✅ Đã chạy';
                btn.className = 'btn btn-sm btn-green';
                btn.style.width = '100%';"""

new_single_exec = """        async function executeAiCommand(e, b64Cmd) {
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
                btn.style.color = '#22c55e';"""
content = content.replace(old_single_exec, new_single_exec)

# Catch the error block for single exec
old_single_err = """            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.textContent = '⚡ Thực thi lệnh này trên máy';
            }"""
new_single_err = """            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
            }"""
content = content.replace(old_single_err, new_single_err)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched UI!")
