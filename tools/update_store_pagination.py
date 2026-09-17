with open("files/gameweb.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update backend /api/store/games to pass offset to search_games_fts
old_backend = """        if query_str:
          games = db.search_games_fts(
              query_str,
              sys_code=sys_code,
              limit=limit,
              source_type=source_type,
          )"""

new_backend = """        if query_str:
          games = db.search_games_fts(
              query_str,
              sys_code=sys_code,
              limit=limit,
              source_type=source_type,
              offset=offset,
          )"""

if old_backend in content:
    content = content.replace(old_backend, new_backend)
    print("Updated backend /api/store/games with offset!")

# 2. Update HTML of Store Tab to include onscroll and load more indicators
old_html = """            <main>
                <div class="toolbar">
                    <div class="search-box">
                        <span class="search-icon"></span>
                        <input type="text" id="store-search-input" placeholder="Tìm kiếm trong 40,000+ game..." onkeydown="if(event.key==='Enter') executeStoreSearch()">
                    </div>
                    <select id="store-sort-select" onchange="executeStoreSearch()" style="background:#0f172a; border:1px solid var(--border); color:#fff; border-radius:8px; padding:8px 12px; font-size:12px; outline:none;">
                        <option value="downloads">Lượt tải nhiều nhất</option>
                        <option value="rating">Đánh giá cao nhất</option>
                        <option value="title">Tên A-Z</option>
                    </select>
                    <button class="btn btn-green" onclick="executeStoreSearch()">Tìm kiếm</button>
                </div>

                <div id="store-download-banner" style="display:none; background: #0f172a; border: 1px solid #0284c7; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700; margin-bottom:6px;">
                        <span id="store-dl-title" style="color:#38bdf8;">Đang tải game về máy...</span>
                        <span id="store-dl-pct" style="color:#10b981;">0%</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 8px; margin-bottom:6px;">
                        <div id="store-dl-bar" class="progress-bar-fill" style="width:0%;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-sub);">
                        <span id="store-dl-speed">Tốc độ: 0 KB/s</span>
                        <span id="store-dl-status">Đang kết nối server...</span>
                    </div>
                </div>

                <div id="store-games-container" class="games-grid"></div>
                <div id="store-loading" style="display:none; text-align:center; padding: 40px; color: var(--primary);">
                    <div style="font-size: 14px; font-weight: 700;">Đang nạp kho game trực tuyến...</div>
                </div>
                <div id="store-empty-state" style="display:none; text-align:center; padding: 60px 20px; color: var(--text-sub);">
                    <div style="font-size: 16px; margin-bottom: 12px; font-weight: 600;">(Không tìm thấy game nào)</div>
                    <p>Thử tìm kiếm với từ khóa khác hoặc chuyển sang hệ máy khác.</p>
                </div>
            </main>"""

new_html = """            <main id="store-main-scroll" onscroll="handleStoreScroll(event)">
                <div class="toolbar">
                    <div class="search-box">
                        <span class="search-icon"></span>
                        <input type="text" id="store-search-input" placeholder="Tìm kiếm trong 40,000+ game..." onkeydown="if(event.key==='Enter') executeStoreSearch()">
                    </div>
                    <select id="store-sort-select" onchange="executeStoreSearch()" style="background:#0f172a; border:1px solid var(--border); color:#fff; border-radius:8px; padding:8px 12px; font-size:12px; outline:none;">
                        <option value="downloads">Lượt tải nhiều nhất</option>
                        <option value="rating">Đánh giá cao nhất</option>
                        <option value="title">Tên A-Z</option>
                    </select>
                    <button class="btn btn-green" onclick="executeStoreSearch()">Tìm kiếm</button>
                </div>

                <div id="store-download-banner" style="display:none; background: #0f172a; border: 1px solid #0284c7; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px;">
                    <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700; margin-bottom:6px;">
                        <span id="store-dl-title" style="color:#38bdf8;">Đang tải game về máy...</span>
                        <span id="store-dl-pct" style="color:#10b981;">0%</span>
                    </div>
                    <div class="progress-bar-bg" style="height: 8px; margin-bottom:6px;">
                        <div id="store-dl-bar" class="progress-bar-fill" style="width:0%;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-sub);">
                        <span id="store-dl-speed">Tốc độ: 0 KB/s</span>
                        <span id="store-dl-status">Đang kết nối server...</span>
                    </div>
                </div>

                <div id="store-games-container" class="games-grid"></div>
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
                    <div style="font-size: 16px; margin-bottom: 12px; font-weight: 600;">(Không tìm thấy game nào)</div>
                    <p>Thử tìm kiếm với từ khóa khác hoặc chuyển sang hệ máy khác.</p>
                </div>
            </main>"""

if old_html in content:
    content = content.replace(old_html, new_html)
    print("Updated Store HTML markup with scroll & pagination containers!")

# 3. Update Store JS functions
old_js = """        function selectStoreCategory(catId) {
            currentStoreCategory = catId;
            currentStoreSystem = 'ALL';
            document.getElementById('store-search-input').value = '';
            renderStoreSidebar();
            loadStoreGames();
        }

        function selectStoreSystem(sysCode) {
            currentStoreSystem = sysCode;
            currentStoreCategory = 'ALL';
            document.getElementById('store-search-input').value = '';
            renderStoreSidebar();
            loadStoreGames();
        }

        async function loadStoreGames() {
            const container = document.getElementById('store-games-container');
            const loading = document.getElementById('store-loading');
            const emptyEl = document.getElementById('store-empty-state');

            container.innerHTML = '';
            loading.style.display = 'block';
            emptyEl.style.display = 'none';

            const sort = document.getElementById('store-sort-select').value;
            const q = document.getElementById('store-search-input').value.trim();

            let url = `/api/store/games?source_type=${currentStoreCategory}&system=${currentStoreSystem}&sort=${sort}&limit=60`;
            if (q) url += `&query=${encodeURIComponent(q)}`;

            try {
                const res = await fetch(url);
                const data = await res.json();
                loading.style.display = 'none';
                if (data.ok && data.games && data.games.length > 0) {
                    storeGames = data.games;
                    renderStoreGrid(storeGames);
                } else {
                    emptyEl.style.display = 'block';
                }
            } catch (e) {
                loading.style.display = 'none';
                emptyEl.style.display = 'block';
            }
        }

        function executeStoreSearch() {
            loadStoreGames();
        }

        function renderStoreGrid(games) {
            const container = document.getElementById('store-games-container');
            let html = '';
            games.forEach((g, idx) => {
                const imgUrl = g.img_url ? `<img src="${g.img_url}" loading="lazy" alt="${g.title}">` : `<div style="font-size:32px;">🕹️</div>`;
                const isViet = g.is_viet ? `<span class="badge-tag badge-viet">VIỆT HÓA</span>` : '';
                const isHack = g.is_hack ? `<span class="badge-tag badge-hack">HACK</span>` : '';
                const isHit = g.is_hit ? `<span class="badge-tag badge-top">TOP</span>` : '';

                const actionBtn = g.is_installed 
                    ? `<span class="badge-tag badge-installed">✓ Đã có trên thẻ</span>`
                    : `<button class="btn btn-sm btn-green" id="btn-store-dl-${g.id}" onclick="downloadStoreGame(${g.id}, '${g.sys_code}', '${encodeURIComponent(g.title)}', '${encodeURIComponent(g.rom_url || '')}', '${encodeURIComponent(g.filename || '')}', '${encodeURIComponent(g.img_url || '')}')">⬇️ Tải về máy</button>`;

                html += `<div class="game-card">
                    <div class="art-box">${imgUrl}</div>
                    <div class="game-info">
                        <div style="display:flex; gap:4px; margin-bottom:4px; flex-wrap:wrap;">${isViet}${isHack}${isHit}</div>
                        <div class="game-title" title="${g.title}">${g.title}</div>
                        <div class="game-meta">
                            <span>${g.sys_code}</span>
                            <span>${g.file_size_str || ''}</span>
                        </div>
                        <div class="game-actions" style="margin-top:10px;">
                            ${actionBtn}
                        </div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }"""

new_js = """        let currentStorePage = 1;
        let storeHasMore = true;
        let isStoreLoading = false;

        function selectStoreCategory(catId) {
            currentStoreCategory = catId;
            currentStoreSystem = 'ALL';
            document.getElementById('store-search-input').value = '';
            renderStoreSidebar();
            resetAndLoadStore();
        }

        function selectStoreSystem(sysCode) {
            currentStoreSystem = sysCode;
            currentStoreCategory = 'ALL';
            document.getElementById('store-search-input').value = '';
            renderStoreSidebar();
            resetAndLoadStore();
        }

        function executeStoreSearch() {
            resetAndLoadStore();
        }

        function resetAndLoadStore() {
            currentStorePage = 1;
            storeHasMore = true;
            storeGames = [];
            loadStoreGames(false);
        }

        function loadMoreStoreGames() {
            if (!isStoreLoading && storeHasMore) {
                currentStorePage++;
                loadStoreGames(true);
            }
        }

        function handleStoreScroll(e) {
            const el = e.target;
            if (el.scrollHeight - el.scrollTop - el.clientHeight < 350) {
                if (!isStoreLoading && storeHasMore) {
                    currentStorePage++;
                    loadStoreGames(true);
                }
            }
        }

        async function loadStoreGames(isAppend = false) {
            if (isStoreLoading) return;
            isStoreLoading = true;

            const container = document.getElementById('store-games-container');
            const loading = document.getElementById('store-loading');
            const loadingMore = document.getElementById('store-loading-more');
            const emptyEl = document.getElementById('store-empty-state');
            const loadMoreBtn = document.getElementById('store-load-more-btn-container');

            if (!isAppend) {
                container.innerHTML = '';
                loading.style.display = 'block';
                emptyEl.style.display = 'none';
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            } else {
                if (loadingMore) loadingMore.style.display = 'block';
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            }

            const sort = document.getElementById('store-sort-select').value;
            const q = document.getElementById('store-search-input').value.trim();
            const limit = 40;

            let url = `/api/store/games?source_type=${currentStoreCategory}&system=${currentStoreSystem}&sort=${sort}&page=${currentStorePage}&limit=${limit}`;
            if (q) url += `&query=${encodeURIComponent(q)}`;

            try {
                const res = await fetch(url);
                const data = await res.json();
                loading.style.display = 'none';
                if (loadingMore) loadingMore.style.display = 'none';

                if (data.ok && data.games && data.games.length > 0) {
                    if (isAppend) {
                        storeGames = storeGames.concat(data.games);
                        renderStoreGrid(data.games, true);
                    } else {
                        storeGames = data.games;
                        renderStoreGrid(storeGames, false);
                    }

                    if (data.games.length < limit) {
                        storeHasMore = false;
                        if (loadMoreBtn) loadMoreBtn.style.display = 'none';
                    } else {
                        storeHasMore = true;
                        if (loadMoreBtn) loadMoreBtn.style.display = 'block';
                    }
                } else {
                    storeHasMore = false;
                    if (!isAppend) {
                        emptyEl.style.display = 'block';
                    }
                    if (loadMoreBtn) loadMoreBtn.style.display = 'none';
                }
            } catch (e) {
                loading.style.display = 'none';
                if (loadingMore) loadingMore.style.display = 'none';
                if (!isAppend) emptyEl.style.display = 'block';
                if (loadMoreBtn) loadMoreBtn.style.display = 'none';
            } finally {
                isStoreLoading = false;
            }
        }

        function renderStoreGrid(games, isAppend = false) {
            const container = document.getElementById('store-games-container');
            let html = '';
            games.forEach((g, idx) => {
                const imgUrl = g.img_url ? `<img src="${g.img_url}" loading="lazy" alt="${g.title}">` : `<div style="font-size:32px;">🕹️</div>`;
                const isViet = g.is_viet ? `<span class="badge-tag badge-viet">VIỆT HÓA</span>` : '';
                const isHack = g.is_hack ? `<span class="badge-tag badge-hack">HACK</span>` : '';
                const isHit = g.is_hit ? `<span class="badge-tag badge-top">TOP</span>` : '';

                const actionBtn = g.is_installed 
                    ? `<span class="badge-tag badge-installed">✓ Đã có trên thẻ</span>`
                    : `<button class="btn btn-sm btn-green" id="btn-store-dl-${g.id}" onclick="downloadStoreGame(${g.id}, '${g.sys_code}', '${encodeURIComponent(g.title)}', '${encodeURIComponent(g.rom_url || '')}', '${encodeURIComponent(g.filename || '')}', '${encodeURIComponent(g.img_url || '')}')">⬇️ Tải về máy</button>`;

                html += `<div class="game-card">
                    <div class="art-box">${imgUrl}</div>
                    <div class="game-info">
                        <div style="display:flex; gap:4px; margin-bottom:4px; flex-wrap:wrap;">${isViet}${isHack}${isHit}</div>
                        <div class="game-title" title="${g.title}">${g.title}</div>
                        <div class="game-meta">
                            <span>${g.sys_code}</span>
                            <span>${g.file_size_str || ''}</span>
                        </div>
                        <div class="game-actions" style="margin-top:10px;">
                            ${actionBtn}
                        </div>
                    </div>
                </div>`;
            });
            if (isAppend) {
                container.insertAdjacentHTML('beforeend', html);
            } else {
                container.innerHTML = html;
            }
        }"""

if old_js in content:
    content = content.replace(old_js, new_js)
    print("Updated Store JS functions with infinite scroll and pagination!")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Finished store pagination update!")
