from typing import List, Optional
import re
from datetime import datetime
import logging
import asyncio

from .base import BaseModemManager
from src.models import Device, SMS

logger = logging.getLogger(__name__)

class SierraManager(BaseModemManager):
    # AT Commands
    AT_COMMANDS = {
        'RESET': 'AT!RESET',
        'SMS_FORMAT': 'AT+CMGF=1',
        'SMS_CHARSET': 'AT+CSCS="GSM"',
        'CHECK_SIGNAL': 'AT+CSQ',
        'CHECK_NETWORK': 'AT+CREG?',
        'GET_OPERATOR': 'AT+COPS?',
        'CHECK_SMS': 'AT+CMGL="ALL"',
        'DELETE_SMS': 'AT+CMGD={}',
        'SEND_SMS': 'AT+CMGS="{}"',
        'GET_BANDS': 'AT!BAND?',
        'SET_BANDS': 'AT!BAND={}',
        'GET_TEMP': 'AT!PCTEMP?',
        'RADIO_OFF': 'AT!PCPOWER=0',
        'RADIO_ON': 'AT!PCPOWER=1'
    }

    # LTE Band configurations
    LTE_BANDS = {
        'all': '00',  # All bands
        'b2_b4_b12': '11',  # Bands 2,4,12 only
        'b13': '13',  # Band 13 only
        'b66': '66'   # Band 66 only
    }

    async def _initialize_modem(self, device: Device) -> bool:
        """Initialize Sierra Wireless modem"""
        try:
            # Reset modem
            await self._send_at_command(device, self.AT_COMMANDS['RESET'])
            await asyncio.sleep(10)  # Sierra needs longer reset time
            
            # Set SMS format to text mode
            if not await self._send_at_command(device, self.AT_COMMANDS['SMS_FORMAT']):
                return False
                
            # Set character set
            if not await self._send_at_command(device, self.AT_COMMANDS['SMS_CHARSET']):
                return False
                
            # Check network registration
            response = await self._send_at_command(device, self.AT_COMMANDS['CHECK_NETWORK'])
            if not response or ',1' not in response:  # Not registered
                return False
                
            # Get current band configuration
            bands_response = await self._send_at_command(device, self.AT_COMMANDS['GET_BANDS'])
            if bands_response:
                device.config['current_bands'] = bands_response
                
            # Get temperature
            temp_response = await self._send_at_command(device, self.AT_COMMANDS['GET_TEMP'])
            if temp_response:
                device.config['temperature'] = temp_response
                
            return True
            
        except Exception as e:
            logger.error(f"Sierra initialization error: {str(e)}")
            return False

    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new messages"""
        messages = []
        try:
            response = await self._send_at_command(device, self.AT_COMMANDS['CHECK_SMS'])
            if not response:
                return messages
                
            # Parse messages - Sierra format is slightly different
            for match in re.finditer(r'\+CMGL: (\d+),".*?","(.*?)",.*?,.*?"(.*?)".*?\r\n(.*?)\r\n', 
                                   response, re.DOTALL):
                index, sender, timestamp, text = match.groups()
                
                message = SMS(
                    device_id=device.id,
                    from_number=sender,
                    to_number=device.phone_number,
                    text=text.strip(),
                    received_at=datetime.utcnow(),
                    delivered=False
                )
                messages.append(message)
                
                # Delete processed message
                await self._send_at_command(
                    device, 
                    self.AT_COMMANDS['DELETE_SMS'].format(index)
                )
                
            return messages
            
        except Exception as e:
            logger.error(f"Check messages error: {str(e)}")
            return messages

    async def send_message(self, device: Device, to_number: str, text: str) -> bool:
        """Send SMS message"""
        try:
            # Start SMS sending
            response = await self._send_at_command(
                device,
                self.AT_COMMANDS['SEND_SMS'].format(to_number)
            )
            if not response or '>' not in response:
                return False
                
            # Send message content
            ser = self._ports.get(device.id)
            if not ser:
                return False
                
            ser.write(text.encode())
            ser.write(b'\x1A')  # Ctrl+Z to end message
            
            # Wait for confirmation
            response = await self._send_at_command(device, "", timeout=5)
            return response and "OK" in response
            
        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
            return False

    async def get_signal_strength(self, device: Device) -> Optional[int]:
        """Get current signal strength"""
        try:
            response = await self._send_at_command(device, self.AT_COMMANDS['CHECK_SIGNAL'])
            if not response:
                return None
                
            match = re.search(r'\+CSQ: (\d+),', response)
            if match:
                signal = int(match.group(1))
                return min(signal * 3.226, 100)  # Convert to percentage
                
            return None
            
        except Exception as e:
            logger.error(f"Signal strength error: {str(e)}")
            return None

    async def set_bands(self, device: Device, bands: str) -> bool:
        """Configure specific LTE bands"""
        if bands not in self.LTE_BANDS:
            return False
            
        try:
            # Set bands
            response = await self._send_at_command(
                device,
                self.AT_COMMANDS['SET_BANDS'].format(self.LTE_BANDS[bands])
            )
            if not response or "OK" not in response:
                return False
                
            # Reset radio for changes to take effect
            await self._send_at_command(device, self.AT_COMMANDS['RADIO_OFF'])
            await asyncio.sleep(1)
            await self._send_at_command(device, self.AT_COMMANDS['RADIO_ON'])
            
            # Update device config
            device.config['current_bands'] = bands
            return True
            
        except Exception as e:
            logger.error(f"Set bands error: {str(e)}")
            return False

    async def get_temperature(self, device: Device) -> Optional[float]:
        """Get device temperature"""
        try:
            response = await self._send_at_command(device, self.AT_COMMANDS['GET_TEMP'])
            if not response:
                return None
                
            match = re.search(r'(-?\d+\.\d+)', response)
            if match:
                return float(match.group(1))
                
            return None
            
        except Exception as e:
            logger.error(f"Get temperature error: {str(e)}")
            return None