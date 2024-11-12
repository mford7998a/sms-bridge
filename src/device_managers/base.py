from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import serial
import logging
import asyncio
from datetime import datetime

from src.models import Device, SMS
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

class BaseModemManager(ABC):
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ports = {}  # Store serial connections

    async def initialize(self, device: Device) -> bool:
        """Initialize device connection and configuration"""
        try:
            # Open serial port
            if not await self._open_port(device):
                return False
                
            # Basic initialization sequence
            if not await self._initialize_modem(device):
                return False
                
            # Update device status
            await self.db.update_device_status(device.id, "online")
            return True
            
        except Exception as e:
            logger.error(f"Device initialization error: {str(e)}")
            await self.db.update_device_status(device.id, "error")
            return False

    async def cleanup(self, device: Device):
        """Cleanup device resources"""
        try:
            await self._close_port(device)
            await self.db.update_device_status(device.id, "offline")
        except Exception as e:
            logger.error(f"Device cleanup error: {str(e)}")

    @abstractmethod
    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new messages"""
        pass

    @abstractmethod
    async def send_message(self, device: Device, to_number: str, text: str) -> bool:
        """Send SMS message"""
        pass

    @abstractmethod
    async def get_signal_strength(self, device: Device) -> Optional[int]:
        """Get current signal strength"""
        pass

    async def _open_port(self, device: Device) -> bool:
        """Open serial port connection"""
        try:
            if device.id in self._ports:
                return True
                
            ser = serial.Serial(
                port=device.port,
                baudrate=115200,
                timeout=1
            )
            self._ports[device.id] = ser
            return True
            
        except Exception as e:
            logger.error(f"Port open error: {str(e)}")
            return False

    async def _close_port(self, device: Device):
        """Close serial port connection"""
        try:
            if device.id in self._ports:
                self._ports[device.id].close()
                del self._ports[device.id]
        except Exception as e:
            logger.error(f"Port close error: {str(e)}")

    async def _send_at_command(self, device: Device, command: str, 
                             timeout: int = 1) -> Optional[str]:
        """Send AT command and get response"""
        try:
            ser = self._ports.get(device.id)
            if not ser:
                return None
                
            # Clear input buffer
            ser.reset_input_buffer()
            
            # Send command
            ser.write(f"{command}\r\n".encode())
            
            # Wait for response
            response = ""
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < timeout:
                if ser.in_waiting:
                    response += ser.read(ser.in_waiting).decode()
                    if "OK" in response or "ERROR" in response:
                        break
                await asyncio.sleep(0.1)
                
            return response.strip()
            
        except Exception as e:
            logger.error(f"AT command error: {str(e)}")
            return None

    @abstractmethod
    async def _initialize_modem(self, device: Device) -> bool:
        """Initialize modem with basic AT commands"""
        pass