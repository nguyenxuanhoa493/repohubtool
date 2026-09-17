import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_cmd_block = r"            // Format \[CMD\] blocks.*?bubble\.innerHTML = safeText;"
new_cmd_block = r"""            // Format [CMD] blocks
            let cmdCount = 0;
            let allCmds = [];
            safeText = safeText.replace(/\[CMD\]([\s\S]*?)\[\/CMD\]/g, (match, cmdText) => {
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

if re.search(old_cmd_block, content, flags=re.DOTALL):
    content = re.sub(old_cmd_block, lambda m: new_cmd_block, content, flags=re.DOTALL)
    with open("files/gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed [CMD] block formatting!")
else:
    print("Could not find old_cmd_block!")
