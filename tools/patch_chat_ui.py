import re

with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update body CSS to prevent whole-page scrolling and pin the layout
old_body_css = r"body \{ background: var\(--bg-main\); color: var\(--text-main\); display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden; \}"
new_body_css = r"body { background: var(--bg-main); color: var(--text-main); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }"
content = re.sub(old_body_css, new_body_css, content)

# 2. Update chat-messages container gap and padding
old_chat_msg_container = r'<div id="chat-messages" style="flex:1; overflow-y:auto; padding:24px; display:flex; flex-direction:column; gap:20px; scroll-behavior: smooth;">'
new_chat_msg_container = r'<div id="chat-messages" style="flex:1; overflow-y:auto; padding:16px 20px; display:flex; flex-direction:column; gap:12px; scroll-behavior: smooth;">'
content = content.replace(old_chat_msg_container, new_chat_msg_container)

# 3. Update hardcoded chat bubble (the initial greeting)
old_greeting_bubble = r'<div style="background:#1e293b; color:#f8fafc; padding:14px 18px; border-radius:16px; border-bottom-left-radius:4px; max-width:85%; font-size:15px; line-height:1.6; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">'
new_greeting_bubble = r'<div style="background:#1e293b; color:#f8fafc; padding:10px 14px; border-radius:12px; border-bottom-left-radius:4px; max-width:85%; font-size:14.5px; line-height:1.45; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">'
content = content.replace(old_greeting_bubble, new_greeting_bubble)

# 4. Update appendChatMessage JS styles
old_js_bubble_padding = r"bubble.style.padding = '14px 18px';"
new_js_bubble_padding = r"bubble.style.padding = '10px 14px';"
content = content.replace(old_js_bubble_padding, new_js_bubble_padding)

old_js_bubble_radius = r"bubble.style.borderRadius = '16px';"
new_js_bubble_radius = r"bubble.style.borderRadius = '12px';"
content = content.replace(old_js_bubble_radius, new_js_bubble_radius)

old_js_bubble_lh = r"bubble.style.lineHeight = '1.6';"
new_js_bubble_lh = r"bubble.style.lineHeight = '1.45';"
content = content.replace(old_js_bubble_lh, new_js_bubble_lh)

old_js_bubble_fs = r"bubble.style.fontSize = '15px';"
new_js_bubble_fs = r"bubble.style.fontSize = '14.5px';"
content = content.replace(old_js_bubble_fs, new_js_bubble_fs)

# Also update the chat input padding to make it a bit more compact
old_chat_input = r'<input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:14px 24px; color:#fff; font-size:15px; outline:none; transition:border 0.2s;"'
new_chat_input = r'<input type="text" id="chat-input" placeholder="Hỏi AI bất cứ điều gì..." autocomplete="off" style="flex:1; background:#070a13; border:1px solid #334155; border-radius:30px; padding:12px 20px; color:#fff; font-size:14.5px; outline:none; transition:border 0.2s;"'
content = content.replace(old_chat_input, new_chat_input)

# And reduce the top/bottom padding of the input container
old_chat_footer = r'<div style="padding:20px; border-top:1px solid var(--border); background:#0f172a;">'
new_chat_footer = r'<div style="padding:16px 20px; border-top:1px solid var(--border); background:#0f172a;">'
content = content.replace(old_chat_footer, new_chat_footer)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched Chat UI for better layout!")
