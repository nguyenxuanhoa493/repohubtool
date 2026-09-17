with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove the "Đính kèm Log" button
old_form = """<form id="chat-form" onsubmit="sendChatMessage(event)" style="display:flex; gap:12px;">
                    <button type="button" class="btn btn-secondary" style="border-radius:30px; padding:0 20px; font-size:14px;" onclick="fetchAndAttachLog()" title="Đính kèm Log hệ thống để nhờ AI phân tích lỗi">📄 Đính kèm Log</button>
                    <input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:14px 24px; color:#fff; font-size:15px; outline:none; transition:border 0.2s;" onfocus="this.style.borderColor='#0284c7'" onblur="this.style.borderColor='#334155'" required>
                    <button type="submit" id="chat-submit-btn" class="btn btn-primary" style="border-radius:30px; padding:0 32px; font-size:15px; font-weight:700;">Gửi ✈️</button>
                </form>"""
new_form = """<form id="chat-form" onsubmit="sendChatMessage(event)" style="display:flex; gap:12px;">
                    <input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:14px 24px; color:#fff; font-size:15px; outline:none; transition:border 0.2s;" onfocus="this.style.borderColor='#0284c7'" onblur="this.style.borderColor='#334155'" required>
                    <button type="submit" id="chat-submit-btn" class="btn btn-primary" style="border-radius:30px; padding:0 32px; font-size:15px; font-weight:700;">Gửi ✈️</button>
                </form>"""
content = content.replace(old_form, new_form)

# 2. Update the System Prompt to inform AI about log paths
old_prompt = """        let aiChatHistory = [
            { role: "system", content: "You are an AI assistant integrated into a RetroHub gaming console (TrimUI Smart Pro, Linux). Answer in Vietnamese. If you need to run a bash command on the device to fix an issue, wrap the EXACT command inside [CMD] and [/CMD] tags on new lines. Example:\\n[CMD]\\nls -la /mnt/SDCARD/\\n[/CMD]\\nThe UI will create an Execute button for the user to click, and send you back the output." }
        ];"""
new_prompt = """        let aiChatHistory = [
            { role: "system", content: "You are an AI assistant integrated into a RetroHub gaming console (TrimUI Smart Pro, Linux). Answer in Vietnamese. If you need to run a bash command on the device to read logs or fix an issue, wrap the EXACT command inside [CMD] and [/CMD] tags on new lines. Example:\\n[CMD]\\nls -la /mnt/SDCARD/\\n[/CMD]\\nRetroArch log is at /mnt/SDCARD/RetroArch/retroarch.log. App logs are in /tmp/. The UI will create an Execute button for the user to click, and send you back the output." }
        ];"""
content = content.replace(old_prompt, new_prompt)

# 3. Update appendChatMessage to handle isCmdResult visually
old_append = """        function appendChatMessage(role, text) {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
            
            const bubble = document.createElement('div');
            bubble.style.maxWidth = '85%';
            bubble.style.padding = '14px 18px';
            bubble.style.borderRadius = '16px';
            bubble.style.fontSize = '15px';
            bubble.style.lineHeight = '1.6';
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
            }
            
            // Escape HTML
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

new_append = """        function appendChatMessage(role, text, isCmdResult = false) {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            
            // If it's a command result, center it and style it like a console
            if (isCmdResult) {
                wrapper.style.justifyContent = 'center';
                wrapper.style.margin = '10px 0';
                
                const consoleBox = document.createElement('div');
                consoleBox.style.background = '#000';
                consoleBox.style.border = '1px solid #334155';
                consoleBox.style.borderRadius = '8px';
                consoleBox.style.padding = '12px';
                consoleBox.style.width = '90%';
                consoleBox.style.fontFamily = 'monospace';
                consoleBox.style.fontSize = '12px';
                consoleBox.style.color = '#a3e635';
                consoleBox.style.boxShadow = 'inset 0 0 10px rgba(0,0,0,0.5)';
                
                const header = document.createElement('div');
                header.style.color = '#64748b';
                header.style.marginBottom = '8px';
                header.style.paddingBottom = '8px';
                header.style.borderBottom = '1px solid #334155';
                header.style.display = 'flex';
                header.style.justifyContent = 'space-between';
                header.innerHTML = '<span><span style="color:#eab308">⚡</span> System Output</span><span>TrimUI Smart Pro</span>';
                
                const content = document.createElement('div');
                content.style.whiteSpace = 'pre-wrap';
                content.style.maxHeight = '250px';
                content.style.overflowY = 'auto';
                
                // Keep the original text but escape basic HTML
                let safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                content.innerHTML = safeText;
                
                consoleBox.appendChild(header);
                consoleBox.appendChild(content);
                wrapper.appendChild(consoleBox);
            } else {
                // Normal chat bubble styling
                wrapper.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
                
                const bubble = document.createElement('div');
                bubble.style.maxWidth = '85%';
                bubble.style.padding = '14px 18px';
                bubble.style.borderRadius = '16px';
                bubble.style.fontSize = '15px';
                bubble.style.lineHeight = '1.6';
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
                }
                
                // Escape HTML
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
            }
            
            container.appendChild(wrapper);"""
content = content.replace(old_append, new_append)

# 4. Modify executeAiCommand to use isCmdResult=true and remove `fetchAndAttachLog` completely
old_exec = """                const resultText = `Đã thực thi lệnh trên TrimUI.\\nKết quả:\\n\`\`\`\\n${outLog}\\n\`\`\``;
                
                btn.textContent = '✅ Đã chạy';
                btn.className = 'btn btn-sm btn-green';
                btn.style.width = '100%';
                
                // Add to chat and send to AI
                appendChatMessage('user', resultText);
                aiChatHistory.push({ role: 'user', content: resultText });"""

new_exec = """                // Note: The AI still sees it as a text response from the user.
                const systemPromptText = `[System Execution Result]\\n${outLog}`;
                
                btn.textContent = '✅ Đã chạy';
                btn.className = 'btn btn-sm btn-green';
                btn.style.width = '100%';
                
                // Pass true for isCmdResult so it renders as a sleek terminal block in the UI
                appendChatMessage('user', outLog, true);
                aiChatHistory.push({ role: 'user', content: systemPromptText });"""
content = content.replace(old_exec, new_exec)

# Remove fetchAndAttachLog definition
fetch_log_func = r"""        async function fetchAndAttachLog\(\) \{[\s\S]*?alert\("Không thể đọc được file log từ hệ thống!"\);\s*\}\s*\}"""
import re
content = re.sub(fetch_log_func, "", content)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated AI UI!")
