// Modal Controls
function showModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function hideModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

// Device Management
function showAddDevice() {
    showModal('addDeviceModal');
    refreshPortList();
}

function showDeviceStats(deviceId) {
    showModal('deviceStatsModal');
    loadDeviceStats(deviceId);
}

function showSystemLogs() {
    showModal('systemLogsModal');
    loadSystemLogs();
}

function showSettings() {
    showModal('settingsModal');
    loadCurrentSettings();
}

// AJAX Functions
async function refreshPortList() {
    const response = await fetch('/api/ports');
    const ports = await response.json();
    const select = document.querySelector('select[name="port"]');
    select.innerHTML = ports.map(port => 
        `<option value="${port}">${port}</option>`
    ).join('');
}

async function loadDeviceStats(deviceId) {
    const response = await fetch(`/api/devices/${deviceId}/stats`);
    const stats = await response.json();
    updateDeviceCharts(stats);
}

async function loadSystemLogs() {
    const level = document.getElementById('logLevel').value;
    const search = document.getElementById('logSearch').value;
    const response = await fetch(`/api/logs?level=${level}&search=${search}`);
    const logs = await response.json();
    updateLogWindow(logs);
}

async function loadCurrentSettings() {
    const response = await fetch('/api/settings');
    const settings = await response.json();
    populateSettingsForm(settings);
}

// Chart Updates
function updateDeviceCharts(stats) {
    signalChart.data.labels = stats.timestamps;
    signalChart.data.datasets[0].data = stats.signal_values;
    signalChart.update();

    messageChart.data.datasets[0].data = [
        stats.messages.received,
        stats.messages.delivered,
        stats.messages.failed,
        stats.messages.pending
    ];
    messageChart.update();
}

// Device Operations
async function removeDevice(deviceId) {
    if (!confirm('Are you sure you want to remove this device?')) return;
    
    const response = await fetch(`/api/devices/${deviceId}`, {
        method: 'DELETE'
    });
    
    if (response.ok) {
        document.querySelector(`#device-${deviceId}`).remove();
        showNotification('Device removed successfully', 'success');
    } else {
        showNotification('Failed to remove device', 'error');
    }
}

async function configureDevice(deviceId) {
    const device = document.querySelector(`#device-${deviceId}`);
    const deviceType = device.dataset.type;
    window.location.href = `/${deviceType}-config?device=${deviceId}`;
}

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initializeCharts();
    
    // Set up real-time updates
    setupRealtimeUpdates();
    
    // Initialize event listeners
    setupEventListeners();
}); 