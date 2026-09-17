with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Specifically target the exact lines that cause the bug
content = content.replace("btn.textContent = 'Đang chạy lệnh... ⏳';", "btn.innerHTML = '⏳';")
content = content.replace("btn.textContent = '✅ Đã chạy';", "btn.innerHTML = '✅';")
content = content.replace("btn.className = 'btn btn-sm btn-green';", "")
content = content.replace("btn.style.width = '100%';", "")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Brute force replaced.")
