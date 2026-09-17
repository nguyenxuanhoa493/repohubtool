with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix JS Error Handling
old_js_err = """                const data = await res.json();
                if (data.error) {
                    throw new Error(data.error);
                }"""
new_js_err = """                const data = await res.json();
                if (data.error) {
                    const errMsg = typeof data.error === 'object' ? (data.error.message || JSON.stringify(data.error)) : data.error;
                    throw new Error(errMsg);
                }"""
content = content.replace(old_js_err, new_js_err)

# Fix JS Model
old_js_model = """                    body: JSON.stringify({
                        model: 'gpt-3.5-turbo',
                        messages: aiChatHistory
                    })"""
new_js_model = """                    body: JSON.stringify({
                        model: 'auto',
                        messages: aiChatHistory
                    })"""
content = content.replace(old_js_model, new_js_model)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed JS!")
