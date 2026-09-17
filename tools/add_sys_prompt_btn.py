import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_header = """                <button class="btn btn-sm btn-secondary" style="margin-left:auto; font-size:13px; padding:8px 16px;" onclick="clearAIChat()">🗑️ Xóa hội thoại</button>"""
new_header = """                <button class="btn btn-sm btn-secondary" style="margin-left:auto; font-size:13px; padding:8px 12px;" onclick="showSystemPrompt()" title="Xem khung nền kiến thức của AI">ℹ️ Xem Prompt</button>
                <button class="btn btn-sm btn-danger" style="margin-left:8px; font-size:13px; padding:8px 12px;" onclick="clearAIChat()">🗑️ Xóa log</button>"""
content = content.replace(old_header, new_header)

old_js = """        function clearAIChat() {"""
new_js = """        function showSystemPrompt() {
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**\n\n\`\`\`\n${SYSTEM_PROMPT}\n\`\`\``);
        }

        function clearAIChat() {"""
content = content.replace(old_js, new_js)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("System Prompt button added!")
