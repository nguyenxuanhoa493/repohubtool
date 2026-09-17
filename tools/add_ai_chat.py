import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Nav Button
nav_pattern = r'<button id="nav-btn-files" class="nav-tab" onclick="switchMainTab\(\'files\'\)">\s*<span>📁</span> Quản lý file\s*</button>'
nav_replacement = """<button id="nav-btn-files" class="nav-tab" onclick="switchMainTab('files')">
                    <span>📁</span> Quản lý file
                </button>
                <button id="nav-btn-chat" class="nav-tab" onclick="switchMainTab('chat')">
                    <span>🤖</span> AI Chatbot
                </button>"""
content = re.sub(nav_pattern, nav_replacement, content)

# 2. Add Tab HTML
tab_html = """    <!-- ================================================================= -->
    <!-- TAB 6: AI CHATBOT -->
    <!-- ================================================================= -->
    <div id="tab-view-chat" class="tab-view">
        <div style="flex:1; display:flex; flex-direction:column; background:#070a13; height:100%; max-width: 900px; margin: 0 auto; width: 100%; border-left: 1px solid var(--border); border-right: 1px solid var(--border); box-shadow: 0 0 30px rgba(0,0,0,0.5);">
            <div style="padding:20px; border-bottom:1px solid var(--border); background:#0f172a; display:flex; align-items:center; gap:16px;">
                <div style="font-size:32px;">🤖</div>
                <div>
                    <h2 style="font-size:18px; font-weight:800; color:#fff; margin:0 0 4px 0;">Trợ lý ảo AI Chatbot</h2>
                    <div style="font-size:13px; color:#10b981; font-weight:600;">● Đang trực tuyến</div>
                </div>
                <button class="btn btn-sm btn-secondary" style="margin-left:auto; font-size:13px; padding:8px 16px;" onclick="clearAIChat()">🗑️ Xóa hội thoại</button>
            </div>
            
            <div id="chat-messages" style="flex:1; overflow-y:auto; padding:24px; display:flex; flex-direction:column; gap:20px; scroll-behavior: smooth;">
                <div style="display:flex; justify-content:flex-start;">
                    <div style="background:#1e293b; color:#f8fafc; padding:14px 18px; border-radius:16px; border-bottom-left-radius:4px; max-width:85%; font-size:15px; line-height:1.6; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                        Xin chào! Tôi là trợ lý ảo AI được tích hợp trực tiếp vào RetroHub. Tôi có thể giúp gì cho bạn?
                    </div>
                </div>
            </div>
            
            <div style="padding:20px; border-top:1px solid var(--border); background:#0f172a;">
                <form id="chat-form" onsubmit="sendChatMessage(event)" style="display:flex; gap:12px;">
                    <input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:14px 24px; color:#fff; font-size:15px; outline:none; transition:border 0.2s;" onfocus="this.style.borderColor='#0284c7'" onblur="this.style.borderColor='#334155'" required>
                    <button type="submit" id="chat-submit-btn" class="btn btn-primary" style="border-radius:30px; padding:0 32px; font-size:15px; font-weight:700;">Gửi ✈️</button>
                </form>
            </div>
        </div>
    </div>
"""
tab_pattern = r'<!-- ================================================================= -->\s*<!-- MODALS -->'
content = re.sub(tab_pattern, tab_html + "\n    <!-- ================================================================= -->\n    <!-- MODALS -->", content)

# 3. Add JS
js_code = """
        // ==================== AI CHATBOT ====================
        let aiChatHistory = [
            { role: "system", content: "You are a helpful AI assistant integrated into a RetroHub gaming device web manager. Answer in Vietnamese. Be concise and friendly." }
        ];

        function appendChatMessage(role, text) {
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
            
            bubble.textContent = text;
            wrapper.appendChild(bubble);
            container.appendChild(wrapper);
            
            // Auto scroll to bottom smoothly
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 50);
        }

        function clearAIChat() {
            if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện?')) return;
            
            aiChatHistory = [{ role: "system", content: "You are a helpful AI assistant integrated into a RetroHub gaming device web manager. Answer in Vietnamese. Be concise and friendly." }];
            const container = document.getElementById('chat-messages');
            if (container) {
                container.innerHTML = `
                    <div style="display:flex; justify-content:flex-start;">
                        <div style="background:#1e293b; color:#f8fafc; padding:14px 18px; border-radius:16px; border-bottom-left-radius:4px; max-width:85%; font-size:15px; line-height:1.6; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                            Đã dọn dẹp lịch sử trò chuyện. Tôi có thể giúp gì cho bạn tiếp theo?
                        </div>
                    </div>
                `;
            }
        }

        async function sendChatMessage(e) {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;
            
            const btn = document.getElementById('chat-submit-btn');
            input.value = '';
            input.disabled = true;
            btn.disabled = true;
            btn.innerHTML = 'Đang nghĩ... <span style="font-size:12px;">⏳</span>';
            
            appendChatMessage('user', text);
            aiChatHistory.push({ role: 'user', content: text });
            
            try {
                const res = await fetch('https://ai.xuanhoa493.com/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer freellmapi-706315155bc56c3a9c765142ab7a08e20d35e2ce26dad3e2'
                    },
                    body: JSON.stringify({
                        model: 'gpt-3.5-turbo',
                        messages: aiChatHistory
                    })
                });
                
                if (!res.ok) {
                    throw new Error('Mã lỗi API: ' + res.status);
                }
                
                const data = await res.json();
                if (data.choices && data.choices.length > 0) {
                    const reply = data.choices[0].message.content;
                    appendChatMessage('assistant', reply);
                    aiChatHistory.push({ role: 'assistant', content: reply });
                } else {
                    appendChatMessage('assistant', 'Lỗi: Phản hồi từ AI bị rỗng.');
                }
            } catch (err) {
                appendChatMessage('assistant', '⚠️ Không thể kết nối tới máy chủ AI. Chi tiết lỗi: ' + err.message);
                // Remove the user message from history so they can try again if they want, or just let it be
            } finally {
                input.disabled = false;
                btn.disabled = false;
                btn.textContent = 'Gửi ✈️';
                input.focus();
            }
        }

        // Khởi động trang web"""
js_pattern = r'// Khởi động trang web'
content = content.replace(js_pattern, js_code)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Added AI Chat tab successfully!")
