with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

start_idx = content.find("function showSystemPrompt()")
if start_idx != -1:
    end_idx = content.find("}", start_idx) + 1
    
    new_func = """function showSystemPrompt() {
            const sysPrompt = aiChatHistory.length > 0 ? aiChatHistory[0].content : "Không tìm thấy System Prompt.";
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**\\n\\n\\`\\`\\`text\\n${sysPrompt}\\n\\`\\`\\``);
        }"""
    
    content = content[:start_idx] + new_func + content[end_idx:]
    with open("files/gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Exact replacement successful!")
else:
    print("Function not found!")
