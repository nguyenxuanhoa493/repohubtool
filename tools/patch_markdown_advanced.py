import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the formatting section of appendChatMessage
old_append = r"""            // Escape HTML
            let safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            // Format \[CMD\] blocks"""

new_append = r"""            // Escape HTML
            let safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            
            // Format basic markdown
            safeText = safeText.replace(/\$\\rightarrow\$/g, '→').replace(/\$\\leftarrow\$/g, '←');
            safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            safeText = safeText.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            // Format code blocks (```)
            safeText = safeText.replace(/```(?:[a-z0-9]+)?\n?([\s\S]*?)```/gi, (match, code) => {
                return `<div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px; margin: 6px 0; font-family: monospace; font-size: 12px; white-space: pre-wrap; overflow-x: auto; max-height: 200px; overflow-y: auto;">${code.trim()}</div>`;
            });
            
            // Format inline code (`)
            safeText = safeText.replace(/`([^`]+)`/g, `<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 4px; font-size: 0.9em; color: #38bdf8;">$1</code>`);
            
            // Format [CMD] blocks"""

content = re.sub(old_append, new_append, content)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Advanced Markdown applied!")
