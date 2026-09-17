with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add button to HTML
old_form = """<form id="chat-form" onsubmit="sendChatMessage(event)" style="display:flex; gap:12px;">
                    <input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:14px 24px; color:#fff; font-size:15px; outline:none; transition:border 0.2s;" onfocus="this.style.borderColor='#0284c7'" onblur="this.style.borderColor='#334155'" required>
                    <button type="submit" id="chat-submit-btn" class="btn btn-primary" style="border-radius:30px; padding:0 32px; font-size:15px; font-weight:700;">Gửi ✈️</button>
                </form>"""
new_form = """<form id="chat-form" onsubmit="sendChatMessage(event)" style="display:flex; gap:12px;">
                    <button type="button" class="btn btn-secondary" style="border-radius:30px; padding:0 20px; font-size:14px;" onclick="fetchAndAttachLog()" title="Đính kèm Log hệ thống để nhờ AI phân tích lỗi">📄 Đính kèm Log</button>
                    <input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:14px 24px; color:#fff; font-size:15px; outline:none; transition:border 0.2s;" onfocus="this.style.borderColor='#0284c7'" onblur="this.style.borderColor='#334155'" required>
                    <button type="submit" id="chat-submit-btn" class="btn btn-primary" style="border-radius:30px; padding:0 32px; font-size:15px; font-weight:700;">Gửi ✈️</button>
                </form>"""
content = content.replace(old_form, new_form)

# Add JS function
js_func = """
        async function fetchAndAttachLog() {
            try {
                const res = await fetch('/api/logs/download');
                if (!res.ok) throw new Error('Network error');
                const text = await res.text();
                if (!text || text.trim() === '') {
                    alert('Log hệ thống hiện đang trống (chưa có lỗi nào được ghi lại)!');
                    return;
                }
                const input = document.getElementById('chat-input');
                // Limit to last 3000 chars to avoid huge context limits
                const tailLog = text.length > 3000 ? text.substring(text.length - 3000) : text;
                const prompt = `Game vừa bị văng. Dưới đây là đoạn cuối của Log hệ thống. Hãy phân tích nguyên nhân và cách khắc phục giúp tôi:\\n\\n\`\`\`\\n${tailLog}\\n\`\`\``;
                input.value = prompt;
                input.focus();
                
                // Optional: auto-submit it!
                // sendChatMessage(new Event('submit', { cancelable: true }));
            } catch (e) {
                alert("Không thể đọc được file log từ hệ thống!");
            }
        }
        
        async function sendChatMessage(e) {"""

content = content.replace("        async function sendChatMessage(e) {", js_func)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
