import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# The JS file has an actual newline in the regex. We need to find it and replace it with `\\n`
# Let's just find the exact block and replace it.

old_block = "            safeText = safeText.replace(/`([^`\n]+)`/g"
new_block = "            safeText = safeText.replace(/`([^`\\\\n]+)`/g"
content = content.replace(old_block, new_block)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed inline code regex!")
