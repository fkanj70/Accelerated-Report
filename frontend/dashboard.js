// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const refreshBtn = document.getElementById('refreshBtn');
const reportsList = document.getElementById('reportsList');
const totalReports = document.getElementById('totalReports');
const crashCount = document.getElementById('crashCount');
const slowCount = document.getElementById('slowCount');
const bugCount = document.getElementById('bugCount');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadReports();
    
    refreshBtn.addEventListener('click', () => {
        loadReports();
    });
    
    // Auto-refresh every 10 seconds
    setInterval(loadReports, 10000);
});

// Load reports from API
async function loadReports() {
    try {
        const response = await fetch(`${API_BASE_URL}/reports`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        displayReports(data.reports);
        updateStats(data.reports);
        
    } catch (error) {
        console.error('Failed to load reports:', error);
        reportsList.innerHTML = `
            <div class="error">
                ❌ Failed to load reports. Make sure the backend is running.
            </div>
        `;
    }
}

// Display reports
function displayReports(reports) {
    if (reports.length === 0) {
        reportsList.innerHTML = '<div class="empty">No reports yet. Submit your first report!</div>';
        return;
    }
    
    reportsList.innerHTML = reports.map(report => `
        <div class="report-card">
            <div class="report-header">
                <span class="report-type ${report.type}">
                    ${getTypeEmoji(report.type)} ${report.type.toUpperCase()}
                </span>
                <span class="report-id">ID: ${report.id.substring(0, 8)}</span>
                <span class="report-time">${formatTime(report.created_at)}</span>
            </div>
            
            <div class="report-message">
                ${report.message}
            </div>
            
            <div class="report-meta">
                <span>📱 ${report.platform || 'web'}</span>
                <span>📦 v${report.app_version || '1.0.0'}</span>
                <span class="status-badge ${report.status}">${report.status}</span>
            </div>
            
            ${report.description ? `
                <div class="report-enrichment">
                    <strong>🤖 AI Analysis:</strong> ${report.description}<br>
                    <strong>Severity:</strong> <span class="severity ${report.severity}">${report.severity || 'unknown'}</span><br>
                    <strong>Category:</strong> ${report.category || 'unknown'}<br>
                    ${report.developer_action ? `<strong>Action:</strong> ${report.developer_action}<br>` : ''}
                    <strong>Confidence:</strong> ${formatConfidence(report.confidence)}
                </div>
            ` : ''}
            
            ${report.helpful_resources && report.helpful_resources.length > 0 ? `
                <div class="helpful-resources">
                    <strong>🔗 Helpful Resources (via Yellowcake):</strong>
                    <ul>
                        ${report.helpful_resources.map(resource => `
                            <li>
                                <a href="${resource.url}" target="_blank" rel="noopener">${resource.title}</a>
                                <span class="resource-type">${resource.type}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${report.sentry_event_id ? `
                <div class="sentry-link">
                    <strong>🔍 Sentry Event:</strong> <code>${report.sentry_event_id}</code>
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Update statistics
function updateStats(reports) {
    totalReports.textContent = reports.length;
    
    const counts = {
        crash: 0,
        slow: 0,
        bug: 0,
        suggestion: 0,
    };
    
    reports.forEach(report => {
        if (counts.hasOwnProperty(report.type)) {
            counts[report.type]++;
        }
    });
    
    crashCount.textContent = counts.crash;
    slowCount.textContent = counts.slow;
    bugCount.textContent = counts.bug;
}

// Helper functions
function getTypeEmoji(type) {
    const emojis = {
        crash: '🔴',
        slow: '🟡',
        bug: '🐛',
        suggestion: '💡',
    };
    return emojis[type] || '📝';
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatConfidence(confidence) {
    if (!confidence) return 'N/A';
    const percent = Math.round(confidence * 100);
    return `${percent}%`;
}
