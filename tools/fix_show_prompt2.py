import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"        function showSystemPrompt\(\) \{[\s\S]*?\$\\{SYSTEM_PROMPT\\}[\s\S]*?\}"

new_func = """        function showSystemPrompt() {
            const sysPrompt = aiChatHistory.length > 0 ? aiChatHistory[0].content : "Không tìm thấy System Prompt.";
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**\\n\\n\\`\\`\\`\\n${sysPrompt}\\n\\`\\`\\``);
        }"""

content = re.sub(pattern, new_func, content)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Replaced showSystemPrompt successfully!")
