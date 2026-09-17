import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update appendChatMessage signature
content = content.replace("function appendChatMessage(role, text) {", "function appendChatMessage(role, text, skipEscape = false) {")
content = content.replace('let safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");', 'let safeText = skipEscape ? text : text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");')

# 2. Update Run All button UI
old_run_all_ui = """            if (cmdCount > 1) {
                const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                safeText += `<div style="margin-top:8px;">
                    <button onclick="executeAllAiCommands(event, '${b64Cmds}')" class="btn btn-sm" style="background:#eab308; color:#000; border-radius:4px; padding:4px 12px; font-weight:bold; border:none; display:inline-flex; align-items:center; gap:6px; cursor:pointer;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        Thực thi tất cả (${cmdCount} lệnh)
                    </button>
                </div>`;
            }"""

new_run_all_ui = """            if (cmdCount > 1) {
                const b64Cmds = btoa(encodeURIComponent(JSON.stringify(allCmds)));
                safeText += `<div style="display: inline-flex; align-items: center; background: #0f172a; border: 1px solid #334155; border-radius: 4px; padding: 2px 4px 2px 8px; margin: 4px 0; gap: 6px; max-width: 100%;">
                    <code style="font-family: monospace; color: #eab308; font-size: 13px; font-weight: bold; white-space: pre-wrap; word-break: break-all;">⚡ Thực thi tất cả (${cmdCount} lệnh)</code>
                    <button onclick="executeAllAiCommands(event, '${b64Cmds}')" title="Thực thi tất cả" style="background: transparent; border: none; cursor: pointer; padding: 4px; display: flex; align-items: center; color: #eab308; flex-shrink: 0; border-left: 1px solid #334155; outline: none;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                </div>`;
            }"""
content = content.replace(old_run_all_ui, new_run_all_ui)

# 3. Update executeAiCommand
old_exec_1 = """                const outLog = data.output || '(Không có kết quả trả về)';
                const resultText = `Đã thực thi lệnh trên TrimUI.\\nKết quả:\\n\\`\\`\\`\\n${outLog}\\n\\`\\`\\``;
                
                btn.innerHTML = '✅';
                
                
                
                // Add to chat and send to AI
                appendChatMessage('user', resultText);
                aiChatHistory.push({ role: 'user', content: resultText });"""

new_exec_1 = """                const outLog = data.output || '(Không có kết quả trả về)';
                const safeLog = outLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px;">
                    <summary style="cursor: pointer; font-size: 13px; font-weight: bold; color: #38bdf8; outline: none;">✅ Đã thực thi lệnh (Nhấn để xem kết quả)</summary>
                    <div style="margin-top: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 200px; overflow-y: auto; color: #cbd5e1;">${safeLog}</div>
                </details>`;
                
                const plainText = `Đã thực thi lệnh trên TrimUI.\\nKết quả:\\n\\`\\`\\`\\n${outLog}\\n\\`\\`\\``;
                
                btn.innerHTML = '✅';
                
                // Add to chat and send to AI
                appendChatMessage('user', htmlText, true);
                aiChatHistory.push({ role: 'user', content: plainText });"""
content = content.replace(old_exec_1, new_exec_1)

# 4. Update executeAllAiCommands
old_exec_2 = """                    const data = await res.json();
                    const outLog = data.output || '(Không có kết quả trả về)';
                    combinedOutput += `--- Kết quả lệnh ${i+1}/${cmds.length}: ${cmd} ---\\n${outLog}\\n\\n`;
                } catch(err) {
                    combinedOutput += `--- Lỗi lệnh ${i+1}/${cmds.length}: ${cmd} ---\\n${err.message}\\n\\n`;
                }
            }
            
            btn.textContent = '✅ Đã chạy tất cả';
            
            btn.style.background = '#22c55e';
            btn.style.color = '#fff';
            
            const resultText = `Đã thực thi ${cmds.length} lệnh trên TrimUI.\\nKết quả:\\n\\`\\`\\`\\n${combinedOutput}\\n\\`\\`\\``;
            
            appendChatMessage('user', resultText);
            aiChatHistory.push({ role: 'user', content: resultText });"""

new_exec_2 = """                    const data = await res.json();
                    const outLog = data.output || '(Không có kết quả trả về)';
                    combinedOutput += `--- Kết quả lệnh ${i+1}/${cmds.length}: ${cmd} ---\\n${outLog}\\n\\n`;
                } catch(err) {
                    combinedOutput += `--- Lỗi lệnh ${i+1}/${cmds.length}: ${cmd} ---\\n${err.message}\\n\\n`;
                }
            }
            
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            btn.style.color = '#22c55e';
            
            const safeLog = combinedOutput.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const htmlText = `<details style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px;">
                <summary style="cursor: pointer; font-size: 13px; font-weight: bold; color: #eab308; outline: none;">✅ Đã thực thi ${cmds.length} lệnh (Nhấn để xem kết quả)</summary>
                <div style="margin-top: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 250px; overflow-y: auto; color: #cbd5e1;">${safeLog}</div>
            </details>`;
            const plainText = `Đã thực thi ${cmds.length} lệnh trên TrimUI.\\nKết quả:\\n\\`\\`\\`\\n${combinedOutput}\\n\\`\\`\\``;
            
            appendChatMessage('user', htmlText, true);
            aiChatHistory.push({ role: 'user', content: plainText });"""

content = content.replace(old_exec_2, new_exec_2)

# Also fix the initial text content setting for Run All loading state
old_run_loading = "btn.textContent = `Đang chạy ${cmds.length} lệnh... ⏳`;"
new_run_loading = "btn.innerHTML = '⏳';"
content = content.replace(old_run_loading, new_run_loading)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated Run All UI and Details UI!")
