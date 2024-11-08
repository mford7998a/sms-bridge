// Batch Operations Management
let batchOperationInProgress = false;

function showBatchOperationsModal() {
    document.getElementById('batchOperationsModal').classList.remove('hidden');
    resetBatchOperation();
}

function hideBatchOperationsModal() {
    if (!batchOperationInProgress) {
        document.getElementById('batchOperationsModal').classList.add('hidden');
    }
}

function resetBatchOperation() {
    document.getElementById('batchProgress').style.width = '0%';
    document.getElementById('batchStatus').textContent = 'Ready to execute';
    document.querySelectorAll('input[name="selected_devices"]').forEach(cb => cb.checked = false);
    document.getElementById('batchOperation').value = 'restart';
    hideAllOperationSettings();
}

function hideAllOperationSettings() {
    document.getElementById('apnSettings').classList.add('hidden');
    document.getElementById('networkModeSettings').classList.add('hidden');
}

// Show/hide operation-specific settings
document.getElementById('batchOperation').addEventListener('change', function() {
    hideAllOperationSettings();
    switch (this.value) {
        case 'update_apn':
            document.getElementById('apnSettings').classList.remove('hidden');
            break;
        case 'network_mode':
            document.getElementById('networkModeSettings').classList.remove('hidden');
            break;
    }
});

async function executeBatchOperation() {
    const selectedDevices = Array.from(document.querySelectorAll('input[name="selected_devices"]:checked'))
        .map(cb => cb.value);
    
    if (selectedDevices.length === 0) {
        showNotification('Please select at least one device', 'error');
        return;
    }

    const operation = document.getElementById('batchOperation').value;
    const parallel = document.querySelector('input[name="parallel"]').checked;
    const continueOnError = document.querySelector('input[name="continue_on_error"]').checked;

    // Get operation-specific settings
    let settings = {};
    switch (operation) {
        case 'update_apn':
            const apnInputs = document.getElementById('apnSettings').getElementsByTagName('input');
            settings = {
                apn: apnInputs[0].value,
                username: apnInputs[1].value,
                password: apnInputs[2].value
            };
            break;
        case 'network_mode':
            settings = {
                mode: document.getElementById('networkModeSettings').querySelector('select').value
            };
            break;
    }

    batchOperationInProgress = true;
    let progress = 0;
    const progressBar = document.getElementById('batchProgress');
    const statusText = document.getElementById('batchStatus');

    try {
        const response = await fetch('/api/batch-operations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                devices: selectedDevices,
                operation: operation,
                settings: settings,
                parallel: parallel,
                continue_on_error: continueOnError
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const {value, done} = await reader.read();
            if (done) break;

            const data = JSON.parse(decoder.decode(value));
            progress = (data.completed / data.total) * 100;
            progressBar.style.width = `${progress}%`;
            statusText.textContent = data.status;

            if (data.error && !continueOnError) {
                throw new Error(data.error);
            }
        }

        showNotification('Batch operation completed successfully', 'success');
    } catch (error) {
        showNotification(`Batch operation failed: ${error.message}`, 'error');
        statusText.textContent = 'Operation failed';
    } finally {
        batchOperationInProgress = false;
    }
} 