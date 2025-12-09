/**
 * Admin panel JavaScript for CZDS management.
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeAuthForm();
    initializeZoneButtons();
    initializeRefreshButtons();
    loadDownloadHistory();
    
    // Try to load zones if credentials are stored
    const storedUsername = localStorage.getItem('czds_username');
    const storedPassword = localStorage.getItem('czds_password');
    if (storedUsername && storedPassword) {
        // Load zones asynchronously without blocking
        loadZones(storedUsername, storedPassword).catch(err => {
            console.error('Auto-load zones error:', err);
        });
    }
});

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
        submitBtn.textContent = 'Authenticating...';
        
        try {
            const response = await fetch('/api/v1/czds/authenticate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            // Check if response is OK
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Store credentials in localStorage for future requests
                localStorage.setItem('czds_username', username);
                localStorage.setItem('czds_password', password);
                localStorage.setItem('czds_token', JSON.stringify(data.data));
                
                showToast('Authentication successful! Loading zones...', 'success');
                
                // Load zones immediately
                await loadZones(username, password);
                
                // Reload page after a short delay to show updated state
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                const errorMsg = data.detail || data.message || 'Authentication failed';
                console.error('Authentication failed:', errorMsg);
                showToast('Authentication failed: ' + errorMsg, 'error');
            }
        } catch (error) {
            console.error('Authentication error:', error);
            showToast('Error: ' + error.message, 'error');
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
    // Zone info buttons
    document.querySelectorAll('.zone-info-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const zoneUrl = this.dataset.url;
            await showZoneInfo(zoneUrl);
        });
    });
    
    // Zone download buttons
    document.querySelectorAll('.zone-download-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const zoneUrl = this.dataset.url;
            const tld = this.dataset.tld;
            await downloadZone(zoneUrl, tld);
        });
    });
}

/**
 * Show zone file information
 */
async function showZoneInfo(zoneUrl) {
    const storedUsername = localStorage.getItem('czds_username');
    const storedPassword = localStorage.getItem('czds_password');
    
    if (!storedUsername || !storedPassword) {
        showToast('Please authenticate first', 'error');
        return;
    }
    const modal = document.getElementById('zone-info-modal');
    const content = document.getElementById('zone-info-content');
    
    content.innerHTML = '<p class="text-slate-600">Loading...</p>';
    modal.classList.remove('hidden');
    
    try {
        const response = await fetch(`/api/v1/czds/zone-info?zone_url=${encodeURIComponent(zoneUrl)}&username=${encodeURIComponent(storedUsername)}&password=${encodeURIComponent(storedPassword)}`);
        const data = await response.json();
        
        if (data.success) {
            const info = data.data;
            content.innerHTML = `
                <div class="space-y-2">
                    <div><strong>URL:</strong> <span class="font-mono text-sm">${escapeHtml(info.url)}</span></div>
                    <div><strong>Size:</strong> ${formatBytes(info.size)}</div>
                    <div><strong>Last Modified:</strong> ${info.lastModified || 'N/A'}</div>
                    <div><strong>Content Type:</strong> ${info.contentType || 'N/A'}</div>
                    ${info.filename ? `<div><strong>Filename:</strong> ${escapeHtml(info.filename)}</div>` : ''}
                </div>
            `;
        } else {
            content.innerHTML = `<p class="text-red-600">Error: ${escapeHtml(data.detail || 'Unknown error')}</p>`;
        }
    } catch (error) {
        content.innerHTML = `<p class="text-red-600">Error: ${escapeHtml(error.message)}</p>`;
    }
}

/**
 * Load zones list
 */
