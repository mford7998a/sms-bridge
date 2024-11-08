from abc import ABC, abstractmethod
from typing import List, Optional
import serial
import logging
from src.models import Device, SMS
import asyncio

logger = logging.getLogger(__name__)

class ModemCommand:
    CHECK_SIGNAL = "AT+CSQ"
    CHECK_SMS = "AT+CMGL=\"ALL\""
    DELETE_SMS = "AT+CMGD={}"
    SET_SMS_MODE = "AT+CMGF=1"  # Text mode
    GET_IMEI = "AT+CGSN"
    GET_SIM_STATUS = "AT+CPIN?"
    GET_OPERATOR = "AT+COPS?"
    USB_MODE_SWITCH = "AT^SETPORT="

class BaseModemManager(ABC):
    def __init__(self):
        self.timeout = 5
        self.baudrate = 115200

    async def send_at_command(self, port: str, command: str, 
                            wait_time: float = 1.0) -> Optional[str]:
        try:
            with serial.Serial(port, self.baudrate, timeout=self.timeout) as ser:
                cmd = f"{command}\r\n".encode()
                ser.write(cmd)
                await asyncio.sleep(wait_time)
                
                response = ""
                while ser.in_waiting:
                    response += ser.readline().decode('utf-8', errors='ignore')
                
                return response.strip()
        except Exception as e:
            logger.error(f"Error sending AT command {command}: {str(e)}")
            return None

    @abstractmethod
    async def check_status(self, device: Device) -> str:
        pass

    @abstractmethod
    async def check_messages(self, device: Device) -> List[SMS]:
        pass

    async def configure_modem(self, device: Device) -> bool:
        """Basic modem configuration"""
        try:
            # Set SMS text mode
            response = await self.send_at_command(device.port, ModemCommand.SET_SMS_MODE)
            if "OK" not in response:
                return False

            # Additional device-specific configuration can be added in child classes
            return True
        except Exception as e:
            logger.error(f"Error configuring modem: {str(e)}")
            return False

    async def parse_sms_response(self, response: str) -> List[dict]:
        """Generic SMS response parser"""
        messages = []
        lines = response.split('\n')
        current_msg = None

        for line in lines:
            if line.startswith('+CMGL:'):
                if current_msg:
                    messages.append(current_msg)
                
                # Parse message header
                parts = line.split(',')
                current_msg = {
                    'index': int(parts[0].split(':')[1].strip()),
                    'status': parts[1].strip('"'),
                    'from': parts[2].strip('"'),
                    'timestamp': parts[4].strip('"') + ',' + parts[5].strip('"'),
                    'text': ''
                }
            elif current_msg is not None:
                current_msg['text'] = line.strip()

        if current_msg:
            messages.append(current_msg)

        return messages 