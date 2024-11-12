// Message Management
let selectedMessages = new Set();

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    setupMessageForm();
});

// WebSocket handling
function initializeWebSocket() {
    wsClient.on('message_status_update', (data) => {
        updateMessageStatus(data.message_id, data.status);
    });

    wsClient.on('new_message', (data) => {
        addNewMessage(data.message);
    });
}

// Message Form Setup
function setupMessageForm() {
    const messageInput = document.querySelector('textarea[name="message"]');
    const charCount = document.getElementById('charCount');

    messageInput.addEventListener('input', function() {
        const count = this.value.length;
        charCount.textContent = count;
        
        if (count > 160) {
            charCount.classList.add('text-red-500');
        } else {
            charCount.classList.remove('text-red-500');
        }
    });
}

// Filter Functions
let filterTimeout;
function debounce(func, wait) {
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(filterTimeout);
            func(...args);
        };
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(later, wait);
    };
}

async function applyFilters() {
    const filters = {
        device: document.getElementById('deviceFilter').value,
        status: document.getElementById('statusFilter').value,
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        search: document.getElementById('searchFilter').value
    };

    try {
        const response = await fetch('/api/messages/filter?' + new URLSearchParams(filters));
        if (!response.ok) throw new Error('Failed to filter messages');
        
        const data = await response.json();
        updateMessageTable(data.messages);
        updatePagination(data.pagination);
        
    } catch (error) {
        console.error('Filter error:', error);
        showNotification('Failed to apply filters', 'error');
    }
}

// Message Actions
async function sendMessage(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    try {
        const response = await fetch('/api/messages/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(Object.fromEntries(formData))
        });

        if (!response.ok) throw new Error('Failed to send message');
        
        const result = await response.json();
        showNotification('Message sent successfully', 'success');
        hideModal('sendMessageModal');
        form.reset();
        
        // Add new message to table
        addNewMessage(result.message);
        
    } catch (error) {
        console.error('Send message error:', error);
        showNotification('Failed to send message', 'error');
    }
}

async function resendMessage(messageId) {
    try {
        const response = await fetch(`/api/messages/${messageId}/resend`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Failed to resend message');
        
        showNotification('Message queued for resend', 'success');
        
    } catch (error) {
        console.error('Resend error:', error);
        showNotification('Failed to resend message', 'error');
    }
}

async function deleteMessage(messageId) {
    if (!confirm('Are you sure you want to delete this message?')) {
        return;
    }

    try {
        const response = await fetch(`/api/messages/${messageId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete message');
        
        // Remove message from table
        document.querySelector(`tr[data-message-id="${messageId}"]`).remove();
        showNotification('Message deleted successfully', 'success');
        
    } catch (error) {
        console.error('Delete error:', error);
        showNotification('Failed to delete message', 'error');
    }
}

// Message Details
async function showMessageDetails(messageId) {
    try {
        const response = await fetch(`/api/messages/${messageId}`);
        if (!response.ok) throw new Error('Failed to load message details');
        
        const message = await response.json();
        
        // Update modal content
        document.getElementById('messageId').textContent = message.id;
        document.getElementById('deviceInfo').textContent = 
            `${message.device_id} (${message.device_type})`;
        document.getElementById('messageFrom').textContent = message.from_number;
        document.getElementById('messageTo').textContent = message.to_number;
        document.getElementById('messageContent').textContent = message.text;
        
        // Update status history
        const statusHistory = document.getElementById('statusHistory');
        statusHistory.innerHTML = message.status_history
            .map(status => `
                <div class="flex justify-between">
                    <span>${status.status}</span>
                    <span>${new Date(status.timestamp).toLocaleString()}</span>
                </div>
            `)
            .join('');
        
        showModal('messageDetailsModal');
        
    } catch (error) {
        console.error('Load details error:', error);
        showNotification('Failed to load message details', 'error');
    }
}

// Batch Operations
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.getElementsByClassName('message-select');
    
    Array.from(checkboxes).forEach(checkbox => {
        checkbox.checked = selectAll.checked;
        if (selectAll.checked) {
            selectedMessages.add(checkbox.value);
        } else {
            selectedMessages.delete(checkbox.value);
        }
    });
}

function showBatchMessages() {
    if (selectedMessages.size === 0) {
        showNotification('Please select messages first', 'warning');
        return;
    }
    
    // Show batch operations modal
    showModal('batchMessagesModal');
}

// UI Updates
function updateMessageStatus(messageId, status) {
    const statusCell = document.querySelector(
        `tr[data-message-id="${messageId}"] .status-badge`
    );
    if (statusCell) {
        statusCell.className = `status-badge status-${status}`;
        statusCell.textContent = status;
    }
}

function addNewMessage(message) {
    const tbody = document.querySelector('table tbody');
    const tr = document.createElement('tr');
    tr.setAttribute('data-message-id', message.id);
    
    tr.innerHTML = `
        <td class="table-cell">
            <input type="checkbox" value="${message.id}" class="message-select">
        </td>
        <td class="table-cell">${new Date(message.received_at).toLocaleString()}</td>
        <td class="table-cell">${message.device_id}</td>
        <td class="table-cell">${message.from_number}</td>
        <td class="table-cell">${message.to_number}</td>
        <td class="table-cell">
            <div class="max-w-xs truncate">${message.text}</div>
        </td>
        <td class="table-cell">
            <span class="status-badge status-${message.status}">
                ${message.status}
            </span>
        </td>
        <td class="table-cell">
            <button onclick="showMessageDetails('${message.id}')" 
                    class="btn-icon" title="View Details">
                <i class="fas fa-eye"></i>
            </button>
            <button onclick="resendMessage('${message.id}')" 
                    class="btn-icon" title="Resend">
                <i class="fas fa-redo"></i>
            </button>
            <button onclick="deleteMessage('${message.id}')" 
                    class="btn-icon text-red-500" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    
    tbody.insertBefore(tr, tbody.firstChild);
}

function updatePagination(pagination) {
    // Update pagination UI
    document.querySelector('.pagination-info').textContent = 
        `Showing ${pagination.start} to ${pagination.end} of ${pagination.total} messages`;
        
    // Update buttons
    document.querySelector('.pagination-prev').disabled = pagination.current === 1;
    document.querySelector('.pagination-next').disabled = 
        pagination.current === pagination.total_pages;
} 