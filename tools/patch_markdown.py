import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update System Prompt to ban LaTeX
old_prompt = r"Bạn phải LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT, ngắn gọn, đúng trọng tâm."
new_prompt = r"Bạn phải LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT, ngắn gọn, đúng trọng tâm. KHÔNG dùng cú pháp LaTeX (như $\rightarrow$), hãy dùng ký tự Unicode bình thường (->, →)."
content = content.replace(old_prompt, new_prompt)

# 2. Add basic markdown parser to appendChatMessage
old_append = r"""                // Format [CMD] blocks
                let cmdCount = 0;"""

new_append = r"""                // Pre-process LaTeX and Markdown
                safeText = safeText.replace(/\$\\rightarrow\$/g, '→').replace(/\$\\leftarrow\$/g, '←').replace(/\$\\Rightarrow\$/g, '⇒');
                safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                safeText = safeText.replace(/\*(.*?)\*/g, '<em>$1</em>');
                
                // Format [CMD] blocks
                let cmdCount = 0;"""
content = content.replace(old_append, new_append)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched Markdown!")
