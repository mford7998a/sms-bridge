import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.models import Device, SMS

@pytest.fixture
def client():
    return TestClient(app)

def test_add_device(client, mock_serial):
    device_data = {
        "id": "test_device",
        "type": "huawei",
        "phone_number": "+1234567890",
        "port": "COM1"
    }
    
    response = client.post("/api/devices", json=device_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["device"]["id"] == device_data["id"]

def test_remove_device(client):
    # First add a device
    device_data = {
        "id": "test_device",
        "type": "huawei",
        "phone_number": "+1234567890",
        "port": "COM1"
    }
    client.post("/api/devices", json=device_data)
    
    # Then remove it
    response = client.delete(f"/api/devices/{device_data['id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_batch_operations(client):
    # Add test devices
    devices = [
        {
            "id": "device1",
            "type": "huawei",
            "phone_number": "+1111111111",
            "port": "COM1"
        },
        {
            "id": "device2",
            "type": "sierra",
            "phone_number": "+2222222222",
            "port": "COM2"
        }
    ]
    
    for device in devices:
        client.post("/api/devices", json=device)
    
    # Test batch operation
    operation = {
        "devices": ["device1", "device2"],
        "type": "reset"
    }
    
    response = client.post("/api/batch", json=operation)
    assert response.status_code == 200
    assert len(response.json()["results"]) == 2

def test_settings_endpoints(client):
    # Test get settings
    response = client.get("/api/settings")
    assert response.status_code == 200
    
    # Test update settings
    settings = {
        "system_name": "Test System",
        "theme": "dark",
        "smshub_api_key": "test_key"
    }
    
    response = client.put("/api/settings", json=settings)
    assert response.status_code == 200
    
    # Verify settings were updated
    response = client.get("/api/settings")
    assert response.json()["system_name"] == "Test System"

def test_message_endpoints(client):
    # Add test device
    device_data = {
        "id": "test_device",
        "type": "huawei",
        "phone_number": "+1234567890",
        "port": "COM1"
    }
    client.post("/api/devices", json=device_data)
    
    # Test send message
    message = {
        "device_id": "test_device",
        "to_number": "+0987654321",
        "text": "Test message"
    }
    
    response = client.post("/api/messages/send", json=message)
    assert response.status_code == 200
    
    # Test get messages
    response = client.get("/api/messages")
    assert response.status_code == 200
    
    # Test message filters
    filters = {
        "device": "test_device",
        "status": "delivered",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    
    response = client.get("/api/messages/filter", params=filters)
    assert response.status_code == 200 