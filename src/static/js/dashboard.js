// Chart configurations and data
let messageActivityChart = null;
let signalStrengthChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    initializeWebSocket();
    refreshDeviceList();
});

// Chart Initialization
function initializeCharts() {
    // Message Activity Chart
    const messageCtx = document.getElementById('messageActivityChart').getContext('2d');
    messageActivityChart = new Chart(messageCtx, {
        type: 'line',
        data: {
            labels: [], // Will be populated with timestamps
            datasets: [{
                label: 'Messages Sent',
                data: [],
                borderColor: 'rgb(59, 130, 246)',
                tension: 0.4
            }, {
                label: 'Messages Received',
                data: [],
                borderColor: 'rgb(16, 185, 129)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Signal Strength Chart
    const signalCtx = document.getElementById('signalStrengthChart').getContext('2d');
    signalStrengthChart = new Chart(signalCtx, {
        type: 'line',
        data: {
            labels: [], // Will be populated with timestamps
            datasets: [] // Will be populated with device data
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// WebSocket Handling
function initializeWebSocket() {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketUpdate(data);
    };

    ws.onclose = function() {
        console.log('WebSocket connection closed');
        setTimeout(initializeWebSocket, 5000); // Reconnect after 5 seconds
    };
}

function handleWebSocketUpdate(data) {
    switch(data.type) {
        case 'device_update':
            updateDeviceStatus(data.device);
            updateSignalStrength(data.device);
            break;
        case 'message_activity':
            updateMessageActivity(data.data);
            break;
        case 'system_status':
            updateSystemStatus(data.status);
            break;
        case 'error':
            showNotification(data.message, 'error');
            break;
    }
}

// Device Management
async function showAddDevice() {
    const modal = document.getElementById('addDeviceModal');
    modal.classList.remove('hidden');
    await refreshPortList();
}

async function refreshPortList() {
    try {
        const response = await fetch('/api/ports');
        const ports = await response.json();
        
        const select = document.querySelector('select[name="port"]');
        select.innerHTML = ports.map(port => 
            `<option value="${port}">${port}</option>`
        ).join('');
    } catch (error) {
        console.error('Error refreshing port list:', error);
        showNotification('Failed to refresh port list', 'error');
    }
}

async function addDevice(form) {
    try {
        const formData = new FormData(form);
        const response = await fetch('/api/devices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(Object.fromEntries(formData))
        });
        
        if (!response.ok) throw new Error('Failed to add device');
        
        showNotification('Device added successfully', 'success');
        hideModal('addDeviceModal');
        refreshDeviceList();
    } catch (error) {
        console.error('Error adding device:', error);
        showNotification('Failed to add device', 'error');
    }
}

async function removeDevice(deviceId) {
    if (!confirm('Are you sure you want to remove this device?')) return;
    
    try {
        const response = await fetch(`/api/devices/${deviceId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) throw new Error('Failed to remove device');
        
        showNotification('Device removed successfully', 'success');
        refreshDeviceList();
    } catch (error) {
        console.error('Error removing device:', error);
        showNotification('Failed to remove device', 'error');
    }
}

// Chart Updates
function updateMessageActivity(data) {
    messageActivityChart.data.labels = data.labels;
    messageActivityChart.data.datasets[0].data = data.sent;
    messageActivityChart.data.datasets[1].data = data.received;
    messageActivityChart.update();
}

function updateSignalStrength(device) {
    // Find or create dataset for device
    let dataset = signalStrengthChart.data.datasets.find(ds => ds.label === device.id);
    if (!dataset) {
        dataset = {
            label: device.id,
            data: [],
            borderColor: getRandomColor(),
            tension: 0.4
        };
        signalStrengthChart.data.datasets.push(dataset);
    }
    
    // Add new data point
    const now = new Date().toLocaleTimeString();
    if (!signalStrengthChart.data.labels.includes(now)) {
        signalStrengthChart.data.labels.push(now);
    }
    dataset.data.push(device.signal_strength);
    
    // Keep last 20 data points
    if (signalStrengthChart.data.labels.length > 20) {
        signalStrengthChart.data.labels.shift();
        dataset.data.shift();
    }
    
    signalStrengthChart.update();
}

// Utility Functions
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    const container = document.getElementById('toastContainer');
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
} 