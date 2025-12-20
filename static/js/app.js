/**
 * Client-side JavaScript for ExpiredDomain.dev
 * Handles filtering, pagination, and clipboard copy functionality.
 */

let currentPage = 1;
let currentFilters = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeFilters();
    initializeCopyButtons();
    initializePagination();
});

/**
 * Initialize filter form and TLD buttons
 */
function initializeFilters() {
    const filterForm = document.getElementById('filter-form');
    const tldButtons = document.querySelectorAll('.tld-filter');
    const tldInput = document.getElementById('tld-filter');
    
    // TLD button clicks
    tldButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Update active state
            tldButtons.forEach(btn => {
                btn.classList.remove('bg-slate-900', 'text-white', 'border-slate-900');
                btn.classList.add('bg-white', 'text-slate-700');
            });
            this.classList.remove('bg-white', 'text-slate-700');
            this.classList.add('bg-slate-900', 'text-white', 'border-slate-900');
            
            // Update hidden input
            tldInput.value = this.dataset.tld;
        });
    });
    
    // Form submission
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        currentPage = 1;
        fetchDrops();
    });
}

/**
 * Fetch drops from API with current filters
 */
function fetchDrops() {
    const formData = new FormData(document.getElementById('filter-form'));
    const params = new URLSearchParams();
    
    // Build query params
    params.append('page', currentPage.toString());
    params.append('page_size', '50');
    
    if (formData.get('date')) {
        params.append('date', formData.get('date'));
    }
    if (formData.get('tld')) {
        params.append('tld', formData.get('tld'));
    }
    if (formData.get('search')) {
        params.append('search', formData.get('search'));
    }
    if (formData.get('min_length')) {
        params.append('min_length', formData.get('min_length'));
    }
    if (formData.get('max_length')) {
        params.append('max_length', formData.get('max_length'));
    }
    if (formData.get('charset_type')) {
        params.append('charset_type', formData.get('charset_type'));
    }
    
    // Show loading state
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '<tr><td colspan="6" class="py-8 text-center text-slate-500">Loading...</td></tr>';
    
    // Fetch from API
    fetch(`/api/v1/drops?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            renderResults(data);
            updatePagination(data);
            updateSummary(data);
        })
        .catch(error => {
            console.error('Error fetching drops:', error);
            tbody.innerHTML = '<tr><td colspan="6" class="py-8 text-center text-red-500">Error loading data. Please try again.</td></tr>';
        });
}

/**
 * Render results into table
 */
function renderResults(data) {
    const tbody = document.getElementById('results-body');
    
    if (data.results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="py-8 text-center text-slate-500">No results found.</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.results.map(drop => {
        const charsetClass = drop.charset_type === 'letters' 
            ? 'bg-blue-100 text-blue-800'
            : drop.charset_type === 'numbers'
            ? 'bg-green-100 text-green-800'
            : 'bg-purple-100 text-purple-800';
        
        return `
            <tr class="border-b border-slate-100 hover:bg-slate-50">
                <td class="py-3 px-4 font-mono text-slate-900">${escapeHtml(drop.domain)}</td>
                <td class="py-3 px-4 text-slate-600">.${escapeHtml(drop.tld)}</td>
                <td class="py-3 px-4 text-slate-600">${drop.drop_date}</td>
                <td class="py-3 px-4 text-slate-600">${drop.length}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-1 rounded text-xs font-medium ${charsetClass}">
                        ${escapeHtml(drop.charset_type)}
                    </span>
                </td>
                <td class="py-3 px-4">
                    <button class="copy-btn px-3 py-1 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 text-sm" data-domain="${escapeHtml(drop.domain)}">
                        Copy
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Re-initialize copy buttons
    initializeCopyButtons();
}

/**
 * Update pagination controls
 */
function updatePagination(data) {
    const totalPages = Math.ceil(data.total / data.page_size);
    document.getElementById('current-page').textContent = data.page;
    document.getElementById('total-pages').textContent = totalPages || 1;
    
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    prevBtn.disabled = data.page <= 1;
    nextBtn.disabled = data.page >= totalPages;
}

/**
 * Update summary text
 */
function updateSummary(data) {
    const summary = document.getElementById('summary');
    const resultCount = document.getElementById('result-count');
    
    if (resultCount) {
        resultCount.textContent = data.total;
    }
}

/**
 * Initialize pagination buttons
 */
function initializePagination() {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                fetchDrops();
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            currentPage++;
            fetchDrops();
        });
    }
}

/**
 * Initialize copy-to-clipboard buttons
 */
function initializeCopyButtons() {
    const copyButtons = document.querySelectorAll('.copy-btn');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const domain = this.dataset.domain;
            copyToClipboard(domain);
        });
    });
}

/**
 * Copy text to clipboard and show toast
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy');
    });
}

/**
 * Show toast notification
 */
function showToast(message) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    toastMessage.textContent = message;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 2000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}









