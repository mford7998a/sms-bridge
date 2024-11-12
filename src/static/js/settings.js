// Settings Management
let originalSettings = null;
let hasUnsavedChanges = false;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    setupEventListeners();
    initializeWebSocket();
});

// Event Listeners
function setupEventListeners() {
    // Track changes
    document.querySelectorAll('input, select').forEach(element => {
        element.addEventListener('change', () => {
            hasUnsavedChanges = true;
            updateSaveButton();
        });
    });

    // Theme changes
    document.getElementById('theme').addEventListener('change', function() {
        applyTheme(this.value);
    });

    // Prevent accidental navigation
    window.addEventListener('beforeunload', function(e) {
        if (hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
}

// Settings Loading
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) throw new Error('Failed to load settings');
        
        const settings = await response.json();
        originalSettings = {...settings};
        
        updateFormFields(settings);
        showNotification('Settings loaded successfully', 'success');
        
    } catch (error) {
        console.error('Load settings error:', error);
        showNotification('Failed to load settings', 'error');
    }
}

function updateFormFields(settings) {
    // General Settings
    document.getElementById('systemName').value = settings.system_name || '';
    document.getElementById('adminEmail').value = settings.admin_email || '';
    document.getElementById('theme').value = settings.theme || 'system';
    document.getElementById('language').value = settings.language || 'en';

    // SMS Hub Settings
    document.getElementById('smsHubApiKey').value = settings.smshub_api_key || '';
    document.getElementById('smsHubBaseUrl').value = settings.smshub_base_url || '';
    document.getElementById('smsHubRetries').value = settings.smshub_retries || 3;
    document.getElementById('smsHubTimeout').value = settings.smshub_timeout || 30;

    // Device Settings
    document.getElementById('deviceScanInterval').value = settings.device_scan_interval || 5;
    document.getElementById('messageCheckInterval').value = settings.message_check_interval || 10;
    document.getElementById('defaultBaudrate').value = settings.default_baudrate || '115200';
    document.getElementById('autoReconnect').checked = settings.auto_reconnect || false;

    // Notification Settings
    document.getElementById('notifyErrors').checked = settings.notify_errors || false;
    document.getElementById('notifyDeviceStatus').checked = settings.notify_device_status || false;
    document.getElementById('notifyLowBalance').checked = settings.notify_low_balance || false;
    document.getElementById('notificationEmail').value = settings.notification_email || '';
    document.getElementById('lowBalanceThreshold').value = settings.low_balance_threshold || 0;

    // Advanced Settings
    document.getElementById('logLevel').value = settings.log_level || 'INFO';
    document.getElementById('logRetention').value = settings.log_retention || 30;
    document.getElementById('enableBackup').checked = settings.enable_backup || false;
    document.getElementById('backupInterval').value = settings.backup_interval || 24;
    document.getElementById('backupLocation').value = settings.backup_location || '';

    // Apply theme
    applyTheme(settings.theme);
}

// Settings Saving
async function saveAllSettings() {
    try {
        const settings = collectFormData();
        
        const response = await fetch('/api/settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) throw new Error('Failed to save settings');
        
        originalSettings = {...settings};
        hasUnsavedChanges = false;
        updateSaveButton();
        
        showNotification('Settings saved successfully', 'success');
        
    } catch (error) {
        console.error('Save settings error:', error);
        showNotification('Failed to save settings', 'error');
    }
}

function collectFormData() {
    return {
        system_name: document.getElementById('systemName').value,
        admin_email: document.getElementById('adminEmail').value,
        theme: document.getElementById('theme').value,
        language: document.getElementById('language').value,
        
        smshub_api_key: document.getElementById('smsHubApiKey').value,
        smshub_base_url: document.getElementById('smsHubBaseUrl').value,
        smshub_retries: parseInt(document.getElementById('smsHubRetries').value),
        smshub_timeout: parseInt(document.getElementById('smsHubTimeout').value),
        
        device_scan_interval: parseInt(document.getElementById('deviceScanInterval').value),
        message_check_interval: parseInt(document.getElementById('messageCheckInterval').value),
        default_baudrate: document.getElementById('defaultBaudrate').value,
        auto_reconnect: document.getElementById('autoReconnect').checked,
        
        notify_errors: document.getElementById('notifyErrors').checked,
        notify_device_status: document.getElementById('notifyDeviceStatus').checked,
        notify_low_balance: document.getElementById('notifyLowBalance').checked,
        notification_email: document.getElementById('notificationEmail').value,
        low_balance_threshold: parseFloat(document.getElementById('lowBalanceThreshold').value),
        
        log_level: document.getElementById('logLevel').value,
        log_retention: parseInt(document.getElementById('logRetention').value),
        enable_backup: document.getElementById('enableBackup').checked,
        backup_interval: parseInt(document.getElementById('backupInterval').value),
        backup_location: document.getElementById('backupLocation').value
    };
}

// Reset Settings
function resetAllSettings() {
    if (!confirm('Are you sure you want to reset all settings to their original values?')) {
        return;
    }
    
    updateFormFields(originalSettings);
    hasUnsavedChanges = false;
    updateSaveButton();
    showNotification('Settings reset to original values', 'info');
}

// Theme Management
function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'system') {
        theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
}

// Import/Export Settings
function exportSettings() {
    const settings = collectFormData();
    const blob = new Blob([JSON.stringify(settings, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `sms-bridge-settings-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function importSettings() {
    showModal('importSettingsModal');
}

async function confirmImport() {
    const fileInput = document.getElementById('settingsFile');
    const overwrite = document.getElementById('overwriteExisting').checked;
    
    if (!fileInput.files.length) {
        showNotification('Please select a file to import', 'warning');
        return;
    }
    
    try {
        const file = fileInput.files[0];
        const text = await file.text();
        const settings = JSON.parse(text);
        
        if (overwrite) {
            updateFormFields(settings);
            hasUnsavedChanges = true;
            updateSaveButton();
        } else {
            // Merge with existing settings
            const merged = {...collectFormData(), ...settings};
            updateFormFields(merged);
            hasUnsavedChanges = true;
            updateSaveButton();
        }
        
        hideModal('importSettingsModal');
        showNotification('Settings imported successfully', 'success');
        
    } catch (error) {
        console.error('Import settings error:', error);
        showNotification('Failed to import settings', 'error');
    }
}

// Updates
async function checkUpdates() {
    try {
        const response = await fetch('/api/system/check-updates');
        if (!response.ok) throw new Error('Failed to check for updates');
        
        const result = await response.json();
        if (result.update_available) {
            showNotification(`Update available: ${result.latest_version}`, 'info');
        } else {
            showNotification('System is up to date', 'success');
        }
        
    } catch (error) {
        console.error('Check updates error:', error);
        showNotification('Failed to check for updates', 'error');
    }
}

// UI Updates
function updateSaveButton() {
    const saveButton = document.querySelector('button[onclick="saveAllSettings()"]');
    saveButton.disabled = !hasUnsavedChanges;
    saveButton.classList.toggle('opacity-50', !hasUnsavedChanges);
}

// WebSocket handling
function initializeWebSocket() {
    wsClient.on('settings_changed', (data) => {
        updateFormFields(data.settings);
        showNotification('Settings updated externally', 'info');
    });
} 