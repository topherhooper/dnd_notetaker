// Audio Extraction Dashboard JavaScript

const API_BASE = '/api';
const REFRESH_INTERVAL = 5000; // 5 seconds

let refreshTimer = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    setupEventListeners();
    startAutoRefresh();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('refresh-btn').addEventListener('click', loadDashboard);
    document.getElementById('cleanup-btn').addEventListener('click', cleanupOldEntries);
    document.getElementById('export-btn').addEventListener('click', exportStatistics);
    document.getElementById('clear-failed-btn').addEventListener('click', clearFailedJobs);
}

// Start auto-refresh
function startAutoRefresh() {
    refreshTimer = setInterval(loadDashboard, REFRESH_INTERVAL);
}

// Load dashboard data
async function loadDashboard() {
    try {
        updateConnectionStatus(true);
        
        // Load health status
        try {
            const health = await fetchAPI('/health');
            updateHealthStatus(health);
        } catch (error) {
            console.error('Failed to load health status:', error);
        }
        
        // Load statistics
        const stats = await fetchAPI('/stats');
        updateStatistics(stats);
        
        // Load recent videos
        const recent = await fetchAPI('/recent?days=7');
        updateRecentTable(recent);
        
        // Load failed videos
        const failed = await fetchAPI('/failed');
        updateFailedTable(failed);
        
        updateLastUpdate();
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        updateConnectionStatus(false);
    }
}

// Fetch from API
async function fetchAPI(endpoint) {
    const response = await fetch(API_BASE + endpoint);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// Update statistics
function updateStatistics(stats) {
    document.getElementById('stat-total').textContent = stats.total || 0;
    document.getElementById('stat-completed').textContent = stats.completed || 0;
    document.getElementById('stat-failed').textContent = stats.failed || 0;
    document.getElementById('stat-success-rate').textContent = `${stats.success_rate || 0}%`;
}

// Update health status
function updateHealthStatus(health) {
    const statusIcons = {
        'healthy': '🟢',
        'unhealthy': '🔴',
        'warning': '🟡',
        'unknown': '⚪'
    };
    
    // Update each component
    for (const [component, info] of Object.entries(health.components || {})) {
        const icon = document.getElementById(`health-${component}`);
        const msg = document.getElementById(`health-${component}-msg`);
        
        if (icon && msg) {
            icon.textContent = statusIcons[info.status] || statusIcons['unknown'];
            msg.textContent = info.message || 'Unknown';
        }
    }
}

// Update recent videos table
function updateRecentTable(videos) {
    const tbody = document.getElementById('recent-tbody');
    
    if (videos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No recent videos</td></tr>';
        return;
    }
    
    tbody.innerHTML = videos.map(video => {
        // Generate audio link HTML
        let audioLinkHtml = '-';
        if (video.storage_url && video.status === 'completed') {
            const fileName = video.storage_path ? video.storage_path.split('/').pop() : 'audio.mp3';
            audioLinkHtml = `
                <div class="audio-link">
                    <a href="${escapeHtml(video.storage_url)}" target="_blank" title="Download ${fileName}">
                        📥 ${truncateText(fileName, 20)}
                    </a>
                    <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(video.storage_url)}', this)" title="Copy URL">
                        📋
                    </button>
                </div>
            `;
        }
        
        return `
            <tr>
                <td title="${escapeHtml(video.file_path)}">${truncatePath(video.file_path)}</td>
                <td><span class="status-badge ${video.status}">${video.status}</span></td>
                <td>${formatDate(video.processed_at)}</td>
                <td>${video.metadata?.duration ? formatDuration(video.metadata.duration) : '-'}</td>
                <td>${audioLinkHtml}</td>
                <td>
                    ${video.status === 'failed' ? 
                        `<button class="btn btn-sm btn-primary" onclick="reprocessVideo('${escapeHtml(video.file_path)}')">Retry</button>` :
                        '-'
                    }
                </td>
            </tr>
        `;
    }).join('');
}

// Update failed videos table
function updateFailedTable(videos) {
    const tbody = document.getElementById('failed-tbody');
    
    if (videos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No failed jobs</td></tr>';
        return;
    }
    
    tbody.innerHTML = videos.map(video => `
        <tr>
            <td title="${escapeHtml(video.file_path)}">${truncatePath(video.file_path)}</td>
            <td title="${escapeHtml(video.metadata?.error || 'Unknown error')}">
                ${truncateText(video.metadata?.error || 'Unknown error', 50)}
            </td>
            <td>${formatDate(video.processed_at)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="reprocessVideo('${escapeHtml(video.file_path)}')">Retry</button>
            </td>
        </tr>
    `).join('');
}

// Reprocess video
async function reprocessVideo(filePath) {
    try {
        const response = await fetch(`${API_BASE}/reprocess`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({file_path: filePath})
        });
        
        if (response.ok) {
            alert('Video marked for reprocessing');
            loadDashboard();
        } else {
            alert('Failed to mark video for reprocessing');
        }
    } catch (error) {
        console.error('Failed to reprocess video:', error);
        alert('Error: ' + error.message);
    }
}

