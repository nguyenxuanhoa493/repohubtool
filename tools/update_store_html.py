with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

old_html = """                <div id="store-games-container" class="games-grid"></div>
                <div id="store-loading" style="display:none; text-align:center; padding: 40px; color: var(--primary);">
                    <div style="font-size: 14px; font-weight: 700;">Đang nạp kho game trực tuyến...</div>
                </div>
                <div id="store-empty-state" style="display:none; text-align:center; padding: 60px 20px; color: var(--text-sub);">
                    <div style="font-size: 16px; margin-bottom: 12px; font-weight: 600;">Không tìm thấy game</div>
                    <p>Hãy thử từ khóa khác hoặc chuyển sang hệ máy khác trong danh sách.</p>
                </div>"""

new_html = """                <div id="store-games-container" class="games-grid"></div>
                <div id="store-loading" style="display:none; text-align:center; padding: 40px; color: var(--primary);">
                    <div style="font-size: 14px; font-weight: 700;">Đang nạp kho game trực tuyến...</div>
                </div>
                <div id="store-loading-more" style="display:none; text-align:center; padding: 24px; color: #38bdf8; font-weight: 600; font-size: 13px;">
                    Đang tải thêm game... ⏳
                </div>
                <div id="store-load-more-btn-container" style="display:none; text-align:center; padding: 24px 0;">
                    <button class="btn btn-secondary" onclick="loadMoreStoreGames()" style="padding: 10px 28px; font-size: 13px; font-weight: 600; border-radius: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">⬇️ Tải thêm game tiếp theo...</button>
                </div>
                <div id="store-empty-state" style="display:none; text-align:center; padding: 60px 20px; color: var(--text-sub);">
                    <div style="font-size: 16px; margin-bottom: 12px; font-weight: 600;">Không tìm thấy game</div>
                    <p>Hãy thử từ khóa khác hoặc chuyển sang hệ máy khác trong danh sách.</p>
                </div>"""

content = content.replace(old_html, new_html)

# Also add onscroll to main in store tab
content = content.replace('<main>\n                <div class="toolbar">\n                    <div class="search-box">\n                        <span class="search-icon"></span>\n                        <input type="text" id="store-search-input"', '<main id="store-main-scroll" onscroll="handleStoreScroll(event)">\n                <div class="toolbar">\n                    <div class="search-box">\n                        <span class="search-icon"></span>\n                        <input type="text" id="store-search-input"')

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated store HTML successfully!")
