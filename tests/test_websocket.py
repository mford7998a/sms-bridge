import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from src.main import app

def test_websocket_connection(client):
    with client.websocket_connect("/ws") as websocket:
        # Test connection is established
        assert websocket.connected

def test_websocket_device_updates(client):
    with client.websocket_connect("/ws") as websocket:
        # Add a device to trigger update
        device_data = {
            "id": "test_device",
            "type": "huawei",
            "phone_number": "+1234567890",
            "port": "COM1"
        }
        client.post("/api/devices", json=device_data)
        
        # Receive update
        data = websocket.receive_json()
        assert data["type"] == "device_added"
        assert data["device"]["id"] == "test_device"

def test_websocket_message_updates(client):
    with client.websocket_connect("/ws") as websocket:
        # Send a message to trigger update
        message = {
            "device_id": "test_device",
            "to_number": "+0987654321",
            "text": "Test message"
        }
        client.post("/api/messages/send", json=message)
        
        # Receive update
        data = websocket.receive_json()
        assert data["type"] == "message_sent" 