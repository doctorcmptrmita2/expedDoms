/**
 * Admin panel JavaScript for CZDS management.
 * Enhanced with Download/Parse/Full options and statistics
 */

// Global state
let currentZoneUrl = null;
let currentTld = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeAuthForm();
    initializeZoneButtons();
    initializeRefreshButtons();
    initializeModals();
    loadDownloadHistory();
    updateStatistics();
    updateAuthStatusUI();
    
    // Try to load zones if credentials are stored
    const storedUsername = localStorage.getItem('czds_username');
    const storedPassword = localStorage.getItem('czds_password');
    if (storedUsername && storedPassword) {
        loadZones(storedUsername, storedPassword).catch(err => {
            console.error('Auto-load zones error:', err);
        });
    }
});

/**
 * Update authentication status UI based on localStorage
 */
function updateAuthStatusUI() {
    const storedUsername = localStorage.getItem('czds_username');
    const storedToken = localStorage.getItem('czds_token');
    
    const authStatusAuth = document.getElementById('auth-status-authenticated');
    const authStatusNotAuth = document.getElementById('auth-status-not-authenticated');
    const authUsername = document.getElementById('auth-username');
    const usernameInput = document.getElementById('username');
    
    if (storedUsername && storedToken) {
        // User is authenticated
        if (authStatusAuth) authStatusAuth.classList.remove('hidden');
        if (authStatusNotAuth) authStatusNotAuth.classList.add('hidden');
        if (authUsername) authUsername.textContent = storedUsername;
        if (usernameInput) usernameInput.value = storedUsername;
    } else {
        // User is not authenticated
        if (authStatusAuth) authStatusAuth.classList.add('hidden');
        if (authStatusNotAuth) authStatusNotAuth.classList.remove('hidden');
    }
}

/**
 * Initialize authentication form
 */
function initializeAuthForm() {
    const authForm = document.getElementById('auth-form');
    if (!authForm) return;
    
    authForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        const submitBtn = authForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="animate-pulse">Authenticating...</span>';
        
        try {
            const response = await fetch('/api/v1/czds/authenticate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                localStorage.setItem('czds_username', username);
                localStorage.setItem('czds_password', password);
                localStorage.setItem('czds_token', JSON.stringify(data.data));
                
                // Update UI immediately
                updateAuthStatusUI();
                
                showToast('✅ Authentication successful!', 'success');
                await loadZones(username, password);
            } else {
                throw new Error(data.detail || 'Authentication failed');
            }
        } catch (error) {
            showToast('❌ ' + error.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

/**
 * Initialize zone action buttons
 */
function initializeZoneButtons() {
    // Info buttons
    document.querySelectorAll('.zone-info-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            await showZoneInfo(this.dataset.url);
        });
    });
    
    // Download only buttons
    document.querySelectorAll('.zone-download-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            await executeAction(this.dataset.url, this.dataset.tld, 'download');
        });
    });
    
    // Parse only buttons
    document.querySelectorAll('.zone-parse-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            await executeAction(this.dataset.url, this.dataset.tld, 'parse');
        });
    });
    
    // Download + Parse buttons
    document.querySelectorAll('.zone-full-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            await executeAction(this.dataset.url, this.dataset.tld, 'full');
        });
    });
}

/**
 * Initialize modal handlers
 */
