// Configuration
const API_BASE_URL = 'http://localhost:8000';
const QUEUE_KEY = 'accelerated_reports_queue';
const RECENT_KEY = 'accelerated_reports_recent';

// State
let chaosMode = false;
let retryInterval = null;

// DOM Elements
const form = document.getElementById('reportForm');
const submitBtn = document.getElementById('submitBtn');
const statusMessage = document.getElementById('statusMessage');
const chaosModeToggle = document.getElementById('chaosMode');
const queueStatus = document.getElementById('queueStatus');
const queueCount = document.getElementById('queueCount');
const recentList = document.getElementById('recentList');
const quickDescription = document.getElementById('quickDescription');
const screenshotInput = document.getElementById('screenshot');
const screenshotPreview = document.getElementById('screenshotPreview');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadQueue();
    loadRecent();
    startQueueProcessor();
    
    chaosModeToggle.addEventListener('change', (e) => {
        chaosMode = e.target.checked;
        showStatus(chaosMode ? '⚠️ Chaos Mode Enabled' : '✅ Normal Mode', chaosMode ? 'warning' : 'success');
    });

    // Screenshot preview
    screenshotInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                screenshotPreview.innerHTML = `<img src="${e.target.result}" alt="Screenshot">`;
                screenshotPreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    });

    // Quick action buttons
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const type = e.currentTarget.dataset.type;
            const message = e.currentTarget.dataset.message;
            
            // Visual feedback
            e.currentTarget.classList.add('clicked');
            setTimeout(() => e.currentTarget.classList.remove('clicked'), 300);
            
            // Get optional context
            const description = quickDescription.value.trim();
            
            // Auto-capture screenshot
            let screenshotData = null;
            try {
                const screenshotBlob = await captureScreenshot();
                if (screenshotBlob) {
                    // Convert to base64 for JSON transmission
                    screenshotData = await blobToBase64(screenshotBlob);
                    showStatus('📸 Screenshot captured!', 'success');
                    
                    // Show preview
                    screenshotPreview.innerHTML = `<img src="${screenshotData}" alt="Screenshot">`;
                    screenshotPreview.classList.remove('hidden');
                }
            } catch (err) {
                console.log('Screenshot capture not available:', err);
            }
            
            await submitReport({
                type: type,
                message: description ? `${message}. Note: ${description}` : message,
                platform: detectPlatform(),
                app_version: '1.0.0',
                screenshot: screenshotData,  // base64 string
            }, true); // true = quick action
            
            // Clear context after submit
            quickDescription.value = '';
            screenshotInput.value = '';
            screenshotPreview.innerHTML = '';
            screenshotPreview.classList.add('hidden');
        });
    });
});

// Auto-capture screenshot using html2canvas or fallback
async function captureScreenshot() {
    try {
        // Method 1: Try to use html2canvas if available
        if (typeof html2canvas !== 'undefined') {
            const canvas = await html2canvas(document.body);
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
            return blob;
        }
        
        // Method 2: Try DisplayMediaCapture API (screen capture)
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
            const stream = await navigator.mediaDevices.getDisplayMedia({ 
                video: { mediaSource: 'screen' } 
            });
            
            const video = document.createElement('video');
            video.srcObject = stream;
            video.play();
            
            // Wait for video to be ready
            await new Promise(resolve => {
                video.onloadedmetadata = resolve;
            });
            
            // Capture frame
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            
            // Stop stream
            stream.getTracks().forEach(track => track.stop());
            
            const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
            return blob;
        }
        
        // Method 3: Check if manual file was uploaded
        if (screenshotInput.files[0]) {
            return screenshotInput.files[0];
        }
        
        return null;
    } catch (err) {
        console.log('Screenshot capture failed:', err);
        // Try manual upload as fallback
        if (screenshotInput.files[0]) {
            return screenshotInput.files[0];
        }
        return null;
    }
}

// Convert blob to base64
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// Auto-detect platform
function detectPlatform() {
    const ua = navigator.userAgent;
    if (/iPad|iPhone|iPod/.test(ua)) return 'ios';
    if (/Android/.test(ua)) return 'android';
    return 'web';
}

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const reportData = {
        type: document.getElementById('reportType').value,
        message: document.getElementById('message').value || document.getElementById('reportType').selectedOptions[0].textContent,
        platform: detectPlatform(),
        app_version: '1.0.0',
    };
    
    await submitReport(reportData, false);
});

