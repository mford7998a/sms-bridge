from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, WebSocket, Depends, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import serial.tools.list_ports
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import jwt

# Initialize FastAPI app
app = FastAPI(title="SMS Bridge Dashboard")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

# Initialize components
active_devices: Dict[str, Device] = {}
device_managers = {
    'franklin': FranklinManager(),
    'sierra': SierraManager(),
    'huawei': HuaweiManager(),
    'android': AndroidManager(),
    'voip': VoipManager()
}

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "your-secret-key"  # Move to environment variables
ALGORITHM = "HS256"

# Device Management Routes
@app.post("/api/devices")
async def add_device(device: Device, background_tasks: BackgroundTasks):
    """Add new device"""
    if device.id in active_devices:
        raise HTTPException(status_code=400, detail="Device already exists")
        
    manager = device_managers.get(device.type)
    if not manager:
        raise HTTPException(status_code=400, detail="Invalid device type")
        
    active_devices[device.id] = device
    background_tasks.add_task(initialize_device, device)
    return {"status": "success", "device": device}

@app.delete("/api/devices/{device_id}")
async def remove_device(device_id: str):
    """Remove device"""
    if device_id not in active_devices:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device = active_devices.pop(device_id)
    await cleanup_device(device)
    return {"status": "success"}

# Batch Operations
@app.post("/api/batch")
async def batch_operation(operation: dict):
    """Execute batch operation on multiple devices"""
    devices = operation.get("devices", [])
    op_type = operation.get("type")
    
    results = []
    for device_id in devices:
        try:
            device = active_devices.get(device_id)
            if device:
                result = await execute_operation(device, op_type)
                results.append({"device_id": device_id, "status": "success", "result": result})
            else:
                results.append({"device_id": device_id, "status": "error", "message": "Device not found"})
        except Exception as e:
            results.append({"device_id": device_id, "status": "error", "message": str(e)})
            
    return {"results": results}

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                await self.disconnect(connection)

manager = ConnectionManager()

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            updates = await get_status_updates()
            await websocket.send_json(updates)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background Tasks
async def initialize_device(device: Device):
    """Initialize new device"""
    try:
        device_manager = device_managers[device.type]
        await device_manager.initialize(device)
        await manager.broadcast({
            "type": "device_added",
            "device": device.dict()
        })
    except Exception as e:
        logger.error(f"Device initialization error: {str(e)}")
        active_devices.pop(device.id, None)

async def cleanup_device(device: Device):
    """Cleanup device resources"""
    try:
        device_manager = device_managers[device.type]
        await device_manager.cleanup(device)
        await manager.broadcast({
            "type": "device_removed",
            "device_id": device.id
        })
    except Exception as e:
        logger.error(f"Device cleanup error: {str(e)}")

# Error Handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        await db.initialize()
        await smshub_client.initialize()
        # Load saved devices
        devices = await db.get_devices()
        for device in devices:
            active_devices[device.id] = device
            await initialize_device(device)
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        for device in list(active_devices.values()):
            await cleanup_device(device)
        await db.cleanup()
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")