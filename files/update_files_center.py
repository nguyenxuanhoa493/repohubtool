with open("gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_div = '<div style="display:flex; justify-content:center; align-items:center; height:100%; padding:20px;">'
new_div = '<div style="display:flex; justify-content:center; align-items:center; height:100%; width:100%; padding:20px; flex:1;">'

content = content.replace(old_div, new_div)

with open("gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated flex wrapper to center UI!")
