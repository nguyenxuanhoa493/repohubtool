import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the AI Prompt so it knows it can use markdown bash too
old_prompt = r'(Mọi thao tác kiểm tra.*?chuyển thành CÂU LỆNH và đặt trong block \[CMD\]lệnh\[/CMD\])'
new_prompt = r'Mọi thao tác kiểm tra phải chuyển thành CÂU LỆNH và đặt trong block ```bash ... ``` (hoặc [CMD]...[/CMD])'
content = re.sub(old_prompt, new_prompt, content)

# 2. Extract the parsing logic to replace it
old_parsing_pattern = r'            // Format code blocks \(```\)[\s\S]*?bubble\.innerHTML = safeText;'

match = re.search(old_parsing_pattern, content)
if not match:
    print("Match not found!")
    exit(1)

old_str = match.group(0)

new_parsing = """            // Format executable blocks FIRST ([CMD] or ```bash)
            let cmdCount = 0;
            let allCmds = [];
            safeText = safeText.replace(/\\[CMD\\]([\\s\\S]*?)\\[\\/CMD\\]|```(?:bash|sh|shell|cmd)\\n([\\s\\S]*?)```/gi, (match, cmd1, cmd2) => {
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
            }

            bubble.innerHTML = safeText;"""

content = content.replace(old_str, new_parsing)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated JS parser successfully!")
