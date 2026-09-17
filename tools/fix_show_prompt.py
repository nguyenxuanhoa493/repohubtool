import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_func = """        function showSystemPrompt() {
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**\\n\\n\\`\\`\\`\\n${SYSTEM_PROMPT}\\n\\`\\`\\``);
        }"""
new_func = """        function showSystemPrompt() {
            const sysPrompt = aiChatHistory.length > 0 ? aiChatHistory[0].content : "Không tìm thấy System Prompt.";
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**\\n\\n\\`\\`\\`\\n${sysPrompt}\\n\\`\\`\\``);
        }"""
content = content.replace(old_func, new_func)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed showSystemPrompt!")