function initializeModals() {
    const infoModal = document.getElementById('zone-info-modal');
    const actionModal = document.getElementById('action-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const closeActionModalBtn = document.getElementById('close-action-modal');
    
    if (closeModalBtn && infoModal) {
        closeModalBtn.addEventListener('click', () => infoModal.classList.add('hidden'));
        infoModal.addEventListener('click', (e) => {
            if (e.target === infoModal) infoModal.classList.add('hidden');
        });
    }
    
    if (closeActionModalBtn && actionModal) {
        closeActionModalBtn.addEventListener('click', () => actionModal.classList.add('hidden'));
        actionModal.addEventListener('click', (e) => {
            if (e.target === actionModal) actionModal.classList.add('hidden');
        });
    }
    
    // Action modal buttons
    document.getElementById('action-download-only')?.addEventListener('click', () => {
        document.getElementById('action-modal').classList.add('hidden');
        executeAction(currentZoneUrl, currentTld, 'download');
    });
    
    document.getElementById('action-parse-only')?.addEventListener('click', () => {
        document.getElementById('action-modal').classList.add('hidden');
        executeAction(currentZoneUrl, currentTld, 'parse');
    });
    
    document.getElementById('action-download-parse')?.addEventListener('click', () => {
        document.getElementById('action-modal').classList.add('hidden');
        executeAction(currentZoneUrl, currentTld, 'full');
    });
    
    // Clear status button
    document.getElementById('clear-status')?.addEventListener('click', () => {
        document.getElementById('operation-messages').innerHTML = '';
        document.getElementById('operation-status').classList.add('hidden');
    });
}

/**
 * Execute download/parse/full action
 */
async function executeAction(zoneUrl, tld, action) {
    const storedUsername = localStorage.getItem('czds_username');
    const storedPassword = localStorage.getItem('czds_password');
    
    if (!storedUsername || !storedPassword) {
        showToast('⚠️ Please authenticate first', 'error');
        return;
    }
    
    const statusDiv = document.getElementById('operation-status');
    const messagesDiv = document.getElementById('operation-messages');
    
    statusDiv.classList.remove('hidden');
    
    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = 'bg-blue-500/10 border border-blue-500/30 rounded-xl p-4';
    
    const actionLabels = {
        'download': '⬇️ Downloading',
        'parse': '📝 Parsing',
        'full': '🚀 Download + Parse'
    };
    
    // Estimated times (in seconds) based on action type
    // Large TLDs like .com, .net, .org, .info take much longer
    const largeTlds = ['com', 'net', 'org', 'info', 'biz', 'email', 'online', 'store', 'club', 'life', 'cloud'];
    const isLargeTld = largeTlds.includes(tld.toLowerCase());
    
    const estimatedTimes = {
        'download': isLargeTld ? 300 : 60,   // 5 min for large, 1 min for small
        'parse': isLargeTld ? 600 : 120,     // 10 min for large, 2 min for small
        'full': isLargeTld ? 900 : 180       // 15 min for large, 3 min for small
    };
    
    const startTime = Date.now();
    const estimatedSeconds = estimatedTimes[action];
    
    messageDiv.innerHTML = `
        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="animate-spin w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    <span class="text-blue-300">${actionLabels[action]} <strong class="text-blue-400">.${tld}</strong></span>
                </div>
                <div class="text-sm text-mist">
                    <span class="elapsed-time">0:00</span> / <span class="text-blue-400">~${formatTime(estimatedSeconds)}</span>
                </div>
            </div>
            <div class="relative h-2 bg-void rounded-full overflow-hidden">
                <div class="progress-bar absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-neon-cyan rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
            <div class="flex justify-between text-xs text-mist/60">
                <span>Processing zone file...</span>
                <span class="progress-percent">0%</span>
            </div>
        </div>
    `;
    messagesDiv.insertBefore(messageDiv, messagesDiv.firstChild);
    
    // Start progress animation
    const progressBar = messageDiv.querySelector('.progress-bar');
    const progressPercent = messageDiv.querySelector('.progress-percent');
    const elapsedTime = messageDiv.querySelector('.elapsed-time');
    
    const progressInterval = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        const progress = Math.min((elapsed / estimatedSeconds) * 100, 95); // Max 95% until complete
        
        progressBar.style.width = progress + '%';
        progressPercent.textContent = Math.round(progress) + '%';
        elapsedTime.textContent = formatTime(Math.round(elapsed));
        
        // Change color based on progress
        if (progress > 75) {
            progressBar.classList.remove('from-blue-500', 'to-neon-cyan');
            progressBar.classList.add('from-amber-500', 'to-orange-400');
        }
    }, 500);
    
    try {
        let result;
        
        if (action === 'download' || action === 'full') {
            // Download (with or without auto_process)
            const autoProcess = action === 'full';
            const response = await fetch(`/api/v1/czds/download?auto_process=${autoProcess}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    zone_url: zoneUrl,
                    tld: tld,
                    username: storedUsername,
                    password: storedPassword
                })
            });
            
            result = await response.json();
            
            if (result.success) {
                // Save to history
                saveDownloadHistory(tld, result.data, action);
            }
        } else if (action === 'parse') {
            // Parse only - let API find the latest zone file
            const response = await fetch(`/api/v1/import/single-zone?tld=${encodeURIComponent(tld)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            result = await response.json();
            
            if (result.success) {
                // Update history with parse info
                updateParseHistory(tld, result);
            }
        }
        
        // Stop progress animation
        clearInterval(progressInterval);
        
        // Calculate actual elapsed time
        const totalElapsed = Math.round((Date.now() - startTime) / 1000);
        
        if (result.success) {
            // Show 100% complete
            progressBar.style.width = '100%';
            progressBar.classList.remove('from-blue-500', 'to-neon-cyan', 'from-amber-500', 'to-orange-400');
            progressBar.classList.add('from-neon-green', 'to-emerald-400');
            progressPercent.textContent = '100%';
            
            messageDiv.className = 'bg-neon-green/10 border border-neon-green/30 rounded-xl p-4';
            
            let html = `
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                        <span class="text-neon-green font-semibold">✅ ${actionLabels[action]} complete for .${tld}</span>
                    </div>
                    <span class="text-sm text-mist">Completed in <span class="text-neon-green font-mono">${formatTime(totalElapsed)}</span></span>
                </div>
                <div class="relative h-2 bg-void rounded-full overflow-hidden mb-3">
                    <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-neon-green to-emerald-400 rounded-full w-full"></div>
                </div>
            `;
            
            if (action === 'download' || action === 'full') {
                html += `<div class="text-sm text-mist">Size: <span class="text-frost">${formatBytes(result.data.size)}</span></div>`;
                html += `<div class="text-sm text-mist font-mono truncate">${escapeHtml(result.data.path)}</div>`;
                
                if (result.data.processed && result.data.process_result) {
                    const proc = result.data.process_result;
                    html += `<div class="mt-3 pt-3 border-t border-neon-green/30 grid grid-cols-3 gap-4">`;
                    html += `<div><div class="text-xs text-mist uppercase">Domains</div><div class="text-lg font-bold text-neon-cyan">${(proc.sld_count || 0).toLocaleString()}</div></div>`;
                    if (proc.drops_detected) {
                        html += `<div><div class="text-xs text-mist uppercase">Drops</div><div class="text-lg font-bold text-neon-purple">${(proc.dropped_count || 0).toLocaleString()}</div></div>`;
                        html += `<div><div class="text-xs text-mist uppercase">Saved</div><div class="text-lg font-bold text-neon-green">${(proc.persisted_count || 0).toLocaleString()}</div></div>`;
                    }
                    html += `</div>`;
                }
            }
            
            if (action === 'parse') {
                html += `<div class="mt-3 grid grid-cols-3 gap-4">`;
                html += `<div><div class="text-xs text-mist uppercase">Domains</div><div class="text-lg font-bold text-neon-cyan">${(result.sld_count || 0).toLocaleString()}</div></div>`;
                html += `<div><div class="text-xs text-mist uppercase">Imported</div><div class="text-lg font-bold text-neon-green">${(result.imported || 0).toLocaleString()}</div></div>`;
                html += `<div><div class="text-xs text-mist uppercase">Skipped</div><div class="text-lg font-bold text-mist/60">${(result.skipped || 0).toLocaleString()}</div></div>`;
                html += `</div>`;
            }
            
            messageDiv.innerHTML = html;
            
            // Update statistics
            updateStatistics();
            
            showToast(`✅ ${actionLabels[action]} complete for .${tld}`, 'success');
        } else {
            throw new Error(result.detail || 'Operation failed');
        }
    } catch (error) {
        // Stop progress animation
        clearInterval(progressInterval);
        
        const totalElapsed = Math.round((Date.now() - startTime) / 1000);
        
        messageDiv.className = 'bg-red-500/10 border border-red-500/30 rounded-xl p-4';
        messageDiv.innerHTML = `
            <div class="flex items-center justify-between mb-3">
                <div class="text-red-400 font-semibold">❌ Error: ${escapeHtml(error.message)}</div>
                <span class="text-sm text-mist">Failed after <span class="text-red-400 font-mono">${formatTime(totalElapsed)}</span></span>
            </div>
            <div class="relative h-2 bg-void rounded-full overflow-hidden">
                <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-red-500 to-red-400 rounded-full" style="width: ${progressBar ? progressBar.style.width : '0%'}"></div>
            </div>
        `;
        showToast('❌ ' + error.message, 'error');
    }
}

/**
 * Save download to history
 */
function saveDownloadHistory(tld, data, action) {
    const history = JSON.parse(localStorage.getItem('download_history') || '[]');
    
    history.push({
        tld: tld,
        date: new Date().toISOString(),
        path: data.path,
        size: data.size,
        action: action,
        processed: data.processed || false,
        process_result: data.process_result || {}
    });
    
    // Keep only last 100 downloads
    while (history.length > 100) {
        history.shift();
    }
    
    localStorage.setItem('download_history', JSON.stringify(history));
}

/**
 * Update parse history
 */
function updateParseHistory(tld, result) {
    const history = JSON.parse(localStorage.getItem('download_history') || '[]');
    
    history.push({
        tld: tld,
        date: new Date().toISOString(),
        action: 'parse',
        processed: true,
        process_result: {
            sld_count: result.sld_count,
            imported: result.imported,
            skipped: result.skipped
        }
    });
    
    while (history.length > 100) {
        history.shift();
    }
    
    localStorage.setItem('download_history', JSON.stringify(history));
}

/**
 * Update statistics display
 */
function updateStatistics() {
    const history = JSON.parse(localStorage.getItem('download_history') || '[]');
    
    // Calculate totals
    let totalDownloads = 0;
    let totalDomains = 0;
    let totalDrops = 0;
    let totalSize = 0;
    
    // TLD breakdown
    const tldStats = {};
    
    history.forEach(item => {
        totalDownloads++;
        totalSize += item.size || 0;
        
        if (item.process_result) {
            totalDomains += item.process_result.sld_count || item.process_result.imported || 0;
            totalDrops += item.process_result.dropped_count || item.process_result.persisted_count || 0;
        }
        
        // TLD breakdown
        if (!tldStats[item.tld]) {
            tldStats[item.tld] = {
                downloads: 0,
                domains: 0,
                drops: 0,
                size: 0,
                lastDownload: null
            };
        }
        
        tldStats[item.tld].downloads++;
        tldStats[item.tld].size += item.size || 0;
        if (item.process_result) {
            tldStats[item.tld].domains += item.process_result.sld_count || item.process_result.imported || 0;
            tldStats[item.tld].drops += item.process_result.dropped_count || item.process_result.persisted_count || 0;
        }
        
        const itemDate = new Date(item.date);
        if (!tldStats[item.tld].lastDownload || itemDate > new Date(tldStats[item.tld].lastDownload)) {
            tldStats[item.tld].lastDownload = item.date;
        }
    });
    
    // Update stat cards
    document.getElementById('stat-total-downloads').textContent = totalDownloads.toLocaleString();
    document.getElementById('stat-total-domains').textContent = totalDomains.toLocaleString();
    document.getElementById('stat-total-drops').textContent = totalDrops.toLocaleString();
    document.getElementById('stat-total-size').textContent = formatBytes(totalSize);
    
    // Update TLD table
    const tbody = document.getElementById('tld-stats-body');
    if (tbody) {
        if (Object.keys(tldStats).length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="py-8 text-center text-mist/60">No download history yet</td></tr>';
        } else {
            tbody.innerHTML = Object.entries(tldStats)
                .sort((a, b) => new Date(b[1].lastDownload) - new Date(a[1].lastDownload))
                .map(([tld, stats]) => `
                    <tr class="hover:bg-steel/20 transition-colors">
                        <td class="py-3 px-4">
                            <span class="inline-flex items-center px-2.5 py-1 rounded-lg bg-neon-purple/10 text-neon-purple text-sm font-medium">.${escapeHtml(tld)}</span>
                        </td>
                        <td class="py-3 px-4 font-mono text-frost">${stats.downloads}</td>
                        <td class="py-3 px-4 font-mono text-neon-cyan">${stats.domains.toLocaleString()}</td>
                        <td class="py-3 px-4 font-mono text-neon-purple">${stats.drops.toLocaleString()}</td>
                        <td class="py-3 px-4 font-mono text-mist">${formatBytes(stats.size)}</td>
                        <td class="py-3 px-4 text-sm text-mist">${new Date(stats.lastDownload).toLocaleString()}</td>
                    </tr>
                `).join('');
        }
    }
}

/**
 * Show zone file information
 */
async function showZoneInfo(zoneUrl) {
    const storedUsername = localStorage.getItem('czds_username');
    const storedPassword = localStorage.getItem('czds_password');
    
    if (!storedUsername || !storedPassword) {
        showToast('⚠️ Please authenticate first', 'error');
        return;
    }
    
    const modal = document.getElementById('zone-info-modal');
    const content = document.getElementById('zone-info-content');
    
    content.innerHTML = '<div class="flex items-center gap-3"><div class="animate-spin w-5 h-5 border-2 border-neon-cyan border-t-transparent rounded-full"></div><span class="text-mist">Loading...</span></div>';
    modal.classList.remove('hidden');
    
    try {
        const response = await fetch(`/api/v1/czds/zone-info?zone_url=${encodeURIComponent(zoneUrl)}&username=${encodeURIComponent(storedUsername)}&password=${encodeURIComponent(storedPassword)}`);
        const data = await response.json();
        
        if (data.success) {
            const info = data.data;
            content.innerHTML = `
                <div class="space-y-3">
                    <div class="p-3 rounded-xl bg-void/50">
                        <div class="text-xs text-mist uppercase tracking-wider mb-1">URL</div>
                        <div class="font-mono text-sm text-frost break-all">${escapeHtml(info.url)}</div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="p-3 rounded-xl bg-void/50">
                            <div class="text-xs text-mist uppercase tracking-wider mb-1">Size</div>
                            <div class="text-frost font-semibold">${formatBytes(info.size)}</div>
                        </div>
                        <div class="p-3 rounded-xl bg-void/50">
                            <div class="text-xs text-mist uppercase tracking-wider mb-1">Last Modified</div>
                            <div class="text-frost font-semibold">${info.lastModified || 'N/A'}</div>
                        </div>
                    </div>
                    ${info.filename ? `
                    <div class="p-3 rounded-xl bg-void/50">
                        <div class="text-xs text-mist uppercase tracking-wider mb-1">Filename</div>
                        <div class="font-mono text-sm text-frost">${escapeHtml(info.filename)}</div>
                    </div>
                    ` : ''}
                </div>
            `;
        } else {
            content.innerHTML = `<div class="p-4 rounded-xl bg-red-500/10 text-red-400">Error: ${escapeHtml(data.detail || 'Unknown error')}</div>`;
        }
    } catch (error) {
        content.innerHTML = `<div class="p-4 rounded-xl bg-red-500/10 text-red-400">Error: ${escapeHtml(error.message)}</div>`;
    }
}

/**
 * Load zones list
 */
async function loadZones(username, password) {
    try {
        const response = await fetch('/api/v1/czds/zones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.data) {
            // Update the zones table dynamically
            updateZonesTable(data.data);
            showToast(`📋 Loaded ${data.count} zones`, 'success');
        }
    } catch (error) {
        console.error('Error loading zones:', error);
        showToast('❌ Error loading zones', 'error');
    }
}

/**
 * Update zones table with data
 */
function updateZonesTable(zones) {
    const tbody = document.getElementById('zones-body');
    const emptyDiv = document.getElementById('zones-empty');
    const zonesSection = document.getElementById('zones-section');
    
    if (!zonesSection) return;
    
    // Hide empty message
    if (emptyDiv) emptyDiv.classList.add('hidden');
    
    // If no tbody exists, we need to create the table structure
    if (!tbody) {
        // Find the zones section content area
        const contentArea = zonesSection.querySelector('.relative');
        if (contentArea) {
            // Remove the empty state
            const existingEmpty = contentArea.querySelector('#zones-empty');
            if (existingEmpty) existingEmpty.remove();
            
            // Add table
            const tableHTML = `
                <div class="mb-6">
                    <p class="text-mist">Found <span class="text-frost font-semibold">${zones.length}</span> authorized zone files</p>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr class="border-b border-steel/30">
                                <th class="text-left py-4 px-4 text-mist font-medium text-sm uppercase tracking-wider">Zone URL</th>
                                <th class="text-left py-4 px-4 text-mist font-medium text-sm uppercase tracking-wider">TLD</th>
                                <th class="text-left py-4 px-4 text-mist font-medium text-sm uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="zones-body" class="divide-y divide-steel/20"></tbody>
                    </table>
                </div>
            `;
            contentArea.insertAdjacentHTML('beforeend', tableHTML);
        }
    }
    
    // Now populate the tbody
    const newTbody = document.getElementById('zones-body');
    if (newTbody) {
        newTbody.innerHTML = zones.slice(0, 50).map(zoneUrl => {
            const parts = zoneUrl.split('/');
            const tld = parts[parts.length - 1].replace('.zone', '');
            return `
                <tr class="hover:bg-steel/20 transition-colors duration-150">
                    <td class="py-4 px-4 font-mono text-sm text-frost/80 truncate max-w-md">${escapeHtml(zoneUrl)}</td>
                    <td class="py-4 px-4">
                        <span class="inline-flex items-center px-2.5 py-1 rounded-lg bg-neon-purple/10 text-neon-purple text-sm font-medium">.${escapeHtml(tld)}</span>
                    </td>
                    <td class="py-4 px-4">
                        <div class="flex gap-2 flex-wrap">
                            <button class="zone-info-btn px-3 py-1.5 bg-blue-500/10 text-blue-400 rounded-lg text-xs hover:bg-blue-500/20 transition-colors font-medium" 
                                data-url="${escapeHtml(zoneUrl)}">
                                ℹ️ Info
                            </button>
                            <button class="zone-download-btn px-3 py-1.5 bg-neon-cyan/10 text-neon-cyan rounded-lg text-xs hover:bg-neon-cyan/20 transition-colors font-medium"
                                data-url="${escapeHtml(zoneUrl)}" data-tld="${escapeHtml(tld)}" data-action="download">
                                ⬇️ Download
                            </button>
                            <button class="zone-parse-btn px-3 py-1.5 bg-amber-500/10 text-amber-400 rounded-lg text-xs hover:bg-amber-500/20 transition-colors font-medium"
                                data-url="${escapeHtml(zoneUrl)}" data-tld="${escapeHtml(tld)}" data-action="parse">
                                📝 Parse
                            </button>
                            <button class="zone-full-btn px-3 py-1.5 bg-neon-green/10 text-neon-green rounded-lg text-xs hover:bg-neon-green/20 transition-colors font-medium"
                                data-url="${escapeHtml(zoneUrl)}" data-tld="${escapeHtml(tld)}" data-action="full">
                                🚀 Full
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
        // Re-initialize buttons for newly added elements
        initializeZoneButtons();
    }
}

/**
 * Load download history on page load
 */
function loadDownloadHistory() {
    updateStatistics();
}

/**
 * Initialize refresh buttons
 */
function initializeRefreshButtons() {
    document.getElementById('refresh-token')?.addEventListener('click', () => window.location.reload());
    
    document.getElementById('refresh-zones')?.addEventListener('click', async () => {
        const storedUsername = localStorage.getItem('czds_username');
        const storedPassword = localStorage.getItem('czds_password');
        
        if (storedUsername && storedPassword) {
            await loadZones(storedUsername, storedPassword);
            window.location.reload();
        } else {
            showToast('⚠️ Please authenticate first', 'error');
        }
    });
}

/**
 * Format bytes to human readable
 */
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
}

/**
 * Format seconds to mm:ss or hh:mm:ss
 */
function formatTime(seconds) {
    if (seconds < 60) {
        return `0:${seconds.toString().padStart(2, '0')}`;
    } else if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    if (!toast || !toastMessage) return;
    
    toastMessage.textContent = message;
    toast.classList.remove('hidden', 'translate-y-4', 'opacity-0');
    
    setTimeout(() => {
        toast.classList.add('translate-y-4', 'opacity-0');
        setTimeout(() => toast.classList.add('hidden'), 300);
    }, 3000);
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
