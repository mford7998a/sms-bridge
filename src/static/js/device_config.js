// Device Configuration Management
let currentDevice = null;
let originalConfig = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadDeviceConfig();
    initializeWebSocket();
});

// Load device configuration
async function loadDeviceConfig() {
    const deviceId = document.getElementById('deviceSelect').value;
    if (!deviceId) return;

    try {
        const response = await fetch(`/api/devices/${deviceId}/config`);
        if (!response.ok) throw new Error('Failed to load device configuration');
        
        const config = await response.json();
        currentDevice = config;
        originalConfig = {...config};
        
        // Update form fields
        updateFormFields(config);
        
        // Load device-specific settings
        await loadDeviceSpecificSettings(config.type);
        
        showNotification('Configuration loaded successfully', 'success');
    } catch (error) {
        console.error('Error loading configuration:', error);
        showNotification('Failed to load configuration', 'error');
    }
}

// Update form fields with configuration
function updateFormFields(config) {
    // Basic Settings
    document.getElementById('deviceName').value = config.name || '';
    document.getElementById('phoneNumber').value = config.phone_number || '';
    document.getElementById('connection').value = config.port || '';
    
    // Advanced Settings
    document.getElementById('baudrate').value = config.baudrate || '115200';
    document.getElementById('timeout').value = config.timeout || '30';
    document.getElementById('retryAttempts').value = config.retry_attempts || '3';
    
    // Network Settings
    document.getElementById('networkMode').value = config.network_mode || 'auto';
    updateBandSelection(config.preferred_bands || []);
    document.getElementById('allowRoaming').checked = config.allow_roaming || false;
    
    // Message Settings
    document.getElementById('messageFormat').value = config.message_format || 'text';
    document.getElementById('characterSet').value = config.character_set || 'GSM';
    document.getElementById('smscNumber').value = config.smsc_number || '';
    document.getElementById('deliveryReports').checked = config.delivery_reports || false;
}

// Load device-specific settings
async function loadDeviceSpecificSettings(deviceType) {
    const container = document.getElementById('deviceSpecificSettings');
    container.innerHTML = '';
    
    try {
        const response = await fetch(`/api/devices/settings/${deviceType}`);
        if (!response.ok) return;
        
        const settings = await response.json();
        const html = generateDeviceSpecificSettingsHTML(settings);
        container.innerHTML = html;
        
        // Initialize any special controls
        initializeDeviceSpecificControls(deviceType);
        
    } catch (error) {
        console.error('Error loading device-specific settings:', error);
    }
}

// Save configuration changes
async function saveAllConfigs() {
    try {
        const config = collectFormData();
        
        const response = await fetch(`/api/devices/${currentDevice.id}/config`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) throw new Error('Failed to save configuration');
        
        originalConfig = {...config};
        showNotification('Configuration saved successfully', 'success');
        
    } catch (error) {
        console.error('Error saving configuration:', error);
        showNotification('Failed to save configuration', 'error');
    }
}

// Reset configuration to original values
function resetAllConfigs() {
    if (!originalConfig) return;
    
    if (confirm('Are you sure you want to reset all settings to their original values?')) {
        updateFormFields(originalConfig);
        showNotification('Configuration reset to original values', 'info');
    }
}

// Test device connection
async function testConnection() {
    try {
        const response = await fetch(`/api/devices/${currentDevice.id}/test`);
        if (!response.ok) throw new Error('Connection test failed');
        
        const result = await response.json();
        showNotification(result.message, result.success ? 'success' : 'error');
        
    } catch (error) {
        console.error('Connection test error:', error);
        showNotification('Connection test failed', 'error');
    }
}

// Reset device
async function resetDevice() {
    if (!confirm('Are you sure you want to reset this device? This will interrupt any active connections.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/devices/${currentDevice.id}/reset`, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Device reset failed');
        
        showNotification('Device reset successfully', 'success');
        
        // Reload configuration after reset
        setTimeout(loadDeviceConfig, 5000);
        
    } catch (error) {
        console.error('Device reset error:', error);
        showNotification('Device reset failed', 'error');
    }
}

// Utility Functions
function collectFormData() {
    return {
        name: document.getElementById('deviceName').value,
        phone_number: document.getElementById('phoneNumber').value,
        port: document.getElementById('connection').value,
        baudrate: parseInt(document.getElementById('baudrate').value),
        timeout: parseInt(document.getElementById('timeout').value),
        retry_attempts: parseInt(document.getElementById('retryAttempts').value),
        network_mode: document.getElementById('networkMode').value,
        preferred_bands: getSelectedBands(),
        allow_roaming: document.getElementById('allowRoaming').checked,
        message_format: document.getElementById('messageFormat').value,
        character_set: document.getElementById('characterSet').value,
        smsc_number: document.getElementById('smscNumber').value,
        delivery_reports: document.getElementById('deliveryReports').checked,
        // Add device-specific settings
        ...collectDeviceSpecificSettings()
    };
}

function getSelectedBands() {
    const select = document.getElementById('preferredBands');
    return Array.from(select.selectedOptions).map(option => option.value);
}

function updateBandSelection(bands) {
    const select = document.getElementById('preferredBands');
    Array.from(select.options).forEach(option => {
        option.selected = bands.includes(option.value);
    });
}

// WebSocket handling for real-time updates
function initializeWebSocket() {
    wsClient.on('device_config_changed', (data) => {
        if (data.device_id === currentDevice?.id) {
            updateFormFields(data.config);
            showNotification('Device configuration updated externally', 'info');
        }
    });
} 