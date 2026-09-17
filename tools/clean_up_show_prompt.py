import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's replace the whole messy block
# We will find `function showSystemPrompt() {` and replace everything until `function clearAIChat() {`
pattern = r"function showSystemPrompt\(\) \{[\s\S]*?function clearAIChat\(\) \{"

new_func = """function showSystemPrompt() {
            const sysPrompt = aiChatHistory.length > 0 ? aiChatHistory[0].content : "Không tìm thấy System Prompt.";
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**\\n\\n\\`\\`\\`text\\n${sysPrompt}\\n\\`\\`\\``);
        }

        function clearAIChat() {"""

content = re.sub(pattern, new_func, content)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Cleaned up successfully!")
