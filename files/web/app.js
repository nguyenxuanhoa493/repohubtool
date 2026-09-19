let currentTab = 'games';
        let allSystems = [];
        let currentSystem = null;
        let currentGames = [];
        let selectedGame = null;

        let storeCategories = [];
        let storeSystems = [];
        let currentStoreCategory = 'HITS';
        let currentStoreSystem = 'ALL';
        let storeGames = [];
        let storeDlInterval = null;

        let ytPlaylists = [];
        let currentYtTab = 'trending';
        let ytVideos = [];

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3000);
        }

        function closeModal(id) {
            const el = document.getElementById(id);
            if (el) el.classList.remove('show');
        }
        function openModal(id) {
            const el = document.getElementById(id);
            if (el) el.classList.add('show');
        }

        let allThemes = [];
        let currentThemeFilter = 'all';
        let currentGamesSubTab = 'library';

        function switchGamesSubTab(subTab) {
            currentGamesSubTab = subTab;
            document.querySelectorAll('.games-subnav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.games-subview').forEach(v => v.classList.remove('active'));

            const btn = document.getElementById(`subtab-btn-${subTab}`);
            const view = document.getElementById(`subview-games-${subTab}`);
            if (btn) btn.classList.add('active');
            if (view) view.classList.add('active');

            if (subTab === 'library') {
                if (!allSystems.length) loadSystems();
            } else if (subTab === 'online') {
                if (!storeCategories.length) loadStoreInit();
            } else if (subTab === 'boxart') {
                loadBoxartSystems();
            }
        }

        function switchMainTab(tab) {
            if (tab === 'store') {
                switchMainTab('games');
                switchGamesSubTab('online');
                return;
            }
            if (tab === 'gdrive') {
                switchMainTab('games');
                switchGamesSubTab('online');
                setTimeout(() => { selectStoreCategory('GDRIVE'); }, 200);
                return;
            }

            currentTab = tab;
            // Cập nhật URL hash
            history.replaceState(null, null, '#' + tab);
            document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));

            const btn = document.getElementById(`nav-btn-${tab}`);
            const view = document.getElementById(`tab-view-${tab}`);
            if (btn) btn.classList.add('active');
            if (view) view.classList.add('active');

            if (tab === 'games') {
                if (currentGamesSubTab === 'library') {
                    if (!allSystems.length) loadSystems();
                } else if (currentGamesSubTab === 'online') {
                    if (!storeCategories.length) loadStoreInit();
                } else if (currentGamesSubTab === 'boxart') {
                    loadBoxartSystems();
                }
            } else if (tab === 'themes') {
                if (!allThemes.length) loadThemes();
            } else if (tab === 'emus') {
                if (!allEmus.length) loadEmus();
            } else if (tab === 'youtube') {
                if (!ytPlaylists.length) loadYouTubeInit();
            } else if (tab === 'stream') {
                checkStreamStatus();
            }
        }

        function reloadCurrentView() {
            loadStorageStatus();
            if (currentTab === 'games') {
                if (currentGamesSubTab === 'library') loadSystems(true);
                else if (currentGamesSubTab === 'online') loadStoreGames();
                else if (currentGamesSubTab === 'boxart') selectBoxartSystem(boxartCurrentSys);
            }
            else if (currentTab === 'themes') loadThemes(true);
            else if (currentTab === 'emus') loadEmus(true);
            else if (currentTab === 'youtube') loadYouTubeVideos(currentYtTab);
        }

        // ==================== EMULATOR STORE ====================
        let allEmus = [];
        let currentEmuFilter = 'all';

        async function loadEmus(force = false) {
            const loading = document.getElementById('emu-loading');
            const container = document.getElementById('emu-grid-container');
            const empty = document.getElementById('emu-empty');
            if (loading) loading.style.display = 'block';
            if (empty) empty.style.display = 'none';
            if (container && force) container.innerHTML = '';

            try {
                const res = await fetch('/api/emus');
                const data = await res.json();
                if (data.ok && Array.isArray(data.emus)) {
                    allEmus = data.emus;
                    updateEmuStats(data);
                    renderEmusGrid();
                } else {
                    showToast('Lỗi khi tải danh sách giả lập: ' + (data.error || ''));
                    if (empty) empty.style.display = 'block';
                }
            } catch (e) {
                showToast('Lỗi kết nối máy chủ: ' + e.message);
                if (empty) empty.style.display = 'block';
            } finally {
                if (loading) loading.style.display = 'none';
            }
        }

        function updateEmuStats(data) {
            const totalEl = document.getElementById('emus-stat-total');
            const instEl = document.getElementById('emus-stat-installed');
            const countAll = document.getElementById('emu-count-all');
            const countInst = document.getElementById('emu-count-installed');
            const countMiss = document.getElementById('emu-count-missing');

            const total = data.total || allEmus.length;
            const installed = data.installed_count !== undefined ? data.installed_count : allEmus.filter(e => e.installed).length;
            const missing = total - installed;

            if (totalEl) totalEl.innerText = total;
            if (instEl) instEl.innerText = installed;
            if (countAll) countAll.innerText = total;
            if (countInst) countInst.innerText = installed;
            if (countMiss) countMiss.innerText = missing;
        }

        function setEmuFilter(filter) {
            currentEmuFilter = filter;
            document.querySelectorAll('[id^="emu-filter-"]').forEach(b => {
                b.className = 'btn btn-secondary';
            });
            const activeBtn = document.getElementById(`emu-filter-${filter}`);
            if (activeBtn) activeBtn.className = 'btn btn-primary';
            renderEmusGrid();
        }

        function filterEmusWeb() {
            renderEmusGrid();
        }

        function renderEmusGrid() {
            const container = document.getElementById('emu-grid-container');
            const empty = document.getElementById('emu-empty');
            if (!container) return;

            const query = (document.getElementById('emu-search-input')?.value || '').trim().toLowerCase();
            
            let filtered = allEmus.filter(item => {
                if (query) {
                    const matchName = (item.name || '').toLowerCase().includes(query);
                    const matchId = (item.id || '').toLowerCase().includes(query);
                    const matchCore = (item.active_core || item.core || '').toLowerCase().includes(query);
                    const matchDesc = (item.desc || '').toLowerCase().includes(query);
                    const matchExt = (item.extlist || '').toLowerCase().includes(query);
                    if (!matchName && !matchId && !matchCore && !matchDesc && !matchExt) return false;
                }

                if (currentEmuFilter === 'installed') return !!item.installed;
                if (currentEmuFilter === 'missing') return !item.installed;
                if (currentEmuFilter === 'retro') return item.category === '8-Bit' || item.category === '16-Bit';
                if (currentEmuFilter === 'handheld') return item.category === 'Handheld';
                if (currentEmuFilter === '3d') return item.category === '3D Consoles';
                if (currentEmuFilter === 'arcade') return item.category === 'Arcade';
                if (currentEmuFilter === 'engine') return item.category === 'Engines' || item.category === 'Media';

                return true;
            });

            if (!filtered.length) {
                container.innerHTML = '';
                if (empty) empty.style.display = 'block';
                return;
            }
            if (empty) empty.style.display = 'none';

            container.innerHTML = filtered.map(item => {
                const isInst = !!item.installed;
                const iconSrc = item.icon_url || `/assets/emus_preview/ic-${item.id.toLowerCase()}.png`;
                const category = item.category || 'Other';
                const core = item.active_core || item.core || 'RetroArch';
                const romCount = item.rom_count || 0;
                const sizeStr = item.package_size || '';

                return `
                <div class="emu-card ${isInst ? 'installed' : ''}" id="emu-card-${item.id}">
                    <div class="emu-card-header">
                        <img src="${iconSrc}" class="emu-icon-img" onerror="this.src='/icon.png'" alt="${item.id}">
                        <div class="emu-title-wrap">
                            <div class="emu-title">${item.name} (${item.id})</div>
                            <div class="emu-subtitle">
                                <span>${item.company || ''} ${item.year ? '• ' + item.year : ''}</span>
                            </div>
                        </div>
                    </div>
                    <div class="emu-card-body">
                        <div class="emu-meta-row">
                            <span class="emu-tag ${isInst ? 'installed-badge' : 'missing-badge'}">
                                ${isInst ? '🟢 Đã cài đặt' : '⚪ Chưa cài'}
                            </span>
                            <span class="emu-tag">${category}</span>
                            <span class="emu-tag core-badge">⚡ ${core}</span>
                            <span class="emu-tag">💾 ${romCount} ROMs</span>
                        </div>
                        <div class="emu-desc">${item.desc || 'Hệ máy giả lập cho TrimUI.'}</div>
                        ${item.extlist ? `<div style="font-size: 11px; color: var(--text-muted); font-family: monospace;">Định dạng: ${item.extlist}</div>` : ''}
                    </div>
                    <div class="emu-card-footer">
                        ${!isInst ? `
                            <button class="btn btn-primary" style="flex: 1;" onclick="installEmuWeb('${item.id}', this)">
                                <span>📥</span> Cài đặt ngay ${sizeStr ? '(' + sizeStr + ')' : ''}
                            </button>
                        ` : `
                            <button class="btn btn-secondary" style="flex: 1;" onclick="installEmuWeb('${item.id}', this)">
                                <span>🔄</span> Cài lại / Update
                            </button>
                            <button class="btn btn-danger" style="padding: 6px 12px;" title="Gỡ bỏ khỏi Emus (Giữ nguyên ROM)" onclick="uninstallEmuWeb('${item.id}', this)">
                                <span>🗑️</span>
                            </button>
                        `}
                    </div>
                </div>
                `;
            }).join('');
        }

        async function installEmuWeb(sysId, btnEl) {
            if (!sysId) return;
            const oldText = btnEl ? btnEl.innerHTML : '';
            if (btnEl) {
                btnEl.disabled = true;
                btnEl.innerHTML = `<span>⏳</span> Đang cài...`;
            }

            try {
                const res = await fetch('/api/emus/install', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sys_id: sysId })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || `Đã cài đặt thành công ${sysId}!`);
                    await loadEmus(false);
                    if (typeof loadSystems === 'function') loadSystems(true);
                } else {
                    showToast('Lỗi: ' + (data.error || 'Cài đặt thất bại'));
                    if (btnEl) {
                        btnEl.disabled = false;
                        btnEl.innerHTML = oldText;
                    }
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e.message);
                if (btnEl) {
                    btnEl.disabled = false;
                    btnEl.innerHTML = oldText;
                }
            }
        }

        async function uninstallEmuWeb(sysId, btnEl) {
            if (!sysId) return;
            if (!confirm(`Bạn có chắc muốn gỡ bỏ hệ máy ${sysId} khỏi danh sách giả lập?\n\nLƯU Ý: Toàn bộ file ROM game trong Roms/${sysId} của bạn vẫn được giữ an toàn!`)) {
                return;
            }

            if (btnEl) {
                btnEl.disabled = true;
                btnEl.innerHTML = `<span>⏳</span>`;
            }

            try {
                const res = await fetch('/api/emus/uninstall', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sys_id: sysId })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || `Đã gỡ bỏ ${sysId}!`);
                    await loadEmus(false);
                    if (typeof loadSystems === 'function') loadSystems(true);
                } else {
                    showToast('Lỗi: ' + (data.error || 'Gỡ bỏ thất bại'));
                    if (btnEl) {
                        btnEl.disabled = false;
                        btnEl.innerHTML = `<span>🗑️</span>`;
                    }
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e.message);
                if (btnEl) {
                    btnEl.disabled = false;
                    btnEl.innerHTML = `<span>🗑️</span>`;
                }
            }
        }

        // ==================== THEME STORE ====================
        async function loadThemes(force = false) {
            const loading = document.getElementById('theme-loading');
            const container = document.getElementById('theme-grid-container');
            const empty = document.getElementById('theme-empty');
            if (loading) loading.style.display = 'block';
            if (container) container.innerHTML = '';
            if (empty) empty.style.display = 'none';

            try {
                const res = await fetch('/api/themes');
                const data = await res.json();
                if (data.ok) {
                    allThemes = data.themes || [];
                    updateThemeFilterCounts();
                    renderThemesList();
                } else {
                    showToast('Lỗi nạp danh sách theme: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Không kết nối được API Theme Store: ' + e);
            } finally {
                if (loading) loading.style.display = 'none';
            }
        }

        function updateThemeFilterCounts() {
            const total = allThemes.length;
            const installed = allThemes.filter(t => t.is_installed).length;
            const available = total - installed;

            const elAll = document.getElementById('theme-count-all');
            const elInst = document.getElementById('theme-count-installed');
            const elAvail = document.getElementById('theme-count-available');

            if (elAll) elAll.textContent = total;
            if (elInst) elInst.textContent = installed;
            if (elAvail) elAvail.textContent = available;
        }

        function setThemeFilter(filter) {
            currentThemeFilter = filter;
            ['all', 'installed', 'available'].forEach(f => {
                const btn = document.getElementById(`theme-filter-${f}`);
                if (btn) {
                    if (f === filter) {
                        btn.className = 'btn btn-primary';
                    } else {
                        btn.className = 'btn btn-secondary';
                    }
                }
            });
            renderThemesList();
        }

        function filterThemesWeb() {
            renderThemesList();
        }

        function renderThemesList() {
            const container = document.getElementById('theme-grid-container');
            const empty = document.getElementById('theme-empty');
            if (!container) return;

            const searchVal = (document.getElementById('theme-search-input')?.value || '').toLowerCase().trim();

            const list = allThemes.filter(t => {
                if (currentThemeFilter === 'installed' && !t.is_installed) return false;
                if (currentThemeFilter === 'available' && t.is_installed) return false;
                if (searchVal) {
                    const name = (t.name || '').toLowerCase();
                    const folder = (t.folder || '').toLowerCase();
                    if (!name.includes(searchVal) && !folder.includes(searchVal)) return false;
                }
                return true;
            });

            if (list.length === 0) {
                container.innerHTML = '';
                if (empty) empty.style.display = 'block';
                return;
            }

            if (empty) empty.style.display = 'none';

            let html = '';
            list.forEach(t => {
                const isInst = t.is_installed;
                const prevUrl = `/api/themes/preview?name=${encodeURIComponent(t.folder)}`;
                const sizeStr = t.size_str || '';
                const fontStr = t.font ? `Font: ${t.font}` : 'Font: Mặc định';

                html += `
                <div class="theme-card">
                    <div class="theme-thumb-box">
                        <img src="${prevUrl}" alt="${t.name}" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'200\\' height=\\'150\\' viewBox=\\'0 0 200 150\\'><rect fill=\\'%23111\\' width=\\'200\\' height=\\'150\\'/><text fill=\\'%23666\\' x=\\'50%\\' y=\\'50%\\' text-anchor=\\'middle\\'>Chưa có preview</text></svg>'">
                        ${isInst ? '<div class="theme-badge-installed">✓ ĐÃ CÀI</div>' : ''}
                    </div>
                    <div class="theme-body">
                        <div>
                            <div class="theme-title" title="${t.name}">${t.name}</div>
                            <div class="theme-meta">
                                <span>${fontStr}</span>
                                <span>${sizeStr}</span>
                            </div>
                        </div>
                        <div class="theme-actions">
                            ${isInst ? `
                                <button class="btn btn-sm btn-primary" style="flex:1;" onclick="installThemeWeb('${t.folder}')">Cài lại</button>
                                <button class="btn btn-sm btn-danger" onclick="uninstallThemeWeb('${t.folder}')">Gỡ bỏ</button>
                            ` : `
                                <button class="btn btn-sm btn-green" style="flex:1;" onclick="installThemeWeb('${t.folder}')">⚡ Cài đặt Theme</button>
                            `}
                        </div>
                    </div>
                </div>
                `;
            });

            container.innerHTML = html;
        }

        async function installThemeWeb(folder) {
            showToast(`Đang cài đặt theme ${folder}...`);
            try {
                const res = await fetch('/api/themes/install', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder: folder })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Cài đặt theme thành công!');
                    loadThemes(true);
                } else {
                    showToast('Lỗi cài theme: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e);
            }
        }

        async function uninstallThemeWeb(folder) {
            if (!confirm(`Bạn có chắc muốn gỡ bỏ theme "${folder}" khỏi thẻ nhớ?`)) return;
            try {
                const res = await fetch('/api/themes/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder: folder })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã gỡ bỏ theme!');
                    loadThemes(true);
                } else {
                    showToast('Lỗi gỡ bỏ: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e);
            }
        }

        async function restoreStockThemeWeb() {
            if (!confirm('Bạn có chắc chắn muốn khôi phục lại Theme Mặc Định gốc xuất xưởng của TrimUI Stock ROM?')) return;
            showToast('Đang khôi phục theme mặc định gốc...');
            try {
                const res = await fetch('/api/themes/restore', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã khôi phục theme mặc định gốc!');
                    loadThemes(true);
                } else {
                    showToast('Lỗi khôi phục: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e);
            }
        }

        async function loadStorageStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.ok && data.storage) {
                    const elTxt = document.getElementById('storage-text');
                    if (elTxt) {
                        elTxt.innerHTML = `Trống <strong>${data.storage.free_gb}</strong> / ${data.storage.total_gb}`;
                    } else {
                        const elStat = document.getElementById('storage-stat');
                        if (elStat) elStat.innerHTML = `<span>💾</span> Trống <strong>${data.storage.free_gb}</strong> / ${data.storage.total_gb}`;
                    }
                }
            } catch (e) {}
        }

        // ==================== QUẢN LÝ GAME (GAMES MANAGER) ====================
        async function loadSystems(forceSelectFirst = false) {
            try {
                const res = await fetch('/api/systems');
                const data = await res.json();
                if (data.ok) {
                    allSystems = data.systems || [];
                    renderSystemsList(data.no_art_count || 0);
                    if (allSystems.length > 0 && (!currentSystem || forceSelectFirst)) {
                        selectSystem(allSystems[0].dir);
                    }
                }
            } catch (e) {
                console.error('Error loading systems:', e);
            }
        }

        function renderSystemsList(noArtCount) {
            const listEl = document.getElementById('systems-list');
            let html = '';
            if (noArtCount > 0) {
                html += `<div class="sys-item ${currentSystem === '__no_art__' ? 'active' : ''}" onclick="selectSystem('__no_art__')">
                    <span style="color:#f59e0b;">⚠️ Thiếu ảnh bìa</span>
                    <span class="count" style="background:#b45309; color:#fff;">${noArtCount}</span>
                </div>`;
            }
            allSystems.forEach(s => {
                const activeCls = (currentSystem === s.dir) ? 'active' : '';
                html += `<div class="sys-item ${activeCls}" onclick="selectSystem('${s.dir}')">
                    <span>${s.name}</span>
                    <span class="count">${s.count}</span>
                </div>`;
            });
            listEl.innerHTML = html;
        }

        async function selectSystem(sysDir) {
            currentSystem = sysDir;
            renderSystemsList();
            try {
                const res = await fetch(`/api/games?system=${encodeURIComponent(sysDir)}`);
                const data = await res.json();
                if (data.ok) {
                    currentGames = data.games || [];
                    renderGamesGrid(currentGames);
                }
            } catch (e) {
                console.error('Error loading games:', e);
            }
        }

        function renderGamesGrid(games) {
            const container = document.getElementById('games-container');
            const emptyEl = document.getElementById('empty-state');
            if (!games || games.length === 0) {
                container.innerHTML = '';
                emptyEl.style.display = 'block';
                return;
            }
            emptyEl.style.display = 'none';
            let html = '';
            games.forEach((g, idx) => {
                const artHtml = g.has_art ? `<img src="${g.art_url}" loading="lazy" alt="${g.title}">` : `<div style="font-size:32px;">🎮</div>`;
                html += `<div class="game-card">
                    <div class="art-box">${artHtml}</div>
                    <div class="game-info">
                        <div class="game-title" title="${g.filename}">${g.title}</div>
                        <div class="game-meta">
                            <span>${g.system}</span>
                            <span>${g.size_str}</span>
                        </div>
                        <div class="game-actions">
                            <button class="btn btn-sm btn-secondary" onclick="openScrapeModal('${g.system}', '${encodeURIComponent(g.filename)}')">Cào ảnh</button>
                            <button class="btn btn-sm btn-secondary" onclick="openRenameModal('${g.system}', '${encodeURIComponent(g.filename)}')">Đổi tên</button>
                            <button class="btn btn-sm btn-secondary" onclick="openMoveModal('${g.system}', '${encodeURIComponent(g.filename)}')">Chuyển</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteGame('${g.system}', '${encodeURIComponent(g.filename)}')">Xóa</button>
                        </div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        function filterGames() {
            const q = document.getElementById('search-input').value.toLowerCase().trim();
            if (!q) {
                renderGamesGrid(currentGames);
                return;
            }
            const filtered = currentGames.filter(g => g.title.toLowerCase().includes(q) || g.filename.toLowerCase().includes(q));
            renderGamesGrid(filtered);
        }

        // ==================== TẢI ROM QUA LINK (DRIVE / DIRECT) ====================
        let currentResolvedUrlData = null;

        function openDownloadByUrlModal() {
            const sysSel = document.getElementById('url-dl-sys-select');
            if (sysSel && allSystems.length) {
                let opts = '';
                allSystems.forEach(s => {
                    const sel = (currentSystem === s.dir) ? 'selected' : '';
                    opts += `<option value="${s.dir}" ${sel}>${s.name || s.dir} (${s.dir})</option>`;
                });
                sysSel.innerHTML = opts;
            }
            const previewBox = document.getElementById('url-download-preview-box');
            if (previewBox) previewBox.style.display = 'none';
            currentResolvedUrlData = null;
            openModal('modal-download-by-url');
        }

        async function resolveUrlForDownload() {
            const input = document.getElementById('url-download-input');
            const url = input ? input.value.trim() : '';
            if (!url) {
                showToast('Vui lòng nhập đường dẫn Google Drive hoặc link direct!');
                return;
            }
            const btn = document.getElementById('btn-resolve-url-dl');
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Đang kiểm tra...';
            }
            try {
                const res = await fetch('/api/gdrive/resolve', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                const data = await res.json();
                if (data.ok) {
                    currentResolvedUrlData = data;
                    const previewBox = document.getElementById('url-download-preview-box');
                    const badge = document.getElementById('url-dl-type-badge');
                    const titleDisp = document.getElementById('url-dl-title-disp');
                    const fnDisp = document.getElementById('url-dl-filename-disp');
                    const szDisp = document.getElementById('url-dl-size-disp');
                    const sysSel = document.getElementById('url-dl-sys-select');

                    if (previewBox) previewBox.style.display = 'block';
                    if (badge) {
                        badge.innerText = data.type === 'static' ? 'DIRECT URL' : 'GOOGLE DRIVE';
                        badge.style.background = data.type === 'static' ? '#059669' : '#2563eb';
                    }
                    if (titleDisp) titleDisp.innerText = data.title || data.filename || 'Tệp Game';
                    if (fnDisp) fnDisp.innerText = data.filename || '--';
                    if (szDisp) szDisp.innerText = data.file_size_str || '--';

                    if (data.suggested_system && sysSel) {
                        for (let opt of sysSel.options) {
                            if (opt.value.toUpperCase() === data.suggested_system.toUpperCase()) {
                                opt.selected = true;
                                break;
                            }
                        }
                    }
                    showToast('Đã nhận diện tệp ROM thành công!');
                } else {
                    showToast('Lỗi: ' + (data.error || 'Không kiểm tra được liên kết'));
                }
            } catch (e) {
                showToast('Lỗi mạng: ' + (e.message || e));
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = 'Kiểm tra link';
                }
            }
        }

        async function submitUrlDownloadDirect() {
            const input = document.getElementById('url-download-input');
            const url = input ? input.value.trim() : '';
            if (!url) {
                showToast('Vui lòng nhập đường dẫn!');
                return;
            }
            const sysSel = document.getElementById('url-dl-sys-select');
            const sysCode = sysSel ? sysSel.value : '';
            if (!sysCode) {
                showToast('Vui lòng chọn hệ máy để xả game!');
                return;
            }
            const extractCb = document.getElementById('url-dl-extract-cb');
            const doExtract = extractCb ? extractCb.checked : true;

            const btn = document.getElementById('btn-submit-url-dl');
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Đang gửi lệnh...';
            }

            const payload = {
                url: url,
                sys_code: sysCode,
                direct_link: currentResolvedUrlData ? (currentResolvedUrlData.direct_link || '') : '',
                filename: currentResolvedUrlData ? (currentResolvedUrlData.filename || '') : '',
                title: currentResolvedUrlData ? (currentResolvedUrlData.title || '') : '',
                extract: doExtract
            };

            try {
                const res = await fetch('/api/gdrive/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Bắt đầu tải ROM về thẻ nhớ!');
                    closeModal('modal-download-by-url');
                    checkStoreDownloadsStatus();
                } else {
                    showToast('Lỗi: ' + (data.error || 'Không thể bắt đầu tải'));
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + (e.message || e));
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = '🚀 Tải ngay về máy';
                }
            }
        }

        // ==================== CÀO BOXART (SUB-TAB) ====================
        let boxartCurrentSys = null;
        let boxartGamesList = [];
        let isBoxartBatchRunning = false;
        let stopBoxartBatchRequested = false;

        async function loadBoxartSystems() {
            if (!allSystems.length) {
                try {
                    const res = await fetch('/api/systems');
                    const data = await res.json();
                    if (data.ok) allSystems = data.systems || [];
                } catch (e) {}
            }
            renderBoxartSidebar();
            if (allSystems.length > 0 && !boxartCurrentSys) {
                selectBoxartSystem(currentSystem || allSystems[0].dir);
            }
        }

        function renderBoxartSidebar() {
            const listEl = document.getElementById('boxart-systems-list');
            if (!listEl) return;
            let html = '';
            allSystems.forEach(s => {
                const active = (boxartCurrentSys === s.dir) ? 'active' : '';
                html += `<div class="sys-item ${active}" onclick="selectBoxartSystem('${s.dir}')">
                    <span>🎮 ${s.name || s.dir}</span>
                    <span class="badge">${s.count || 0}</span>
                </div>`;
            });
            listEl.innerHTML = html;
        }

        async function selectBoxartSystem(sysDir) {
            boxartCurrentSys = sysDir;
            renderBoxartSidebar();
            const curName = document.getElementById('boxart-cur-sys-name');
            if (curName) curName.innerText = sysDir;

            const container = document.getElementById('boxart-games-container');
            const empty = document.getElementById('boxart-empty-state');
            if (container) container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:30px; color:#38bdf8;">Đang nạp danh sách game...</div>';
            if (empty) empty.style.display = 'none';

            try {
                const res = await fetch(`/api/games?system=${encodeURIComponent(sysDir)}`);
                const data = await res.json();
                if (data.ok) {
                    boxartGamesList = data.games || [];
                    updateBoxartStats();
                    renderBoxartGamesGrid();
                }
            } catch (e) {
                if (container) container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px; color:#ef4444;">Lỗi: ${e.message}</div>`;
            }
        }

        function updateBoxartStats() {
            const total = boxartGamesList.length;
            const hasArt = boxartGamesList.filter(g => g.has_art).length;
            const pct = total > 0 ? Math.round((hasArt / total) * 100) : 0;

            const tEl = document.getElementById('boxart-stat-total');
            const hEl = document.getElementById('boxart-stat-has');
            const pEl = document.getElementById('boxart-stat-pct');
            if (tEl) tEl.innerText = total;
            if (hEl) hEl.innerText = hasArt;
            if (pEl) pEl.innerText = `${pct}%`;
        }

        function renderBoxartGamesGrid() {
            const container = document.getElementById('boxart-games-container');
            const empty = document.getElementById('boxart-empty-state');
            if (!container) return;

            if (!boxartGamesList.length) {
                container.innerHTML = '';
                if (empty) empty.style.display = 'block';
                return;
            }
            if (empty) empty.style.display = 'none';

            let html = '';
            boxartGamesList.forEach(g => {
                const imgTag = g.has_art 
                    ? `<img src="${g.art_url}" id="boxart-img-${boxartCurrentSys}-${g.filename}" loading="lazy" style="width:100%; height:100%; object-fit:contain;">`
                    : `<div id="boxart-img-${boxartCurrentSys}-${g.filename}" style="display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%; height:100%; color:var(--text-sub); font-size:11px;"><span>🖼️</span><span>Chưa có ảnh</span></div>`;

                html += `<div class="game-card" style="padding:10px;">
                    <div class="art-box" style="height:140px;">${imgTag}</div>
                    <div class="game-info" style="margin-top:8px;">
                        <div class="game-title" title="${g.title || g.filename}">${g.title || g.filename}</div>
                        <div style="font-size:11px; color:var(--text-sub); margin-top:2px;">${g.filename}</div>
                        <div style="display:flex; gap:6px; margin-top:8px;">
                            <button class="btn btn-sm btn-primary" style="flex:1;" onclick="scrapeSingleBoxartSubTab('${boxartCurrentSys}', '${encodeURIComponent(g.filename)}')">⚡ Cào ảnh</button>
                            <button class="btn btn-sm btn-secondary" onclick="openScrapeModal('${boxartCurrentSys}', '${encodeURIComponent(g.filename)}')">🔍 Tìm</button>
                        </div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        async function scrapeSingleBoxartSubTab(system, encodedFilename) {
            const fname = decodeURIComponent(encodedFilename);
            showToast(`Đang cào ảnh cho ${fname}...`);
            try {
                const res = await fetch('/api/scrape/auto', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({system: system, filename: fname, fast: true})
                });
                const data = await res.json();
                if (data.ok && data.art_url) {
                    showToast(`Cào thành công ảnh cho ${fname}!`);
                    const imgBox = document.getElementById(`boxart-img-${system}-${fname}`);
                    if (imgBox) {
                        imgBox.outerHTML = `<img src="${data.art_url}" id="boxart-img-${system}-${fname}" style="width:100%; height:100%; object-fit:contain;">`;
                    }
                    const target = boxartGamesList.find(g => g.filename === fname);
                    if (target) target.has_art = true;
                    updateBoxartStats();
                } else {
                    showToast(`Không tìm thấy ảnh: ${data.error || ''}`);
                }
            } catch (e) {
                showToast(`Lỗi cào ảnh: ${e.message}`);
            }
        }

        async function startBoxartSubTabScrape() {
            if (isBoxartBatchRunning) return;
            const missingGames = boxartGamesList.filter(g => !g.has_art);
            if (!missingGames.length) {
                showToast('Hệ máy này đã có đầy đủ ảnh bìa!');
                return;
            }

            isBoxartBatchRunning = true;
            stopBoxartBatchRequested = false;

            const bar = document.getElementById('boxart-batch-bar');
            const statusText = document.getElementById('boxart-batch-status');
            const pctText = document.getElementById('boxart-batch-pct');
            const fillBar = document.getElementById('boxart-batch-fill');

            if (bar) bar.style.display = 'flex';

            let completed = 0;
            const total = missingGames.length;

            for (let g of missingGames) {
                if (stopBoxartBatchRequested) break;
                if (statusText) statusText.innerText = `Đang cào (${completed + 1}/${total}): ${g.filename}`;
                try {
                    const res = await fetch('/api/scrape/auto', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({system: boxartCurrentSys, filename: g.filename, fast: true})
                    });
                    const data = await res.json();
                    if (data.ok && data.art_url) {
                        g.has_art = true;
                        const imgBox = document.getElementById(`boxart-img-${boxartCurrentSys}-${g.filename}`);
                        if (imgBox) {
                            imgBox.outerHTML = `<img src="${data.art_url}" id="boxart-img-${boxartCurrentSys}-${g.filename}" style="width:100%; height:100%; object-fit:contain;">`;
                        }
                    }
                } catch (e) {}

                completed++;
                const pct = Math.round((completed / total) * 100);
                if (pctText) pctText.innerText = `${pct}%`;
                if (fillBar) fillBar.style.width = `${pct}%`;
                updateBoxartStats();
            }

            isBoxartBatchRunning = false;
            if (bar) {
                setTimeout(() => { bar.style.display = 'none'; }, 2000);
            }
            showToast(stopBoxartBatchRequested ? 'Đã dừng cào ảnh!' : 'Hoàn thành cào toàn bộ ảnh thiếu!');
        }

        function stopBoxartSubTabScrape() {
            stopBoxartBatchRequested = true;
            showToast('Đang dừng cào ảnh...');
        }

        async function cleanupRomImagesWeb() {
            if (!confirm('Bạn có chắc muốn dọn dẹp các tệp/thư mục ảnh trùng trong ROMs?')) return;
            showToast('Đang quét và dọn dẹp ảnh thừa...');
            try {
                const res = await fetch('/api/cleanup_rom_images', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || `Đã dọn dẹp ${data.cleaned_count} ảnh thừa!`);
                    if (boxartCurrentSys) selectBoxartSystem(boxartCurrentSys);
                } else {
                    showToast('Lỗi: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e);
            }
        }

        // ==================== TẢI GAME ONLINE (ROMS STORE) ====================
        let storeSearchTimer = null;

        async function loadStoreInit() {
            try {
                const res = await fetch('/api/store/categories');
                const data = await res.json();
                if (data.ok) {
                    storeCategories = data.categories || [];
                    storeSystems = data.systems || [];
                    renderStoreSidebar();
                    loadStoreGames();
                }
            } catch (e) {
                console.error('Error loadStoreInit:', e);
            }
        }

        function renderStoreSidebar() {
            const catList = document.getElementById('store-categories-list');
            if (catList) {
                let htmlCat = '';
                storeCategories.forEach(c => {
                    const active = (currentStoreCategory === c.id) ? 'active' : '';
                    htmlCat += `<div class="sys-item ${active}" onclick="selectStoreCategory('${c.id}')">
                        <span>${c.icon || '📁'} ${c.name}</span>
                    </div>`;
                });
                catList.innerHTML = htmlCat;
            }

            const sysFilter = document.getElementById('store-system-filter');
            if (sysFilter && storeSystems.length) {
                let opts = '<option value="ALL">Tất cả hệ máy</option>';
                storeSystems.forEach(s => {
                    const sel = (currentStoreSystem === s.code) ? 'selected' : '';
                    opts += `<option value="${s.code}" ${sel}>${s.name} (${s.count})</option>`;
                });
                sysFilter.innerHTML = opts;
            }
        }

        let currentStorePage = 1;
        let storeHasMore = true;
        let isStoreLoading = false;

        let currentStoreSource = 'ALL';

        function selectStoreCategory(catId) {
            currentStoreCategory = catId;
            if (catId === 'GDRIVE') {
                currentStoreSource = 'GDRIVE';
                const selectEl = document.getElementById('store-source-filter');
                if (selectEl) selectEl.value = 'GDRIVE';
            } else if (catId === 'RETROSTIC') {
                currentStoreSource = 'RETROSTIC';
                const selectEl = document.getElementById('store-source-filter');
                if (selectEl) selectEl.value = 'RETROSTIC';
            } else if (catId === 'ARCHIVE') {
                currentStoreSource = 'ARCHIVE';
                const selectEl = document.getElementById('store-source-filter');
                if (selectEl) selectEl.value = 'ARCHIVE';
            } else {
                currentStoreSource = 'ALL';
                const selectEl = document.getElementById('store-source-filter');
                if (selectEl) selectEl.value = 'ALL';
            }
            updateGDriveButtonState();
            const searchInput = document.getElementById('store-search-input');
            if (searchInput) searchInput.value = '';
            renderStoreSidebar();
            resetAndLoadStore();
        }

        function changeStoreSourceFilter() {
            const selectEl = document.getElementById('store-source-filter');
            currentStoreSource = selectEl ? selectEl.value : 'ALL';
            if (currentStoreSource !== 'ALL') {
                currentStoreCategory = currentStoreSource;
                renderStoreSidebar();
            }
            updateGDriveButtonState();
            resetAndLoadStore();
        }

        function toggleGDriveSourceFilter() {
            if (currentStoreSource === 'GDRIVE') {
                currentStoreSource = 'ALL';
                currentStoreCategory = 'HITS';
            } else {
                currentStoreSource = 'GDRIVE';
                currentStoreCategory = 'GDRIVE';
            }
            const selectEl = document.getElementById('store-source-filter');
            if (selectEl) selectEl.value = currentStoreSource;
            renderStoreSidebar();
            updateGDriveButtonState();
            resetAndLoadStore();
        }

        function updateGDriveButtonState() {
            const btn = document.getElementById('btn-toggle-gdrive-source');
            if (!btn) return;
            if (currentStoreSource === 'GDRIVE' || currentStoreCategory === 'GDRIVE') {
                btn.className = 'btn btn-sm btn-primary';
                btn.style.boxShadow = '0 0 10px rgba(37, 99, 235, 0.4)';
            } else {
                btn.className = 'btn btn-sm btn-secondary';
                btn.style.boxShadow = 'none';
            }
        }

        function changeStoreSystemFilter() {
            const selectEl = document.getElementById('store-system-filter');
            currentStoreSystem = selectEl ? selectEl.value : 'ALL';
            resetAndLoadStore();
        }

        function debounceStoreSearch() {
            if (storeSearchTimer) clearTimeout(storeSearchTimer);
            storeSearchTimer = setTimeout(() => {
                resetAndLoadStore();
            }, 300);
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

        async function loadStoreGames(isAppend = false) {
            if (isStoreLoading) return;
            isStoreLoading = true;

            const container = document.getElementById('store-games-container');
            const loading = document.getElementById('store-loading');
            const paginationEl = document.getElementById('store-pagination');

            if (!isAppend) {
                if (container) container.innerHTML = '';
                if (loading) loading.style.display = 'block';
                if (paginationEl) paginationEl.innerHTML = '';
            }

            const sortSelect = document.getElementById('store-sort-select');
            const sort = sortSelect ? sortSelect.value : 'downloads';
            const searchInput = document.getElementById('store-search-input');
            const q = searchInput ? searchInput.value.trim() : '';
            const sysFilter = document.getElementById('store-system-filter');
            const sys = sysFilter ? sysFilter.value : currentStoreSystem;
            const limit = 40;

            let effSource = (currentStoreSource !== 'ALL') ? currentStoreSource : currentStoreCategory;
            let url = `/api/store/games?source_type=${encodeURIComponent(effSource)}&system=${encodeURIComponent(sys)}&sort=${sort}&page=${currentStorePage}&limit=${limit}`;
            if (q) url += `&query=${encodeURIComponent(q)}`;

            try {
                const res = await fetch(url);
                const data = await res.json();
                if (loading) loading.style.display = 'none';

                if (data.ok && data.games && data.games.length > 0) {
                    if (isAppend) {
                        storeGames = storeGames.concat(data.games);
                        renderStoreGrid(data.games, true);
                    } else {
                        storeGames = data.games;
                        renderStoreGrid(storeGames, false);
                    }
                    if (paginationEl) {
                        renderStorePagination(data.page || currentStorePage, data.games.length >= limit);
                    }
                } else {
                    if (!isAppend && container) {
                        container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:50px 20px; color:var(--text-sub);"><div style="font-size:36px; margin-bottom:10px;">🔍</div><div style="font-size:15px; font-weight:600; color:#fff;">Không tìm thấy game phù hợp</div><p style="font-size:12px; margin-top:6px;">Hãy thử tìm từ khóa khác (VD: Mario, Contra, Pokemon...)</p></div>';
                    }
                    if (paginationEl) paginationEl.innerHTML = '';
                }
            } catch (e) {
                console.error("loadStoreGames error:", e);
                if (loading) loading.style.display = 'none';
                if (!isAppend && container) {
                    container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#ef4444;">Lỗi tải dữ liệu: ${e.message || e}</div>`;
                }
            } finally {
                isStoreLoading = false;
            }
        }

        function renderStorePagination(currentPage, hasNext) {
            const paginationEl = document.getElementById('store-pagination');
            if (!paginationEl) return;
            let html = '';
            if (currentPage > 1) {
                html += `<button class="btn btn-secondary" onclick="goToStorePage(${currentPage - 1})">⬅ Trang trước</button>`;
            }
            html += `<span style="display:flex; align-items:center; padding:0 12px; font-size:13px; font-weight:700; color:var(--text-sub);">Trang ${currentPage}</span>`;
            if (hasNext) {
                html += `<button class="btn btn-primary" onclick="goToStorePage(${currentPage + 1})">Trang sau ➡</button>`;
            }
            paginationEl.innerHTML = html;
        }

        function goToStorePage(page) {
            currentStorePage = page;
            loadStoreGames(false);
            const mainEl = document.querySelector('#subview-games-online main') || document.querySelector('#tab-view-store main');
            if (mainEl) mainEl.scrollTop = 0;
        }

        function renderStoreGrid(games, isAppend = false) {
            const container = document.getElementById('store-games-container');
            if (!container) return;
            let html = '';
            games.forEach((g, idx) => {
                const imgUrl = g.img_url ? `<img src="${g.img_url}" loading="lazy" alt="${g.title}">` : `<div style="font-size:32px;">🕹️</div>`;
                const isViet = g.is_viet ? `<span class="badge-tag badge-viet">VIỆT HÓA</span>` : '';
                const isHack = g.is_hack ? `<span class="badge-tag badge-hack">HACK</span>` : '';
                const isHit = g.is_hit ? `<span class="badge-tag badge-top">TOP</span>` : '';
                const isGDrive = (g.source_name === 'GDRIVE' || (g.rom_url && g.rom_url.includes('drive.google.com'))) ? `<span class="badge-tag" style="background:#2563eb; color:#fff; font-weight:700;">GDRIVE</span>` : '';

                const actionBtn = g.is_installed 
                    ? `<span class="badge-tag badge-installed">✓ Đã có trên thẻ</span>`
                    : `<button class="btn btn-sm btn-green" id="btn-store-dl-${g.id}" onclick="downloadStoreGame(${g.id}, '${g.sys_code}', '${encodeURIComponent(g.title)}', '${encodeURIComponent(g.rom_url || '')}', '${encodeURIComponent(g.filename || '')}', '${encodeURIComponent(g.img_url || '')}')">⬇️ Tải về máy</button>`;

                html += `<div class="game-card">
                    <div class="art-box">${imgUrl}</div>
                    <div class="game-info">
                        <div style="display:flex; gap:4px; margin-bottom:4px; flex-wrap:wrap;">${isViet}${isHack}${isHit}${isGDrive}</div>
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
        }

        async function downloadStoreGame(id, sysCode, titleEnc, romUrlEnc, fnameEnc, imgUrlEnc) {
            const title = decodeURIComponent(titleEnc);
            const romUrl = decodeURIComponent(romUrlEnc);
            const fname = decodeURIComponent(fnameEnc);
            const imgUrl = decodeURIComponent(imgUrlEnc);

            const btn = document.getElementById(`btn-store-dl-${id}`);
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Đang tải...';
            }

            try {
                const res = await fetch('/api/store/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        game_id: id,
                        sys_code: sysCode,
                        title: title,
                        rom_url: romUrl,
                        filename: fname,
                        img_url: imgUrl
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(`Bắt đầu tải: ${title}`);
                    startStoreDownloadPolling();
                } else {
                    alert('Lỗi: ' + (data.error || 'Không thể tải'));
                    if (btn) { btn.disabled = false; btn.innerText = '⬇️ Tải về máy'; }
                }
            } catch (e) {
                alert('Lỗi kết nối: ' + e);
                if (btn) { btn.disabled = false; btn.innerText = '⬇️ Tải về máy'; }
            }
        }

        function startStoreDownloadPolling() {
            const banner = document.getElementById('store-active-downloads') || document.getElementById('store-download-banner');
            if (banner) banner.style.display = 'block';

            if (storeDlInterval) clearInterval(storeDlInterval);
            storeDlInterval = setInterval(async () => {
                try {
                    const res = await fetch('/api/store/download/status');
                    const data = await res.json();
                    if (data.ok && data.downloads && data.downloads.length > 0) {
                        const dlList = document.getElementById('store-dl-list');
                        const speedEl = document.getElementById('store-dl-speed');
                        let allDone = true;
                        let html = '';

                        data.downloads.forEach(active => {
                            const pct = active.progress_pct || 0;
                            let sizeInfo = '';
                            if (active.total_bytes > 0) {
                                const curMb = (active.downloaded_bytes / (1024 * 1024)).toFixed(1);
                                const totMb = (active.total_bytes / (1024 * 1024)).toFixed(1);
                                sizeInfo = ` (${curMb} / ${totMb} MB)`;
                            } else if (active.downloaded_bytes > 0) {
                                const curMb = (active.downloaded_bytes / (1024 * 1024)).toFixed(1);
                                sizeInfo = ` (${curMb} MB)`;
                            }

                            let statusText = 'Đang nhận tệp...';
                            let statusColor = 'var(--text-sub)';
                            if (active.status === 'completed') {
                                statusText = '✓ Đã tải xong và lưu vào thẻ nhớ!';
                                statusColor = '#34d399';
                            } else if (active.status === 'error') {
                                statusText = `❌ ${active.error_msg || 'Lỗi tải game'}`;
                                statusColor = '#f87171';
                            } else {
                                allDone = false;
                            }

                            html += `<div style="margin-bottom:8px;">
                                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                                    <span style="font-weight:700; color:#fff;">${active.title} (${active.sys_code})</span>
                                    <span style="font-weight:700; color:#10b981;">${pct}%</span>
                                </div>
                                <div class="progress-bar-bg" style="height:6px; background:#1e293b; border-radius:4px; overflow:hidden; margin-bottom:4px;">
                                    <div style="height:100%; width:${pct}%; background:linear-gradient(90deg, #10b981, #38bdf8); transition:width 0.2s;"></div>
                                </div>
                                <div style="display:flex; justify-content:space-between; font-size:11px; color:${statusColor};">
                                    <span>${statusText}</span>
                                    <span>${active.speed_str || '0 KB/s'}${sizeInfo}</span>
                                </div>
                            </div>`;
                        });

                        if (dlList) dlList.innerHTML = html;

                        if (allDone) {
                            clearInterval(storeDlInterval);
                            setTimeout(() => { if (banner) banner.style.display = 'none'; }, 4000);
                            loadStoreGames(false);
                            if (typeof loadSystems === 'function') loadSystems();
                        }
                    } else {
                        clearInterval(storeDlInterval);
                        if (banner) banner.style.display = 'none';
                    }
                } catch (e) {}
            }, 500);
        }

        // ==================== QUẢN LÝ YOUTUBE ====================
        async function loadYouTubeInit() {
            try {
                const res = await fetch('/api/youtube/playlists');
                const data = await res.json();
                if (data.ok) {
                    ytPlaylists = data.playlists || [];
                    renderYouTubePlaylists(data.favorites_count || 0);
                    loadYouTubeVideos('trending');
                }
            } catch (e) {
                console.error('Error loadYouTubeInit:', e);
            }
        }

        function renderYouTubePlaylists(favCount = 0) {
            const listEl = document.getElementById('yt-playlists-list');
            let html = '';
            
            // Item 1: Trending
            html += `<div class="yt-playlist-item ${currentYtTab === 'trending' ? 'active' : ''}" onclick="selectYouTubePlaylist('trending')">
                <span>🔥 Trending YouTube</span>
            </div>`;

            // Item 2: Favorites
            html += `<div class="yt-playlist-item ${currentYtTab === 'favorites' ? 'active' : ''}" onclick="selectYouTubePlaylist('favorites')">
                <span>⭐ Video Yêu thích</span>
                <span class="count" style="background:#b45309; color:#fff; font-size:11px; padding:2px 7px; border-radius:10px;">${favCount}</span>
            </div>`;

            // Custom playlists
            ytPlaylists.forEach(q => {
                const active = (currentYtTab === q) ? 'active' : '';
                html += `<div class="yt-playlist-item ${active}" onclick="selectYouTubePlaylist('${q.replace(/'/g, "\\'")}')">
                    <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;">${q}</span>
                    <button class="btn btn-sm btn-danger" style="padding:2px 6px; font-size:10px;" onclick="deletePlaylist(event, '${q.replace(/'/g, "\\'")}')">&times;</button>
                </div>`;
            });

            listEl.innerHTML = html;
        }

        function selectYouTubePlaylist(q) {
            currentYtTab = q;
            renderYouTubePlaylists();
            loadYouTubeVideos(q);
        }

        async function loadYouTubeVideos(query) {
            const container = document.getElementById('yt-videos-container');
            const loading = document.getElementById('yt-loading');
            const countEl = document.getElementById('yt-video-count');
            const titleEl = document.getElementById('yt-current-title');

            container.innerHTML = '';
            loading.style.display = 'block';

            if (query === 'favorites') {
                titleEl.innerText = '⭐ Video Yêu thích';
                try {
                    const res = await fetch('/api/youtube/favorites');
                    const data = await res.json();
                    loading.style.display = 'none';
                    if (data.ok) {
                        ytVideos = data.favorites || [];
                        countEl.innerText = `${ytVideos.length} video`;
                        renderYouTubeGrid(ytVideos, true);
                    }
                } catch (e) { loading.style.display = 'none'; }
                return;
            }

            titleEl.innerText = (query === 'trending') ? '🔥 Trending YouTube' : `📺 Playlist: ${query}`;
            try {
                const res = await fetch(`/api/youtube/search?q=${encodeURIComponent(query)}&limit=24`);
                const data = await res.json();
                loading.style.display = 'none';
                if (data.ok && data.videos) {
                    ytVideos = data.videos;
                    countEl.innerText = `${ytVideos.length} video`;
                    renderYouTubeGrid(ytVideos, false);
                }
            } catch (e) {
                loading.style.display = 'none';
            }
        }

        function executeYouTubeSearch() {
            const q = document.getElementById('yt-search-input').value.trim();
            if (!q) return;
            currentYtTab = q;
            renderYouTubePlaylists();
            loadYouTubeVideos(q);
        }

        function renderYouTubeGrid(videos, isFavList = false) {
            const container = document.getElementById('yt-videos-container');
            if (!videos || videos.length === 0) {
                container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-sub);">Chưa có video nào.</div>';
                return;
            }

            let html = '';
            videos.forEach(v => {
                const favBtn = isFavList 
                    ? `<button class="btn btn-sm btn-danger" onclick="removeFromFavorites('${v.id}')">❌ Xóa khỏi Yêu thích</button>`
                    : `<button class="btn btn-sm btn-gold" onclick="addToFavorites('${v.id}', '${encodeURIComponent(v.title)}', '${encodeURIComponent(v.channel || '')}', '${encodeURIComponent(v.duration || '')}', '${encodeURIComponent(v.thumb || '')}')">⭐ Lưu yêu thích</button>`;

                html += `<div class="yt-card">
                    <div class="yt-thumb-box">
                        <img src="${v.thumb}" loading="lazy" alt="${v.title}">
                        <span class="yt-dur-badge">${v.duration || 'Video'}</span>
                    </div>
                    <div class="game-info">
                        <div class="game-title" title="${v.title}">${v.title}</div>
                        <div class="game-meta">
                            <span>${v.channel || 'YouTube'}</span>
                            <span>${v.age || ''}</span>
                        </div>
                        <div class="game-actions" style="margin-top:10px;">
                            ${favBtn}
                            <a href="https://www.youtube.com/watch?v=${v.id}" target="_blank" class="btn btn-sm btn-secondary">Xem ↗</a>
                        </div>
                    </div>
                </div>`;
            });
            container.innerHTML = html;
        }

        function openImportPlaylistModal() {
            document.getElementById('import-playlist-url').value = '';
            document.getElementById('import-playlist-title').value = '';
            document.getElementById('import-playlist-status').style.display = 'none';
            document.getElementById('btn-submit-import-pl').disabled = false;
            openModal('modal-import-playlist');
        }

        async function submitImportPlaylist() {
            const url = document.getElementById('import-playlist-url').value.trim();
            const customTitle = document.getElementById('import-playlist-title').value.trim();
            if (!url) {
                alert('Vui lòng dán Link hoặc ID Playlist YouTube!');
                return;
            }

            const statusEl = document.getElementById('import-playlist-status');
            const statusText = document.getElementById('import-playlist-status-text');
            const btnSubmit = document.getElementById('btn-submit-import-pl');

            statusEl.style.display = 'block';
            statusText.innerText = '⏳ Đang quét danh sách và lấy toàn bộ video từ YouTube...';
            btnSubmit.disabled = true;

            try {
                const res = await fetch('/api/youtube/playlists/import', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url, custom_title: customTitle})
                });
                const data = await res.json();
                btnSubmit.disabled = false;

                if (data.ok) {
                    closeModal('modal-import-playlist');
                    showToast(`🎉 ${data.message}`);
                    ytPlaylists = data.playlists || [];
                    currentYtTab = data.title;
                    renderYouTubePlaylists();
                    
                    // Render the imported videos directly
                    const titleEl = document.getElementById('yt-current-title');
                    const countEl = document.getElementById('yt-video-count');
                    titleEl.innerText = `📺 Playlist: ${data.title}`;
                    countEl.innerText = `${data.count} video`;
                    ytVideos = data.videos || [];
                    renderYouTubeGrid(ytVideos, false);
                } else {
                    statusText.innerText = '❌ ' + (data.error || 'Lỗi khi nhập playlist');
                }
            } catch (e) {
                btnSubmit.disabled = false;
                statusText.innerText = '❌ Lỗi kết nối: ' + e;
            }
        }

        function openAddPlaylistModal() {
            document.getElementById('new-playlist-name').value = '';
            openModal('modal-add-playlist');
        }

        async function submitAddPlaylist() {
            const name = document.getElementById('new-playlist-name').value.trim();
            if (!name) return;
            try {
                const res = await fetch('/api/youtube/playlists/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-add-playlist');
                    showToast(`Đã thêm playlist ${name}!`);
                    ytPlaylists = data.playlists || [];
                    selectYouTubePlaylist(name);
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function deletePlaylist(e, name) {
            e.stopPropagation();
            if (!confirm(`Bạn có chắc muốn xóa playlist "${name}"?`)) return;
            try {
                const res = await fetch('/api/youtube/playlists/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name: name})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(`Đã xóa playlist ${name}!`);
                    ytPlaylists = data.playlists || [];
                    selectYouTubePlaylist('trending');
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function addToFavorites(id, titleEnc, channelEnc, durEnc, thumbEnc) {
            const video = {
                id: id,
                title: decodeURIComponent(titleEnc),
                channel: decodeURIComponent(channelEnc),
                duration: decodeURIComponent(durEnc),
                thumb: decodeURIComponent(thumbEnc)
            };
            try {
                const res = await fetch('/api/youtube/favorites/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({video: video})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã lưu video vào Yêu thích!');
                    loadYouTubeInit();
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function removeFromFavorites(id) {
            try {
                const res = await fetch('/api/youtube/favorites/remove', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: id})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã xóa khỏi Yêu thích!');
                    loadYouTubeVideos('favorites');
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        function addCurrentSearchAsPlaylist() {
            const q = document.getElementById('yt-search-input').value.trim();
            if (!q) return;
            document.getElementById('new-playlist-name').value = q;
            submitAddPlaylist();
        }

        async function clearYouTubeCache() {
            if (!confirm('Dọn dẹp toàn bộ bộ nhớ đệm ảnh thumbnail YouTube trên thẻ nhớ?')) return;
            try {
                const res = await fetch('/api/youtube/cache/clear', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã dọn dẹp cache YouTube!');
                    loadStorageStatus();
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        // ==================== MODALS & HELPERS ====================
        function openRenameModal(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            selectedGame = {system: sys, filename: fn};
            document.getElementById('rename-old').value = fn;
            document.getElementById('rename-new').value = fn;
            openModal('modal-rename');
        }

        async function submitRename() {
            if (!selectedGame) return;
            const newName = document.getElementById('rename-new').value.trim();
            if (!newName) return;
            try {
                const res = await fetch('/api/rename', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        system: selectedGame.system,
                        old_filename: selectedGame.filename,
                        new_filename: newName
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-rename');
                    showToast(data.message || 'Đổi tên thành công!');
                    selectSystem(selectedGame.system);
                } else { alert('Lỗi: ' + (data.error || 'Không thể đổi tên')); }
            } catch (e) { alert('Lỗi kết nối: ' + e); }
        }

        function openMoveModal(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            selectedGame = {system: sys, filename: fn};
            document.getElementById('move-game').value = `${fn} (${sys})`;
            const sel = document.getElementById('move-target-sys');
            let opts = '';
            allSystems.forEach(s => {
                if (s.dir !== sys) opts += `<option value="${s.dir}">${s.name} (${s.dir})</option>`;
            });
            sel.innerHTML = opts;
            openModal('modal-move');
        }

        async function submitMove() {
            if (!selectedGame) return;
            const targetSys = document.getElementById('move-target-sys').value;
            if (!targetSys) return;
            try {
                const res = await fetch('/api/move', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        from_system: selectedGame.system,
                        to_system: targetSys,
                        filename: selectedGame.filename
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-move');
                    showToast(data.message || 'Chuyển hệ máy thành công!');
                    loadSystems();
                } else { alert('Lỗi: ' + (data.error || 'Không thể chuyển')); }
            } catch (e) { alert('Lỗi kết nối: ' + e); }
        }

        async function deleteGame(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            if (!confirm(`Bạn có chắc chắn muốn xóa game "${fn}" khỏi thẻ nhớ?`)) return;
            try {
                const res = await fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({system: sys, filename: fn, delete_art: true})
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(`Đã xóa ${fn}`);
                    selectSystem(sys);
                } else { alert('Lỗi: ' + (data.error || 'Không thể xóa')); }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        function openScrapeModal(sys, fnEnc) {
            const fn = decodeURIComponent(fnEnc);
            selectedGame = {system: sys, filename: fn};
            document.getElementById('scrape-query').value = cleanRomTitle(fn);
            document.getElementById('scrape-results').innerHTML = '';
            openModal('modal-scrape');
            executeScrapeSearch();
        }

        function cleanRomTitle(fn) {
            let base = fn.replace(/\.[^/.]+$/, "");
            base = base.replace(/^\d+\s*[-–—.]\s*/, "");
            return base.replace(/\(.*?\)|\[.*?\]/g, "").trim();
        }

        async function executeScrapeSearch() {
            if (!selectedGame) return;
            const q = document.getElementById('scrape-query').value.trim();
            const resBox = document.getElementById('scrape-results');
            resBox.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-sub);">Đang tìm ảnh...</div>';
            try {
                const res = await fetch(`/api/scrape/search?system=${encodeURIComponent(selectedGame.system)}&query=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.ok && data.candidates && data.candidates.length > 0) {
                    let html = '';
                    data.candidates.forEach(c => {
                        html += `<div class="game-card" style="cursor:pointer;" onclick="applyScrapedArt('${encodeURIComponent(c.url)}')">
                            <div class="art-box"><img src="${c.url}" loading="lazy" alt="Boxart"></div>
                            <div style="padding:6px; font-size:10px; color:var(--text-sub); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${c.type || 'Boxart'}</div>
                        </div>`;
                    });
                    resBox.innerHTML = html;
                } else {
                    resBox.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-sub);">Không tìm thấy ảnh. Hãy thử nhập từ khóa khác hoặc dán link bên dưới.</div>';
                }
            } catch (e) {
                resBox.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:20px; color:#ef4444;">Lỗi tìm ảnh: ' + e + '</div>';
            }
        }

        async function applyScrapedArt(urlEnc) {
            if (!selectedGame) return;
            const url = decodeURIComponent(urlEnc);
            try {
                const res = await fetch('/api/scrape/auto', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        system: selectedGame.system,
                        filename: selectedGame.filename,
                        query: document.getElementById('scrape-query').value.trim(),
                        fast: false
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    closeModal('modal-scrape');
                    showToast('Đã gán ảnh bìa thành công!');
                    selectSystem(selectedGame.system);
                } else { alert('Lỗi gán ảnh: ' + (data.error || 'Thất bại')); }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function submitDirectArtUrl() {
            const url = document.getElementById('scrape-direct-url').value.trim();
            if (!url || !selectedGame) return;
            applyScrapedArt(encodeURIComponent(url));
        }

        function openGoogleImageSearch() {
            if (!selectedGame) return;
            const q = document.getElementById('scrape-query').value.trim() + ' ' + selectedGame.system + ' boxart cover';
            window.open('https://www.google.com/search?tbm=isch&q=' + encodeURIComponent(q), '_blank');
        }

        function handleUploadRomClick() {
            document.getElementById('rom-file-input-direct').click();
        }

        async function handleDirectRomFiles(e) {
            const files = e.target.files;
            if (!files || files.length === 0 || !currentSystem) return;
            for (let i = 0; i < files.length; i++) {
                const f = files[i];
                showToast(`Đang tải lên ${f.name}...`);
                try {
                    await fetch(`/api/upload_rom?system=${encodeURIComponent(currentSystem)}&filename=${encodeURIComponent(f.name)}`, {
                        method: 'POST',
                        body: f
                    });
                } catch (err) {}
            }
            showToast('Tải ROMs thành công!');
            selectSystem(currentSystem);
        }

        // ==================== SAVE & CHEATS MODAL ====================
        function openSavesCheatsModal(tab = 'saves') {
            switchSavesCheatsTab(tab);
            openModal('modal-saves-cheats');
        }

        function switchSavesCheatsTab(tab) {
            ['saves', 'cheats', 'logs'].forEach(t => {
                const btn = document.getElementById(`tab-btn-${t}`);
                const c = document.getElementById(`tab-content-${t}`);
                if (btn) btn.className = (t === tab) ? 'btn btn-sm' : 'btn btn-sm btn-secondary';
                if (c) c.style.display = (t === tab) ? 'block' : 'none';
            });
            if (tab === 'saves') loadSavesData();
            else if (tab === 'cheats') loadCheatsData();
        }

        async function loadSavesData() {
            try {
                const res = await fetch('/api/saves');
                const data = await res.json();
                if (data.ok) {
                    document.getElementById('saves-stats-text').innerText = `Tổng cộng ${data.stats ? data.stats.total_files : 0} file save trên thẻ nhớ.`;
                    const box = document.getElementById('backups-list-table');
                    if (!data.backups || data.backups.length === 0) {
                        box.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-sub); font-size:12px;">Chưa có bản sao lưu nào. Hãy bấm "+ Tạo bản sao lưu mới" ở trên!</div>';
                        return;
                    }
                    let html = '';
                    data.backups.forEach(b => {
                        html += `<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 10px; border-bottom:1px solid var(--border); font-size:12px;">
                            <div>
                                <strong style="color:#38bdf8;">${b.created_at || b.filename}</strong>
                                <span style="color:var(--text-sub); margin-left:8px;">(${b.size_str})</span>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <a href="/api/saves/download?file=${encodeURIComponent(b.filename)}" class="btn btn-sm btn-secondary" download>Tải về (.zip)</a>
                                <button class="btn btn-sm btn-green" onclick="restoreSaveBackupWeb('${b.filename}')">Khôi phục</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteSaveBackupWeb('${b.filename}')">Xóa</button>
                            </div>
                        </div>`;
                    });
                    box.innerHTML = html;
                }
            } catch (e) {}
        }

        async function createSaveBackupWeb() {
            try {
                const res = await fetch('/api/saves/backup', {method: 'POST'});
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã tạo bản sao lưu thành công!');
                    loadSavesData();
                }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function restoreSaveBackupWeb(fn) {
            if (!confirm(`Khôi phục dữ liệu từ bản sao lưu "${fn}"?`)) return;
            try {
                const res = await fetch('/api/saves/restore', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: fn})
                });
                const data = await res.json();
                if (data.ok) showToast(data.message || 'Khôi phục thành công!');
                else alert('Lỗi: ' + data.error);
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function deleteSaveBackupWeb(fn) {
            if (!confirm(`Xóa bản sao lưu "${fn}"?`)) return;
            try {
                const res = await fetch('/api/saves/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filename: fn})
                });
                const data = await res.json();
                if (data.ok) { showToast('Đã xóa bản sao lưu!'); loadSavesData(); }
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function loadCheatsData() {
            try {
                const res = await fetch('/api/cheats/status');
                const data = await res.json();
                if (data.ok && data.status) {
                    document.getElementById('cheats-status-box').innerHTML = `Đã cài đặt: <strong>${data.status.installed_count}</strong> file cheat trên máy. Tổng kho Libretro: <strong>${data.status.total_available}</strong> game hỗ trợ cheat.`;
                }
            } catch (e) {}
        }

        async function downloadCheatsWeb(mode) {
            try {
                const res = await fetch('/api/cheats/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: mode})
                });
                const data = await res.json();
                if (data.ok) showToast(data.message || 'Đang tải kho cheat...');
            } catch (e) { alert('Lỗi: ' + e); }
        }

        async function sendLogTelegramWeb() {
            try {
                const res = await fetch('/api/logs/send-telegram', {method: 'POST'});
                const data = await res.json();
                if (data.ok) showToast('Đã gửi nhật ký lên Telegram tác giả!');
                else alert('Lỗi: ' + data.error);
            } catch (e) { alert('Lỗi: ' + e); }
        }

        
        // ==================== AI CHATBOT ====================
        const RETROHUB_SYSTEM_PROMPT = `Bạn là trợ lý AI chuyên gia kỹ thuật điều hành hệ sinh thái RetroHub và thiết bị máy chơi game cầm tay (Linux aarch64, Kernel 4.9, Shell BusyBox/Ash).
Bạn tương tác với người dùng qua Web Game Manager và có khả năng đề xuất các câu lệnh shell để người dùng bấm chạy trực tiếp trên máy (qua nút bấm thực thi).

QUY TẮC LÀM VIỆC CỐT LÕI (BẮT BUỘC TUÂN THỦ 100%):
1. ĐỊNH DẠNG KHỐI LỆNH: Mọi câu lệnh cần thực thi BẮT BUỘC PHẢI đặt trong block code markdown:
\`\`\`bash
câu_lệnh_ở_đây
\`\`\`
hoặc [CMD]câu_lệnh_ở_đây[/CMD].
Hệ thống web sẽ tự động trích xuất và tạo nút bấm ⚡ Thực thi riêng cho từng lệnh.

2. CÂU LỆNH ĐƠN GIẢN, TÁCH RỜI & AN TOÀN:
- Mỗi block code chỉ chứa DUY NHẤT 1 câu lệnh (hoặc 1 lệnh đơn gọn gàng). Tránh gom quá nhiều lệnh phức tạp nối bằng && hay ; trong cùng một block để người dùng dễ quan sát output từng bước.
- KHÔNG dùng markdown styling (như *tên_file* hay **bold**) bên trong block code.
- Môi trường là Linux BusyBox ash: Sử dụng các lệnh tiêu chuẩn (ls, cat, grep, find, sed, rm, cp, mv, ps, df, free, kill...).
- Python 3 trên máy KHÔNG có module SSL: Nếu cần gọi mạng HTTPS, dùng curl -s -k. Để chỉnh sửa file XML/JSON phức tạp an toàn, có thể dùng python3 -c "import xml.etree.ElementTree as ET..." hoặc python3 -c "import json...".

3. QUY TRÌNH CHẨN ĐOÁN LỖI & RÚT GỌN THỜI GIAN DEBUG (FAST INVESTIGATION):
- KHI NHẬN ĐƯỢC LOG (từ nút 'Quét log lỗi' hoặc lệnh tail/cat): Đọc ngay các dòng Error/Exception/Panic, xác định trực diện nguyên nhân gốc rễ và đưa NGAY LẬP TỨC câu lệnh khắc phục trong block code, kèm lời giải thích ngắn gọn (tối đa 2-3 câu). Không lan man.
- TUYỆT ĐỐI KHÔNG ĐOÁN MÒ: Không tự suy diễn thông số phần cứng (như độ phân giải màn hình, CPU, RAM), đường dẫn file hay cấu hình khi chưa rõ. Hãy đọc kỹ thông tin được cung cấp từ nút "Gửi info" hoặc "Quét log lỗi", hoặc chủ động gửi 1 câu lệnh gom chẩn đoán nhanh.
- Luôn trả lời bằng TIẾNG VIỆT, ngắn gọn, lịch sự, đi thẳng vào giải pháp kỹ thuật.`;

        let aiChatHistory = [
            { role: "system", content: RETROHUB_SYSTEM_PROMPT }
        ];

        function strToBase64(str) {
            try {
                return btoa(unescape(encodeURIComponent(str)));
            } catch (e) {
                return btoa(str);
            }
        }

        function base64ToStr(b64) {
            try {
                return decodeURIComponent(escape(atob(b64)));
            } catch (e) {
                return atob(b64);
            }
        }

        function appendChatMessage(role, text, skipEscape = false, isCard = false) {
            const container = document.getElementById('chat-messages');
            if (!container) return;
            
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
            
            const bubble = document.createElement('div');
            bubble.style.maxWidth = '85%';
            bubble.style.fontSize = '14px';
            bubble.style.lineHeight = '1.4';
            bubble.style.whiteSpace = 'pre-wrap';
            bubble.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            
            if (isCard) {
                bubble.style.background = 'transparent';
                bubble.style.padding = '0';
                bubble.style.border = 'none';
                bubble.style.boxShadow = 'none';
            } else if (role === 'user') {
                bubble.style.background = '#0284c7';
                bubble.style.color = '#fff';
                bubble.style.padding = '8px 12px';
                bubble.style.borderRadius = '12px';
                bubble.style.borderBottomRightRadius = '4px';
                bubble.style.border = '1px solid #0369a1';
            } else {
                bubble.style.background = '#1e293b';
                bubble.style.color = '#f8fafc';
                bubble.style.padding = '8px 12px';
                bubble.style.borderRadius = '12px';
                bubble.style.borderBottomLeftRadius = '4px';
                bubble.style.border = '1px solid #334155';
            }
            
            if (skipEscape) {
                bubble.innerHTML = text;
                wrapper.appendChild(bubble);
                container.appendChild(wrapper);
                setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
                return;
            }

            // BƯỚC 1: Trích xuất các block lệnh [CMD]...[/CMD] và ```bash ... ``` TRƯỚC KHI escape HTML / Markdown
            let cmdBlocks = [];
            let processedText = text;
            
            processedText = processedText.replace(/\[CMD\]([\s\S]*?)\[\/CMD\]|```(?:[a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/gi, (match, cmd1, cmd2) => {
                const rawCmd = (cmd1 || cmd2 || '').trim();
                if (!rawCmd) return '';
                const token = `__CMD_BLOCK_TOKEN_${cmdBlocks.length}__`;
                cmdBlocks.push(rawCmd);
                return token;
            });

            // BƯỚC 2: Trích xuất inline code `...`
            let inlineCodes = [];
            processedText = processedText.replace(/`([^`\n]+)`/g, (match, codeText) => {
                const token = `__INLINE_CODE_TOKEN_${inlineCodes.length}__`;
                inlineCodes.push(codeText);
                return token;
            });

            // BƯỚC 3: Escape HTML cho phần văn bản thông thường
            let safeText = processedText
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // BƯỚC 4: Format Markdown cơ bản (chỉ trên text an toàn)
            safeText = safeText.replace(/\$\\rightarrow\$/g, '→').replace(/\$\\leftarrow\$/g, '←');
            safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            safeText = safeText.replace(/\*(.*?)\*/g, '<em>$1</em>');

            // BƯỚC 5: Khôi phục inline code an toàn
            inlineCodes.forEach((code, idx) => {
                const escapedCode = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                const html = `<code style="background: rgba(0,0,0,0.3); padding: 2px 5px; border-radius: 4px; font-size: 13px; color: #38bdf8; font-family: monospace;">${escapedCode}</code>`;
                safeText = safeText.replace(`__INLINE_CODE_TOKEN_${idx}__`, html);
            });

            // BƯỚC 6: Khôi phục các Block lệnh với nút Thực thi (giữ 100% RAW command trong Base64)
            let allCmds = [];
            cmdBlocks.forEach((rawCmd, idx) => {
                allCmds.push(rawCmd);
                const b64Cmd = strToBase64(rawCmd);
                const escapedDisplay = rawCmd.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                
                const blockHtml = `<div style="display: flex; align-items: center; justify-content: space-between; background: #070a13; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 8px 6px 10px; margin: 6px 0; gap: 8px; max-width: 100%;">
                    <code style="font-family: monospace; color: #38bdf8; font-size: 13px; line-height: 1.4; white-space: pre-wrap; word-break: break-all; flex: 1;">${escapedDisplay}</code>
                    <button onclick="executeAiCommand(event, '${b64Cmd}')" title="Thực thi lệnh này" style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); cursor: pointer; padding: 5px 8px; border-radius: 4px; color: #34d399; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; outline: none; transition: all 0.2s;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    </button>
                </div>`;
                safeText = safeText.replace(`__CMD_BLOCK_TOKEN_${idx}__`, blockHtml);
            });

            // BƯỚC 7: Nút Chạy tất cả nếu có nhiều hơn 1 lệnh
            if (cmdBlocks.length > 1) {
                const b64Cmds = strToBase64(JSON.stringify(allCmds));
                safeText += `<div style="display: flex; justify-content: flex-end; margin-top: 6px;">
                    <div style="display: inline-flex; align-items: center; background: #070a13; border: 1px solid rgba(234, 179, 8, 0.35); border-radius: 6px; padding: 3px 6px 3px 10px; gap: 8px;">
                        <span style="font-family: monospace; color: #facc15; font-size: 12px; font-weight: 600;">⚡ Chạy tất cả (${cmdBlocks.length} lệnh)</span>
                        <button onclick="executeAllAiCommands(event, '${b64Cmds}')" title="Thực thi tất cả theo thứ tự" style="background: rgba(234, 179, 8, 0.15); border: none; cursor: pointer; padding: 3px 6px; border-radius: 4px; color: #facc15; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; outline: none; transition: all 0.2s;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                        </button>
                    </div>
                </div>`;
            }

            bubble.innerHTML = safeText;
            wrapper.appendChild(bubble);
            container.appendChild(wrapper);
            
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 50);
        }

        async function executeAllAiCommands(e, b64Cmds) {
            const cmds = JSON.parse(base64ToStr(b64Cmds));
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            
            let combinedOutput = "";
            for(let i=0; i<cmds.length; i++) {
                const cmd = cmds[i];
                try {
                    const res = await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: cmd})
                    });
                    const data = await res.json();
                    const rawOut = (data.output || '').trim();
                    const code = (typeof data.code !== 'undefined') ? data.code : 0;
                    const outLog = rawOut || (code === 0 ? '(Thành công - Không có output)' : `(Mã lỗi: ${code})`);
                    combinedOutput += `--- [${i+1}/${cmds.length}] ${cmd} (Exit: ${code}) ---\n${outLog}\n\n`;
                } catch(err) {
                    combinedOutput += `--- [${i+1}/${cmds.length}] ${cmd} (Lỗi) ---\n${err.message}\n\n`;
                }
            }
            
            btn.innerHTML = '✅';
            btn.style.background = 'rgba(56, 189, 248, 0.15)';
            btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            btn.style.color = '#38bdf8';
            
            const systemPromptText = `[System Execution Result]\n${combinedOutput.trim()}`;
            const safeCombined = combinedOutput.trim().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #facc15; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                    <span style="display: flex; align-items: center; gap: 6px;">
                        <span>⚡</span> Đã thực thi ${cmds.length} lệnh
                    </span>
                    <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem log)</span>
                </summary>
                <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeCombined}</div>
            </details>`;
            appendChatMessage('user', htmlText, true, true);
            aiChatHistory.push({ role: 'user', content: systemPromptText });
            
            document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
            document.getElementById('chat-submit-btn').disabled = true;
            doHeadlessAiFetch();
        }


        async function sendDeviceInfoToAI() {
            const btn = document.getElementById('btn-send-info');
            if(btn) { btn.disabled = true; btn.innerHTML = '⏳ Đang quét...'; }
            
            const cmd = [
                'echo "=== [1] THÔNG TIN PHẦN CỨNG & HỆ ĐIỀU HÀNH ==="',
                'uname -a',
                'cat /proc/device-tree/model 2>/dev/null && echo ""',
                'echo "=== [2] MÀN HÌNH & ĐỘ PHÂN GIẢI THỰC TẾ ==="',
                'if [ -f /sys/class/graphics/fb0/virtual_size ]; then echo "Framebuffer resolution: $(cat /sys/class/graphics/fb0/virtual_size)"; elif which fbset >/dev/null 2>&1; then fbset | grep -i "geometry"; fi',
                'echo "=== [3] RAM & BỘ NHỚ DISK ==="',
                'free -m',
                'df -h | grep -E "Filesystem|/mnt/SDCARD|/tmp|rootfs"',
                'echo "=== [4] GIẢ LẬP ĐÃ CÀI (/mnt/SDCARD/Emus) ==="',
                'ls -d /mnt/SDCARD/Emus/*/ 2>/dev/null',
                'echo "=== [5] CORES RETROARCH (.so) ==="',
                'ls /mnt/SDCARD/RetroArch/.retroarch/cores/*.so 2>/dev/null | awk -F/ "{print \\$NF}"',
                'echo "=== [6] APPS & GAME PORTS (/mnt/SDCARD/Apps & Data/ports) ==="',
                'ls -d /mnt/SDCARD/Apps/*/ 2>/dev/null',
                'ls -d /mnt/SDCARD/Data/ports/*/ 2>/dev/null',
                'echo "=== [7] THƯ MỤC ROMS HIỆN CÓ ==="',
                'ls -d /mnt/SDCARD/Roms/*/ 2>/dev/null',
                'echo "=== [8] CẤU TRÚC ỨNG DỤNG RETROHUB ==="',
                'find /mnt/SDCARD/Apps/RetroHub -maxdepth 2 2>/dev/null | grep -v "/\\._" | head -n 35',
                'echo "=== [9] CÁC FILE LOG THỰC TẾ TRÊN THIẾT BỊ ==="',
                'find /mnt/SDCARD /tmp -maxdepth 5 -type f 2>/dev/null | grep -iE "\\.(log|out)$|loi\\.txt$" | grep -v "\\._" | head -n 30'
            ].join("; echo ''; ");
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                const outLog = data.output || '(Lỗi đọc dữ liệu)';
                const safeLog = outLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #34d399; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span>📡</span> Đã nạp cấu hình & giả lập máy cho AI
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem chi tiết)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeLog}</div>
                </details>`;
                
                appendChatMessage('user', htmlText, true, true);
                
                const plainText = 'Đây là toàn bộ thông tin phần cứng (model máy, độ phân giải màn hình thực tế, RAM, Disk), danh sách giả lập, cores RetroArch, game ports, cấu trúc thư mục và các file log thực tế trên máy:\n```\n' + outLog + '\n```\nHãy ghi nhớ các thông số này (đặc biệt là độ phân giải màn hình thực tế, danh sách giả lập và log) để tư vấn và đưa ra câu lệnh chính xác 100%.';
                aiChatHistory.push({ role: 'user', content: plainText });
                
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                
                doHeadlessAiFetch();
            } catch (e) {
                alert('Lỗi lấy thông tin: ' + e.message);
            } finally {
                if(btn) { btn.disabled = false; btn.innerHTML = '📡 Gửi info'; }
            }
        }

        async function quickDebugLogsAI() {
            const btn = document.getElementById('btn-quick-debug');
            if (btn) { btn.disabled = true; btn.innerHTML = '⏳ Đang quét log...'; }

            const cmd = [
                'echo "=== [1] LOGS VỪA THAY ĐỔI GẦN ĐÂY (< 30 PHÚT) ==="',
                'find /mnt/SDCARD /tmp -maxdepth 5 -type f -mmin -30 2>/dev/null | grep -iE "\\.(log|out|txt)$" | grep -v "/\\._" | while read f; do echo "--- FILE: \\$f ---"; tail -n 25 "\\$f"; echo ""; done',
                'echo "=== [2] RETROHUB LOG (25 DÒNG CUỐI) ==="',
                'if [ -f /mnt/SDCARD/RetroHub/logs/retrohub.log ]; then tail -n 25 /mnt/SDCARD/RetroHub/logs/retrohub.log; elif [ -f /mnt/SDCARD/Apps/RetroHub/logs/retrohub.log ]; then tail -n 25 /mnt/SDCARD/Apps/RetroHub/logs/retrohub.log; else echo "(Không có file log)"; fi',
                'echo "=== [3] RETROARCH LOG (25 DÒNG CUỐI) ==="',
                'if [ -f /mnt/SDCARD/RetroArch/.retroarch/logs/retroarch.log ]; then tail -n 25 /mnt/SDCARD/RetroArch/.retroarch/logs/retroarch.log; elif [ -f /mnt/SDCARD/RetroArch/retroarch.log ]; then tail -n 25 /mnt/SDCARD/RetroArch/retroarch.log; else echo "(Không có file log)"; fi',
                'echo "=== [4] LOGS GAME PORTS / PORTMASTER (NẾU CÓ) ==="',
                'find /mnt/SDCARD/Data/ports /mnt/SDCARD/roms/ports -maxdepth 3 -type f \\( -name "*.log" -o -name "log.txt" -o -name "StardewValley.log" \\) 2>/dev/null | while read pf; do echo "--- PORT LOG: \\$pf ---"; tail -n 20 "\\$pf"; echo ""; done',
                'echo "=== [5] DMESG KERNEL WARNINGS & ERRORS ==="',
                'dmesg 2>/dev/null | grep -iE "error|fail|panic|oom|segfault|killed|fault" | tail -n 20 || echo "(Không có)"'
            ].join("; echo ''; ");

            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                const outLog = data.output || '(Lỗi đọc dữ liệu log)';
                const safeLog = outLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

                const htmlText = `<details style="background: #0f172a; border: 1px solid #7c3aed; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #c084fc; background: #1e1b4b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span>🔍</span> Tổng hợp nhật ký lỗi hệ thống & giả lập gần nhất
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem chi tiết)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 240px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #7c3aed;">${safeLog}</div>
                </details>`;

                appendChatMessage('user', htmlText, true, true);

                const plainText = 'Dưới đây là toàn bộ các file log vừa thay đổi gần đây, log RetroHub, RetroArch, PortMaster và dmesg kernel trên thiết bị:\n```\n' + outLog + '\n```\nHãy phân tích nhanh nguyên nhân lỗi từ log trên và đưa ra ngay câu lệnh khắc phục ngắn gọn, chuẩn xác.';
                aiChatHistory.push({ role: 'user', content: plainText });

                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;

                doHeadlessAiFetch();
            } catch (e) {
                alert('Lỗi chẩn đoán log: ' + e.message);
            } finally {
                if (btn) { btn.disabled = false; btn.innerHTML = '🔍 Quét log lỗi'; }
            }
        }

        async function executeAiCommand(e, b64Cmd) {
            const cmd = base64ToStr(b64Cmd);
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '⏳';
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                
                const rawOut = (data.output || '').trim();
                const code = (typeof data.code !== 'undefined') ? data.code : 0;
                let displayLog = rawOut;
                if (!displayLog) {
                    if (code === 0) {
                        displayLog = '✓ Lệnh đã thực thi thành công (Không có text xuất ra terminal / Exit code: 0)';
                    } else {
                        displayLog = `⚠️ Lệnh hoàn tất với mã lỗi (Exit code: ${code})`;
                    }
                }
                const safeLog = displayLog.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                
                const htmlText = `<details style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; overflow: hidden; min-width: 280px; max-width: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                    <summary style="cursor: pointer; padding: 7px 12px; font-size: 12.5px; font-weight: 600; color: #38bdf8; background: #1e293b; display: flex; align-items: center; justify-content: space-between; user-select: none; outline: none; gap: 8px;">
                        <span style="display: flex; align-items: center; gap: 6px;">
                            <span style="color: #34d399;">✓</span> Kết quả thực thi
                        </span>
                        <span style="font-size: 11px; color: #94a3b8; font-weight: normal;">(Nhấn xem log)</span>
                    </summary>
                    <div style="padding: 10px 12px; background: #070a13; font-family: monospace; font-size: 12px; line-height: 1.45; white-space: pre-wrap; word-break: break-all; max-height: 220px; overflow-y: auto; color: #e2e8f0; border-top: 1px solid #1e293b;">${safeLog}</div>
                </details>`;
                
                const plainText = `Đã thực thi lệnh trên TrimUI: \`${cmd}\`\nKết quả:\n\`\`\`\n${rawOut || '(Lệnh hoàn tất - Không có output)'}\n\`\`\`\nExit code: ${code}`;
                
                btn.innerHTML = '✅';
                btn.style.background = 'rgba(56, 189, 248, 0.15)';
                btn.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                btn.style.color = '#38bdf8';
                
                // Add to chat and send to AI
                appendChatMessage('user', htmlText, true, true);
                aiChatHistory.push({ role: 'user', content: plainText });
                
                // Send headless request
                document.getElementById('chat-submit-btn').innerHTML = 'Đang nghĩ... ⏳';
                document.getElementById('chat-submit-btn').disabled = true;
                
                doHeadlessAiFetch();
                
            } catch(err) {
                alert('Lỗi chạy lệnh: ' + err.message);
                btn.disabled = false;
                btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
            }
        }
        
        async function doHeadlessAiFetch() {
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: 'auto', messages: aiChatHistory })
                });
                if (!res.ok) throw new Error('Mã lỗi API: ' + res.status);
                const data = await res.json();
                if (data.error) {
                    const errMsg = typeof data.error === 'object' ? (data.error.message || JSON.stringify(data.error)) : data.error;
                    throw new Error(errMsg);
                }
                if (data.choices && data.choices.length > 0) {
                    const reply = data.choices[0].message.content;
                    appendChatMessage('assistant', reply);
                    aiChatHistory.push({ role: 'assistant', content: reply });
                } else {
                    appendChatMessage('assistant', 'Lỗi: Phản hồi từ AI bị rỗng.');
                }
            } catch (err) {
                appendChatMessage('assistant', '⚠️ Lỗi khi phản hồi: ' + err.message);
            } finally {
                const btn = document.getElementById('chat-submit-btn');
                btn.disabled = false;
                btn.textContent = 'Gửi ✈️';
            }
        }

        function showSystemPrompt() {
            const sysPrompt = aiChatHistory.length > 0 ? aiChatHistory[0].content : "Không tìm thấy System Prompt.";
            appendChatMessage('assistant', `**Đây là toàn bộ System Prompt hiện tại đang nạp cho AI:**

\`\`\`text
${sysPrompt}
\`\`\``);
        }

        function clearAIChat() {
            if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện?')) return;
            
            aiChatHistory = [{ role: "system", content: RETROHUB_SYSTEM_PROMPT }];
            const container = document.getElementById('chat-messages');
            if (container) {
                container.innerHTML = `
                    <div style="display:flex; justify-content:flex-start;">
                        <div style="background:#1e293b; color:#f8fafc; padding:10px 14px; border-radius:12px; border-bottom-left-radius:4px; max-width:85%; font-size:14.5px; line-height:1.45; border:1px solid #334155; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                            Đã dọn dẹp lịch sử trò chuyện. Tôi có thể giúp gì cho bạn tiếp theo?
                        </div>
                    </div>
                `;
            }
        }

        async function sendChatMessage(e) {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;
            
            const btn = document.getElementById('chat-submit-btn');
            input.value = '';
            input.disabled = true;
            btn.disabled = true;
            btn.innerHTML = 'Đang nghĩ... <span style="font-size:12px;">⏳</span>';
            
            appendChatMessage('user', text);
            aiChatHistory.push({ role: 'user', content: text });
            
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        model: 'auto',
                        messages: aiChatHistory
                    })
                });
                
                if (!res.ok) {
                    throw new Error('Mã lỗi API: ' + res.status);
                }
                
                const data = await res.json();
                if (data.error) {
                    const errMsg = typeof data.error === 'object' ? (data.error.message || JSON.stringify(data.error)) : data.error;
                    throw new Error(errMsg);
                }
                if (data.choices && data.choices.length > 0) {
                    const reply = data.choices[0].message.content;
                    appendChatMessage('assistant', reply);
                    aiChatHistory.push({ role: 'assistant', content: reply });
                } else {
                    appendChatMessage('assistant', 'Lỗi: Phản hồi từ AI bị rỗng.');
                }
            } catch (err) {
                appendChatMessage('assistant', '⚠️ Không thể kết nối tới máy chủ AI. Chi tiết lỗi: ' + err.message);
                // Remove the user message from history so they can try again if they want, or just let it be
            } finally {
                input.disabled = false;
                btn.disabled = false;
                btn.textContent = 'Gửi ✈️';
                input.focus();
            }
        }


        // ==================== STREAM JS LOGIC ====================
        function openStreamNewTab() {
            window.open('http://' + window.location.hostname + ':8088', '_blank');
        }

        async function checkStreamStatus() {
            const statusBadge = document.getElementById('stream-status-badge');
            const toggleBtn = document.getElementById('btn-stream-toggle');
            const newTabBtn = document.getElementById('btn-stream-newtab');
            if (!statusBadge || !toggleBtn) return;
            
            try {
                const res = await fetch('/api/run_cmd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: 'ps | grep "python.*streamer.py" | grep -v grep'})
                });
                const data = await res.json();
                const out = data.output || '';
                if (out.includes('streamer.py')) {
                    statusBadge.textContent = '🟢 Đang chạy';
                    statusBadge.style.color = '#10b981';
                    toggleBtn.innerHTML = '🛑 Tắt Stream';
                    toggleBtn.className = 'btn btn-danger';
                    if (newTabBtn) newTabBtn.style.display = 'inline-flex';
                } else {
                    statusBadge.textContent = '🔴 Đã tắt';
                    statusBadge.style.color = '#ef4444';
                    toggleBtn.innerHTML = '▶️ Bật Stream ngay';
                    toggleBtn.className = 'btn btn-secondary';
                    if (newTabBtn) newTabBtn.style.display = 'none';
                }
            } catch(e) {
                statusBadge.textContent = '⚠️ Lỗi kiểm tra';
            }
        }

        async function toggleScreenStream() {
            const toggleBtn = document.getElementById('btn-stream-toggle');
            if (!toggleBtn) return;
            
            const isRunning = toggleBtn.innerHTML.includes('Tắt');
            toggleBtn.disabled = true;
            toggleBtn.innerHTML = '⏳ Đang xử lý...';
            
            try {
                if (isRunning) {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'kill -9 $(ps | awk "/streamer\.py/ {print $1}")'})
                    });
                } else {
                    await fetch('/api/run_cmd', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cmd: 'nohup /mnt/SDCARD/System/bin/python3 /mnt/SDCARD/Apps/RetroHub/streamer.py > /dev/null 2>&1 &'})
                    });
                    
                    // Tự động mở tab mới khi bật stream thành công (sau 1.5s để server kịp khởi động)
                    setTimeout(() => {
                        window.open('http://' + window.location.hostname + ':8088', '_blank');
                    }, 1500);
                }
                setTimeout(checkStreamStatus, 1500);
            } catch(e) {
                alert('Lỗi: ' + e.message);
                checkStreamStatus();
            } finally {
                setTimeout(() => toggleBtn.disabled = false, 1500);
            }
        }
        
        // Auto-check stream status initially
        setTimeout(checkStreamStatus, 1000);

        // ==================== GOOGLE DRIVE GAME LIBRARY ====================
        let gdriveLibrary = [];
        let currentResolvedDrive = null;
        let driveAvailableSystems = [];
        let driveDownloadPolling = null;

        function escapeDriveHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        async function loadDriveSystems() {
            try {
                const res = await fetch('/api/gdrive/systems');
                const data = await res.json();
                if (data.ok && data.systems) {
                    driveAvailableSystems = data.systems;
                }
            } catch (e) {
                console.error('Error loading systems for gdrive:', e);
            }
        }

        async function resolveDriveUrl() {
            const input = document.getElementById('gdrive-url-input');
            const btn = document.getElementById('btn-gdrive-resolve');
            const url = (input ? input.value : '').trim();
            if (!url) {
                showToast('Vui lòng dán liên kết hoặc File ID Google Drive');
                return;
            }

            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span>⏳</span> Đang kiểm tra...';
            }

            try {
                const res = await fetch('/api/gdrive/resolve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                if (!data.ok) {
                    throw new Error(data.error || 'Không thể lấy thông tin tệp từ Drive');
                }

                currentResolvedDrive = data;
                renderDrivePreview(data);
                showToast('Đã lấy thông tin tệp Google Drive thành công!');
            } catch (e) {
                showToast('Lỗi: ' + e.message);
                cancelDrivePreview();
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<span>🔍</span> Lấy thông tin';
                }
            }
        }

        function renderDrivePreview(data) {
            const card = document.getElementById('gdrive-preview-card');
            if (!card) return;
            document.getElementById('gdrive-preview-title').textContent = data.title || data.filename || 'Game Drive';
            document.getElementById('gdrive-preview-filename').textContent = data.filename || '--';
            document.getElementById('gdrive-preview-size').textContent = data.file_size || '--';
            const sysBadge = document.getElementById('gdrive-preview-sys');
            if (sysBadge) {
                sysBadge.textContent = data.suggested_sys || 'ROM';
            }
            card.style.display = 'block';
        }

        function cancelDrivePreview() {
            currentResolvedDrive = null;
            const card = document.getElementById('gdrive-preview-card');
            if (card) card.style.display = 'none';
        }

        async function saveCurrentDriveToLibrary() {
            if (!currentResolvedDrive) {
                showToast('Chưa có thông tin tệp để lưu');
                return;
            }
            try {
                const res = await fetch('/api/gdrive/library/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentResolvedDrive)
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã lưu game vào thư viện Drive riêng!');
                    cancelDrivePreview();
                    const input = document.getElementById('gdrive-url-input');
                    if (input) input.value = '';
                    loadDriveLibrary();
                } else {
                    showToast('Lỗi khi lưu: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e.message);
            }
        }

        async function loadDriveLibrary(forceToast = false) {
            const table = document.getElementById('gdrive-library-table');
            const empty = document.getElementById('gdrive-empty-state');
            const countDisp = document.getElementById('gdrive-lib-count');

            try {
                const res = await fetch('/api/gdrive/library');
                const data = await res.json();
                if (data.ok) {
                    gdriveLibrary = data.items || [];
                    if (countDisp) countDisp.textContent = `${gdriveLibrary.length} game đã lưu`;
                    if (gdriveLibrary.length === 0) {
                        if (empty) empty.style.display = 'block';
                        if (table) table.innerHTML = '';
                    } else {
                        if (empty) empty.style.display = 'none';
                        renderDriveLibraryTable(gdriveLibrary);
                    }
                    if (forceToast) showToast('Đã nạp lại thư viện Google Drive!');
                }
            } catch (e) {
                console.error('Error loading gdrive library:', e);
            }
        }

        function renderDriveLibraryTable(items) {
            const container = document.getElementById('gdrive-library-table');
            if (!container) return;

            container.innerHTML = items.map(item => {
                const isDownloaded = item.status === 'downloaded';
                const sysTag = item.downloaded_sys || item.suggested_sys || 'ROM';
                const addedDate = item.added_at ? new Date(item.added_at * 1000).toLocaleDateString('vi-VN') : '';

                return `
                <div style="display: flex; align-items: center; justify-content: space-between; background: #0b1329; border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px; gap: 12px; flex-wrap: wrap;">
                    <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 220px;">
                        <span class="badge" style="background: ${isDownloaded ? '#059669' : '#2563eb'}; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; min-width: 45px; text-align: center;">
                            ${sysTag}
                        </span>
                        <div style="min-width: 0;">
                            <div style="font-size: 14px; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 420px;">
                                ${escapeDriveHtml(item.title || item.filename || 'Game')}
                            </div>
                            <div style="font-size: 12px; color: #94a3b8; display: flex; gap: 14px; margin-top: 2px; flex-wrap: wrap;">
                                <span>Tệp: <span style="color:#cbd5e1;">${escapeDriveHtml(item.filename || '--')}</span></span>
                                <span>Dung lượng: <span style="color:#38bdf8;">${item.file_size || '--'}</span></span>
                                ${addedDate ? `<span>Ngày thêm: ${addedDate}</span>` : ''}
                                ${isDownloaded ? `<span style="color:#10b981; font-weight:600;">✓ Đã tải về ${item.downloaded_sys || ''}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <button class="btn btn-sm ${isDownloaded ? 'btn-secondary' : 'btn-green'}" onclick="openDownloadDriveModal('${item.id}')" style="display: flex; align-items: center; gap: 4px;">
                            <span>${isDownloaded ? '🔄' : '⚡'}</span> ${isDownloaded ? 'Tải lại' : 'Tải về máy'}
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteDriveItem('${item.id}')" title="Xóa khỏi thư viện Drive">
                            🗑️
                        </button>
                    </div>
                </div>
                `;
            }).join('');
        }

        let selectedDriveDownloadItem = null;

        async function openDownloadDriveModal(itemId) {
            const item = gdriveLibrary.find(it => it.id === itemId);
            if (!item) return;
            selectedDriveDownloadItem = item;

            if (!driveAvailableSystems.length) {
                await loadDriveSystems();
            }

            document.getElementById('mdl-gdrive-title').textContent = item.title || item.filename;
            document.getElementById('mdl-gdrive-filename').textContent = item.filename || '--';
            document.getElementById('mdl-gdrive-size').textContent = item.file_size || '--';

            const select = document.getElementById('mdl-gdrive-sys-select');
            const defaultSys = item.downloaded_sys || item.suggested_sys || 'GBA';

            const fallbackSystems = [
                { tag: 'GBA', name: 'Game Boy Advance (GBA)' },
                { tag: 'SFC', name: 'Super Nintendo (SNES / SFC)' },
                { tag: 'FC', name: 'NES / Famicom (FC)' },
                { tag: 'MD', name: 'Sega Mega Drive / Genesis (MD)' },
                { tag: 'PS', name: 'Sony PlayStation (PS1)' },
                { tag: 'PSP', name: 'PlayStation Portable (PSP)' },
                { tag: 'NDS', name: 'Nintendo DS (NDS)' },
                { tag: 'JAVA', name: 'Java J2ME Mobile (JAVA)' },
                { tag: 'ARCADE', name: 'Arcade / CPS / FBNeo' },
                { tag: 'GB', name: 'Game Boy (GB)' },
                { tag: 'GBC', name: 'Game Boy Color (GBC)' },
                { tag: 'PICO8', name: 'PICO-8' },
                { tag: 'DC', name: 'Sega Dreamcast (DC)' },
                { tag: 'N64', name: 'Nintendo 64 (N64)' },
                { tag: 'PCE', name: 'PC Engine (PCE)' },
                { tag: 'NEOGEO', name: 'SNK Neo Geo' },
                { tag: 'WSC', name: 'WonderSwan Color (WSC)' },
            ];

            const sysList = driveAvailableSystems.length ? driveAvailableSystems : fallbackSystems;
            select.innerHTML = sysList.map(s => {
                const tag = s.tag || s.dir || s.code;
                const name = s.name || tag;
                const sel = (tag === defaultSys) ? 'selected' : '';
                return `<option value="${tag}" ${sel}>${name} (${tag})</option>`;
            }).join('');

            const isArchive = (item.filename || '').toLowerCase().match(/\.(zip|7z|rar)$/);
            const extractCb = document.getElementById('mdl-gdrive-extract-cb');
            if (extractCb) {
                extractCb.checked = Boolean(isArchive && ['PS', 'PSP', 'JAVA'].includes(defaultSys));
            }

            openModal('modal-download-gdrive');
        }

        async function confirmStartDriveDownload() {
            if (!selectedDriveDownloadItem) return;
            const item = selectedDriveDownloadItem;
            const select = document.getElementById('mdl-gdrive-sys-select');
            const extractCb = document.getElementById('mdl-gdrive-extract-cb');
            const sysCode = select ? select.value : (item.suggested_sys || 'GBA');
            const extract = extractCb ? extractCb.checked : false;

            closeModal('modal-download-gdrive');
            showToast(`Bắt đầu tải ${item.title || item.filename} về hệ máy ${sysCode}...`);

            try {
                const res = await fetch('/api/gdrive/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: item.id,
                        sys_code: sysCode,
                        title: item.title,
                        filename: item.filename,
                        direct_link: item.direct_link,
                        url: item.url,
                        extract: extract
                    })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast(data.message || 'Đã khởi tạo tiến trình tải!');
                    checkDriveDownloadsStatus();
                } else {
                    showToast('Lỗi tải game: ' + (data.error || ''));
                }
            } catch (e) {
                showToast('Lỗi kết nối tải: ' + e.message);
            }
        }

        async function deleteDriveItem(itemId) {
            if (!confirm('Bạn có chắc muốn xóa game này khỏi thư viện Drive riêng?')) return;
            try {
                const res = await fetch('/api/gdrive/library/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: itemId })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('Đã xóa game khỏi thư viện Drive!');
                    loadDriveLibrary();
                } else {
                    showToast('Lỗi khi xóa!');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e.message);
            }
        }

        async function checkDriveDownloadsStatus() {
            const bar = document.getElementById('gdrive-downloads-bar');
            const list = document.getElementById('gdrive-downloads-list');
            const countDisp = document.getElementById('gdrive-dl-count');

            try {
                const res = await fetch('/api/gdrive/download/status');
                const data = await res.json();
                if (data.ok && data.downloads) {
                    const downloads = data.downloads;
                    const activeDownloads = downloads.filter(d => d.status === 'downloading');

                    if (activeDownloads.length > 0) {
                        if (bar) bar.style.display = 'block';
                        if (countDisp) countDisp.textContent = `${activeDownloads.length} đang tải`;
                        if (list) {
                            list.innerHTML = activeDownloads.map(d => `
                                <div style="background: #0b1329; border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                                        <strong style="color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px;">
                                            ${escapeDriveHtml(d.title || d.filename)} (${d.sys_code})
                                        </strong>
                                        <span style="color: #38bdf8; font-weight: 700;">${d.progress_pct}% - ${d.speed_str}</span>
                                    </div>
                                    <div class="progress-bar-bg" style="height: 6px;">
                                        <div class="progress-bar-fill" style="width: ${d.progress_pct}%;"></div>
                                    </div>
                                </div>
                            `).join('');
                        }

                        if (!driveDownloadPolling) {
                            driveDownloadPolling = setInterval(checkDriveDownloadsStatus, 1000);
                        }
                    } else {
                        if (bar) bar.style.display = 'none';
                        if (driveDownloadPolling) {
                            clearInterval(driveDownloadPolling);
                            driveDownloadPolling = null;
                            loadDriveLibrary();
                        }
                    }
                }
            } catch (e) {
                console.error('Error polling drive downloads:', e);
            }
        }

        // Khởi động trang web
        loadStorageStatus();
        
        // Đọc hash từ URL (ví dụ: /#chat)
        const initialTab = window.location.hash.replace('#', '');
        if (initialTab && document.getElementById(`nav-btn-${initialTab}`)) {
            switchMainTab(initialTab);
        } else {
            loadSystems(); // Mặc định
        }