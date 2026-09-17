import re

with open("gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_func = """        async function toggleScreenStream() {
            const btn = document.getElementById('btn-stream-toggle');
            if (btn) btn.disabled = true;
            try {
                const endpoint = isStreamRunning ? '/api/stream/stop' : '/api/stream/start';
                const res = await fetch(endpoint, { method: 'POST' });
                const data = await res.json();
                isStreamRunning = !!data.running;
                updateStreamUI();
                showToast(isStreamRunning ? 'Đã khởi động Stream màn hình (Cổng 8088)' : 'Đã tắt Stream màn hình');
            } catch (e) {
                alert('Lỗi thao tác dịch vụ stream: ' + e);
            } finally {
                if (btn) btn.disabled = false;
            }
        }"""

new_func = """        async function toggleScreenStream() {
            const btn = document.getElementById('btn-stream-toggle');
            if (btn) btn.disabled = true;
            try {
                const wasRunning = isStreamRunning;
                const endpoint = isStreamRunning ? '/api/stream/stop' : '/api/stream/start';
                const res = await fetch(endpoint, { method: 'POST' });
                const data = await res.json();
                isStreamRunning = !!data.running;
                updateStreamUI();
                showToast(isStreamRunning ? 'Đã khởi động Stream màn hình (Cổng 8088)' : 'Đã tắt Stream màn hình');
                
                if (!wasRunning && isStreamRunning) {
                    setTimeout(() => {
                        openStreamNewTab();
                    }, 800);
                }
            } catch (e) {
                alert('Lỗi thao tác dịch vụ stream: ' + e);
            } finally {
                if (btn) btn.disabled = false;
            }
        }"""

if old_func in content:
    content = content.replace(old_func, new_func)
    with open("gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated toggleScreenStream successfully!")
else:
    print("Function not found, using regex...")
    # fallback if exact match fails
    pattern = r'async function toggleScreenStream\(\) \{.*?if \(btn\) btn\.disabled = false;\s*\}\s*\}'
    content = re.sub(pattern, new_func, content, flags=re.DOTALL)
    with open("gameweb.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated using regex.")