async function loadZones(username, password) {
    try {
        const response = await fetch('/api/v1/czds/zones', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        // Check if response is OK
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.data) {
            // Update zones table
            updateZonesTable(data.data);
            showToast(`Loaded ${data.count} zones`, 'success');
        } else {
            const errorMsg = data.detail || data.message || 'Unknown error';
            console.error('Failed to load zones:', errorMsg);
            showToast('Failed to load zones: ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('Error loading zones:', error);
        showToast('Error loading zones: ' + error.message, 'error');
    }
}

/**
 * Update zones table with new data
 */
function updateZonesTable(zones) {
    const tbody = document.getElementById('zones-body');
    const emptyDiv = document.getElementById('zones-empty');
    const zonesSection = document.getElementById('zones-section');
    
    if (!zonesSection) return;
    
    // Show zones section
    zonesSection.style.display = 'block';
    
    if (zones.length === 0) {
        if (emptyDiv) emptyDiv.style.display = 'block';
        if (tbody) tbody.innerHTML = '';
        return;
    }
    
    if (emptyDiv) emptyDiv.style.display = 'none';
    
    if (!tbody) {
        // Create table if it doesn't exist
        const zonesSection = document.getElementById('zones-section');
        if (zonesSection) {
            zonesSection.innerHTML = `
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-2xl font-bold text-slate-900">Authorized Zones</h2>
                    <button id="refresh-zones" class="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200">
                        Refresh List
                    </button>
                </div>
                <div class="mb-4">
                    <p class="text-slate-600">Found <strong>${zones.length}</strong> authorized zone files</p>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead>
                            <tr class="bg-slate-50 border-b border-slate-200">
                                <th class="text-left py-3 px-4 text-slate-700 font-medium">Zone URL</th>
                                <th class="text-left py-3 px-4 text-slate-700 font-medium">TLD</th>
                                <th class="text-left py-3 px-4 text-slate-700 font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="zones-body"></tbody>
                    </table>
                </div>
            `;
        }
    }
    
    const newTbody = document.getElementById('zones-body');
    if (newTbody) {
        newTbody.innerHTML = zones.slice(0, 50).map(zoneUrl => {
            const parts = zoneUrl.split('/');
            const tld = parts[parts.length - 1].replace('.zone', '');
            return `
                <tr class="border-b border-slate-100 hover:bg-slate-50">
                    <td class="py-3 px-4 font-mono text-sm text-slate-900">${escapeHtml(zoneUrl)}</td>
                    <td class="py-3 px-4 text-slate-600">.${escapeHtml(tld)}</td>
                    <td class="py-3 px-4">
                        <div class="flex gap-2">
                            <button class="zone-info-btn px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm hover:bg-blue-200" 
                                data-url="${escapeHtml(zoneUrl)}">
                                Info
                            </button>
                            <button class="zone-download-btn px-3 py-1 bg-green-100 text-green-800 rounded text-sm hover:bg-green-200"
                                data-url="${escapeHtml(zoneUrl)}" data-tld="${escapeHtml(tld)}">
                                Download
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    // Re-initialize buttons
    initializeZoneButtons();
    initializeRefreshButtons();
}

/**
 * Download zone file
 */
async function downloadZone(zoneUrl, tld) {
    const storedUsername = localStorage.getItem('czds_username');
    const storedPassword = localStorage.getItem('czds_password');
    
    if (!storedUsername || !storedPassword) {
        showToast('Please authenticate first', 'error');
        return;
    }
    const statusDiv = document.getElementById('download-status');
    const messagesDiv = document.getElementById('download-messages');
    
    statusDiv.classList.remove('hidden');
    
    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = 'bg-blue-50 border border-blue-200 rounded-lg p-3';
    messageDiv.innerHTML = `
        <div class="flex items-center justify-between">
            <span>Downloading ${tld}...</span>
            <span class="animate-spin">⏳</span>
        </div>
    `;
    messagesDiv.appendChild(messageDiv);
    
    try {
        const response = await fetch('/api/v1/czds/download?auto_process=true', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                zone_url: zoneUrl,
                tld: tld,
                username: storedUsername,
                password: storedPassword
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            messageDiv.className = 'bg-green-50 border border-green-200 rounded-lg p-3';
            let processInfo = '';
            
            if (data.data.processed) {
                const proc = data.data.process_result || {};
                processInfo = `
                    <div class="mt-2 pt-2 border-t border-green-300">
                        <div class="text-sm">
                            <strong>Parsed:</strong> ${proc.sld_count || 0} domains found
                            ${proc.drops_detected ? `<br><strong>Drops:</strong> ${proc.dropped_count || 0} dropped, ${proc.persisted_count || 0} saved to DB` : ''}
                        </div>
                    </div>
                `;
            }
            
            messageDiv.innerHTML = `
                <div class="flex items-center justify-between">
                    <span>✓ Downloaded ${tld} successfully</span>
                    <span class="text-sm text-slate-600">${formatBytes(data.data.size)}</span>
                </div>
                <div class="text-sm text-slate-600 mt-1 font-mono">${escapeHtml(data.data.path)}</div>
                ${processInfo}
            `;
            
            // Store download in localStorage for persistence
            const downloadHistory = JSON.parse(localStorage.getItem('download_history') || '[]');
            downloadHistory.push({
                tld: tld,
                date: new Date().toISOString(),
                path: data.data.path,
                size: data.data.size,
                processed: data.data.processed || false,
                process_result: data.data.process_result || {}
            });
            // Keep only last 50 downloads
            if (downloadHistory.length > 50) {
                downloadHistory.shift();
            }
            localStorage.setItem('download_history', JSON.stringify(downloadHistory));
        } else {
            messageDiv.className = 'bg-red-50 border border-red-200 rounded-lg p-3';
            messageDiv.innerHTML = `
                <div>✗ Download failed: ${escapeHtml(data.detail || 'Unknown error')}</div>
            `;
        }
    } catch (error) {
        messageDiv.className = 'bg-red-50 border border-red-200 rounded-lg p-3';
        messageDiv.innerHTML = `
            <div>✗ Error: ${escapeHtml(error.message)}</div>
        `;
    }
}

/**
 * Initialize refresh buttons
 */
function initializeRefreshButtons() {
    const refreshTokenBtn = document.getElementById('refresh-token');
    const refreshZonesBtn = document.getElementById('refresh-zones');
    const closeModalBtn = document.getElementById('close-modal');
    const modal = document.getElementById('zone-info-modal');
    
    if (refreshTokenBtn) {
        refreshTokenBtn.addEventListener('click', function() {
            window.location.reload();
        });
    }
    
    if (refreshZonesBtn) {
        refreshZonesBtn.addEventListener('click', async function() {
            const storedUsername = localStorage.getItem('czds_username');
            const storedPassword = localStorage.getItem('czds_password');
            
            if (storedUsername && storedPassword) {
                await loadZones(storedUsername, storedPassword);
            } else {
                window.location.reload();
            }
        });
    }
    
    if (closeModalBtn && modal) {
        closeModalBtn.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
        
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
}

/**
 * Format bytes to human readable format
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    if (!toast || !toastMessage) return;
    
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500'
    };
    
    toast.className = `fixed bottom-4 right-4 ${colors[type] || colors.info} text-white px-6 py-3 rounded-lg shadow-lg`;
    toastMessage.textContent = message;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load and display download history from localStorage
 */
function loadDownloadHistory() {
    const downloadHistory = JSON.parse(localStorage.getItem('download_history') || '[]');
    const statusDiv = document.getElementById('download-status');
    const messagesDiv = document.getElementById('download-messages');
    
    if (!statusDiv || !messagesDiv) return;
    
    if (downloadHistory.length > 0) {
        statusDiv.classList.remove('hidden');
        messagesDiv.innerHTML = '';
        
        // Show last 10 downloads
        downloadHistory.slice(-10).reverse().forEach(download => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'bg-green-50 border border-green-200 rounded-lg p-3 mb-2';
            
            const processInfo = download.processed && download.process_result ? `
                <div class="mt-2 pt-2 border-t border-green-300">
                    <div class="text-sm">
                        <strong>Parsed:</strong> ${download.process_result.sld_count || 0} domains found
                        ${download.process_result.drops_detected ? `<br><strong>Drops:</strong> ${download.process_result.dropped_count || 0} dropped, ${download.process_result.persisted_count || 0} saved to DB` : ''}
                    </div>
                </div>
            ` : '';
            
            messageDiv.innerHTML = `
                <div class="flex items-center justify-between">
                    <span>✓ ${download.tld} (${new Date(download.date).toLocaleString()})</span>
                    <span class="text-sm text-slate-600">${formatBytes(download.size)}</span>
                </div>
                <div class="text-sm text-slate-600 mt-1 font-mono">${escapeHtml(download.path)}</div>
                ${processInfo}
            `;
            
            messagesDiv.appendChild(messageDiv);
        });
    }
}

