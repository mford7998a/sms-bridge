class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.handlers = new Map();
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.reconnect = this.reconnect.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
    }

    async connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                this.triggerHandler('connected');
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.triggerHandler('disconnected');
                this.reconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.triggerHandler('error', error);
            };

            this.ws.onmessage = this.handleMessage;
            
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.reconnect();
        }
    }

    async reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.triggerHandler('max_attempts_reached');
            return;
        }

        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        
        // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, this.reconnectDelay));
        this.reconnectDelay *= 2;
        
        this.connect();
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.triggerHandler('message', data);
            
            // Trigger specific handlers based on message type
            if (data.type) {
                this.triggerHandler(data.type, data);
            }
            
        } catch (error) {
            console.error('Error handling message:', error);
        }
    }

    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, new Set());
        }
        this.handlers.get(event).add(handler);
    }

    off(event, handler) {
        if (this.handlers.has(event)) {
            this.handlers.get(event).delete(handler);
        }
    }

    triggerHandler(event, data = null) {
        if (this.handlers.has(event)) {
            for (const handler of this.handlers.get(event)) {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in ${event} handler:`, error);
                }
            }
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Initialize WebSocket client
const wsClient = new WebSocketClient(`ws://${window.location.host}/ws`);

// Add default handlers
wsClient.on('connected', () => {
    showNotification('Connected to server', 'success');
});

wsClient.on('disconnected', () => {
    showNotification('Disconnected from server', 'warning');
});

wsClient.on('error', (error) => {
    showNotification('WebSocket error occurred', 'error');
});

wsClient.on('max_attempts_reached', () => {
    showNotification('Unable to connect to server', 'error');
});

// Message type handlers
wsClient.on('device_update', (data) => {
    updateDeviceStatus(data.device);
});

wsClient.on('message_received', (data) => {
    updateMessageList(data.message);
});

wsClient.on('system_status', (data) => {
    updateSystemStatus(data.status);
});

// Connect on load
document.addEventListener('DOMContentLoaded', () => {
    wsClient.connect();
});

// Export for use in other modules
window.wsClient = wsClient; 