// Submit report with chaos mode simulation and AI enrichment
async function submitReport(reportData, isQuickAction = false) {
    if (submitBtn) submitBtn.disabled = true;
    setStatus('Sending…');
    showStatus('📤 Sending...', 'info');
    
    try {
        // Chaos mode: simulate random failures
        if (chaosMode && Math.random() < 0.3) {
            throw new Error('Simulated network failure (Chaos Mode)');
        }
        
        // Chaos mode: simulate delay
        if (chaosMode && Math.random() < 0.3) {
            await new Promise(resolve => setTimeout(resolve, 800));
        }
        
        const response = await fetch(`${API_BASE_URL}/reports`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(reportData),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        // Show AI enrichment result if available
        if (result.ai_enriched) {
            showStatus(`✅ Sent! AI detected: ${result.category || 'analyzing'}`, 'success');
        } else {
            showStatus(`✅ Report sent!`, 'success');
        }
        
        addToRecent(reportData, result.report_id);
        if (form) form.reset();
        
    } catch (error) {
        console.error('Submit failed:', error);
        
        // Queue the report for retry
        queueReport(reportData);
        showStatus('⏳ Queued - will retry automatically', 'warning');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

// Queue management
function queueReport(reportData) {
    const queue = getQueue();
    queue.push({
        ...reportData,
        queued_at: new Date().toISOString(),
        retry_count: 0,
    });
    saveQueue(queue);
    updateQueueUI();
}

function getQueue() {
    const stored = localStorage.getItem(QUEUE_KEY);
    return stored ? JSON.parse(stored) : [];
}

function saveQueue(queue) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

function loadQueue() {
    updateQueueUI();
}

function updateQueueUI() {
    const queue = getQueue();
    queueCount.textContent = queue.length;
    
    if (queue.length > 0) {
        queueStatus.classList.remove('hidden');
    } else {
        queueStatus.classList.add('hidden');
    }
}

// Queue processor (auto-retry)
function startQueueProcessor() {
    retryInterval = setInterval(async () => {
        const queue = getQueue();
        
        if (queue.length === 0) return;
        
        console.log(`Processing queue: ${queue.length} items`);
        
        // Process one item at a time
        const item = queue[0];
        
        try {
            const response = await fetch(`${API_BASE_URL}/reports`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: item.type,
                    message: item.message,
                    platform: item.platform,
                    app_version: item.app_version,
                    screenshot: item.screenshot || null,
                }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            // Success - remove from queue
            queue.shift();
            saveQueue(queue);
            updateQueueUI();
            
            setStatus('Recovered ✅ (delivered)');
            showStatus(`✅ Queued report delivered! ID: ${result.report_id.substring(0, 8)}...`, 'success');
            addToRecent(item, result.report_id);
            
        } catch (error) {
            console.error('Retry failed:', error);
            
            // Increment retry count
            item.retry_count = (item.retry_count || 0) + 1;
            
            // If too many retries, give up
            if (item.retry_count > 10) {
                queue.shift();
                saveQueue(queue);
                updateQueueUI();
                showStatus('❌ Report failed after 10 retries. Discarded.', 'error');
            } else {
                // Update queue with new retry count
                queue[0] = item;
                saveQueue(queue);
            }
        }
    }, 5000); // Retry every 5 seconds
}

// Recent submissions
function addToRecent(reportData, reportId) {
    const recent = getRecent();
    recent.unshift({
        id: reportId,
        type: reportData.type,
        message: reportData.message,
        timestamp: new Date().toISOString(),
    });
    
    // Keep only last 5
    if (recent.length > 5) {
        recent.pop();
    }
    
    saveRecent(recent);
    displayRecent();
}

function getRecent() {
    const stored = localStorage.getItem(RECENT_KEY);
    return stored ? JSON.parse(stored) : [];
}

function saveRecent(recent) {
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
}

function loadRecent() {
    displayRecent();
}

function displayRecent() {
    const recent = getRecent();
    
    if (recent.length === 0) {
        recentList.innerHTML = '<p class="empty">No recent submissions</p>';
        return;
    }
    
    recentList.innerHTML = recent.map(item => `
        <div class="recent-item">
            <span class="recent-type ${item.type}">${getTypeEmoji(item.type)} ${item.type}</span>
            <span class="recent-message">${truncate(item.message, 50)}</span>
            <span class="recent-time">${formatTime(item.timestamp)}</span>
        </div>
    `).join('');
}

// UI helpers
function showStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
    
    // Auto-hide success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            statusMessage.classList.add('hidden');
        }, 5000);
    }
}

function getTypeEmoji(type) {
    const emojis = {
        crash: '🔴',
        slow: '🟡',
        bug: '🐛',
        suggestion: '💡',
    };
    return emojis[type] || '📝';
}

function truncate(str, length) {
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}