// Cleanup old entries
async function cleanupOldEntries() {
    if (!confirm('Remove all entries older than 90 days?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/cleanup`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({days: 90})
        });
        
        const result = await response.json();
        alert(`Removed ${result.deleted} old entries`);
        loadDashboard();
    } catch (error) {
        console.error('Failed to cleanup:', error);
        alert('Error: ' + error.message);
    }
}

// Clear failed jobs
async function clearFailedJobs() {
    if (!confirm('Clear all failed jobs?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/clear-failed`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Failed jobs cleared');
            loadDashboard();
        }
    } catch (error) {
        console.error('Failed to clear failed jobs:', error);
        alert('Error: ' + error.message);
    }
}

// Export statistics
function exportStatistics() {
    // Create CSV content
    const stats = {
        total: document.getElementById('stat-total').textContent,
        completed: document.getElementById('stat-completed').textContent,
        failed: document.getElementById('stat-failed').textContent,
        success_rate: document.getElementById('stat-success-rate').textContent
    };
    
    const csv = `Metric,Value
Total Processed,${stats.total}
Completed,${stats.completed}
Failed,${stats.failed}
Success Rate,${stats.success_rate}
Export Date,${new Date().toISOString()}`;
    
    // Download CSV
    const blob = new Blob([csv], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audio_extraction_stats_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// Utility functions
function updateConnectionStatus(connected) {
    const dot = document.getElementById('connection-status');
    dot.className = `status-dot ${connected ? '' : 'error'}`;
}

function updateLastUpdate() {
    const now = new Date().toLocaleTimeString();
    document.getElementById('last-update').textContent = `Last update: ${now}`;
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function truncatePath(path, maxLength = 50) {
    if (path.length <= maxLength) return path;
    return '...' + path.slice(-(maxLength - 3));
}

function truncateText(text, maxLength = 50) {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - 3) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Copy URL to clipboard
async function copyToClipboard(url, button) {
    try {
        await navigator.clipboard.writeText(url);
        
        // Visual feedback
        button.classList.add('copied');
        button.textContent = '✓';
        
        setTimeout(() => {
            button.classList.remove('copied');
            button.textContent = '📋';
        }, 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
        alert('Failed to copy URL to clipboard');
    }
}

// Refresh expired URL
async function refreshURL(storagePath, linkElement) {
    try {
        const response = await fetch(`${API_BASE}/refresh-url`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({storage_path: storagePath})
        });
        
        if (response.ok) {
            const result = await response.json();
            linkElement.href = result.url;
            return result.url;
        } else {
            throw new Error('Failed to refresh URL');
        }
    } catch (error) {
        console.error('Failed to refresh URL:', error);
        alert('Failed to refresh URL: ' + error.message);
    }
}