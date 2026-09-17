import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix \r in rightarrow/leftarrow
content = content.replace("replace(/\$\r", r"replace(/\$\\r")
content = content.replace("ightarrow\$/g", r"ightarrow\$/g")
content = content.replace("replace(/\$\x0c", r"replace(/\$\\f") # just in case \f was used somewhere?
content = content.replace(r"replace(/\$", r"replace(/\$\\v")

# Let's just manually replace the entire Format basic markdown section to be 100% safe
old_section_pattern = r"            // Format basic markdown.*?            // Format \[CMD\] blocks"
new_section = r"""            // Format basic markdown
            safeText = safeText.replace(/\$\\rightarrow\$/g, '→').replace(/\$\\leftarrow\$/g, '←');
            safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            safeText = safeText.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            // Format code blocks (```)
            safeText = safeText.replace(/```(?:[a-zA-Z0-9]+)?\n?([\s\S]*?)```/gi, (match, code) => {
                return `<div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px; margin: 6px 0; font-family: monospace; font-size: 12.5px; line-height: 1.4; white-space: pre-wrap; overflow-x: auto; max-height: 180px; overflow-y: auto;">${code.trim()}</div>`;
            });
            
            // Format inline code (`)
            safeText = safeText.replace(/`([^`\n]+)`/g, `<code style="background: rgba(0,0,0,0.2); padding: 2px 4px; border-radius: 4px; font-size: 13px; color: #38bdf8;">$1</code>`);
            
            // Format [CMD] blocks"""

content = re.sub(old_section_pattern, lambda m: new_section, content, flags=re.DOTALL)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Replaced whole markdown section cleanly!")
