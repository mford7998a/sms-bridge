from typing import List, Dict
import asyncio
import re
from .base import BaseModemManager, ModemCommand
from src.models import Device, SMS

class SierraManager(BaseModemManager):
    """
    Manager for Sierra Wireless EM7455 and HP LT4120 (T77W595.00)
    These devices support both AT commands and QMI protocol
    """
    
    SIERRA_COMMANDS = {
        'FIRMWARE_VERSION': 'AT!PACKAGE?',
        'TEMPERATURE': 'AT!PCTEMP?',
        'BANDS': 'AT!BAND?',
        'LOCK_BAND': 'AT!BAND=',
        'CARRIER_AGG': 'AT!CAINFO?',
        'SET_APN': 'AT+CGDCONT=1,"IP","{}"',
        'RADIO_ON': 'AT+CFUN=1',
        'RADIO_OFF': 'AT+CFUN=0',
        'GET_ICCID': 'AT+ICCID',
        'GET_SIGNAL_EXT': 'AT!GSTATUS?',  # Enhanced signal info
        'SET_QMI_MODE': 'AT!USBCOMP=1,1,10D',  # Enable QMI mode
        'SET_MBIM_MODE': 'AT!USBCOMP=1,1,10B'  # Enable MBIM mode
    }

    # LTE bands configuration
    LTE_BANDS = {
        'all': '00000000',
        'b2_b4_b12': '00000842',  # Bands 2,4,12 only
        'b2_b4': '00000042',      # Bands 2,4 only
        'b13': '00001000'         # Band 13 only
    }

    async def initialize_device(self, device: Device) -> bool:
        """Initial device setup and configuration"""
        try:
            # Enable radio
            await self.send_at_command(device.port, self.SIERRA_COMMANDS['RADIO_ON'])
            await asyncio.sleep(2)
            
            # Configure for SMS
            await self.send_at_command(device.port, ModemCommand.SET_SMS_MODE)
            
            # Get device info
            iccid_response = await self.send_at_command(
                device.port, 
                self.SIERRA_COMMANDS['GET_ICCID']
            )
            if iccid_response:
                device.sim_iccid = iccid_response.replace('+ICCID: ', '').strip()
            
            # Enable QMI mode for better data performance
            await self.send_at_command(device.port, self.SIERRA_COMMANDS['SET_QMI_MODE'])
            
            return True
            
        except Exception as e:
            logger.error(f"Sierra initialization error: {str(e)}")
            return False

    async def check_status(self, device: Device) -> str:
        # Get enhanced signal info
        response = await self.send_at_command(
            device.port,
            self.SIERRA_COMMANDS['GET_SIGNAL_EXT']
        )
        
        if response:
            try:
                # Parse enhanced signal info
                rssi_match = re.search(r'RSSI\s*=\s*(-\d+)', response)
                rsrp_match = re.search(r'RSRP\s*=\s*(-\d+)', response)
                sinr_match = re.search(r'SINR\s*=\s*(-?\d+)', response)
                
                if rssi_match:
                    rssi = int(rssi_match.group(1))
                    # Convert RSSI to percentage (-60 dBm = 100%, -120 dBm = 0%)
                    device.signal_strength = min(100, max(0, 
                        (rssi + 120) * 100 // 60))
                    
                    # Store detailed signal info
                    device.signal_details = {
                        'rssi': rssi,
                        'rsrp': int(rsrp_match.group(1)) if rsrp_match else None,
                        'sinr': int(sinr_match.group(1)) if sinr_match else None
                    }
                    
                    return 'online'
            except Exception:
                pass
        
        # Fallback to basic signal check
        response = await self.send_at_command(device.port, ModemCommand.CHECK_SIGNAL)
        if response and "+CSQ:" in response:
            signal = int(response.split(':')[1].split(',')[0].strip())
            device.signal_strength = (signal * 100) // 31
            return 'online'
            
        return 'offline'

    async def check_messages(self, device: Device) -> List[SMS]:
        messages = []
        
        # Ensure we're in text mode
        await self.send_at_command(device.port, ModemCommand.SET_SMS_MODE)
        
        response = await self.send_at_command(device.port, ModemCommand.CHECK_SMS)
        if not response:
            return messages

        parsed_messages = await self.parse_sms_response(response)
        
        for msg in parsed_messages:
            sms = SMS(
                device_id=device.id,
                from_number=msg['from'],
                to_number=device.phone_number,
                text=msg['text'],
                received_at=msg['timestamp'],
                delivered=False
            )
            messages.append(sms)
            
            # Delete processed message
            await self.send_at_command(
                device.port,
                ModemCommand.DELETE_SMS.format(msg['index'])
            )

        return messages

    async def set_bands(self, device: Device, bands: str) -> bool:
        """Configure specific LTE bands"""
        if bands not in self.LTE_BANDS:
            return False
            
        cmd = f"{self.SIERRA_COMMANDS['LOCK_BAND']}{self.LTE_BANDS[bands]}"
        response = await self.send_at_command(device.port, cmd)
        
        if response and "OK" in response:
            # Device needs reset after band change
            await self.send_at_command(device.port, self.SIERRA_COMMANDS['RADIO_OFF'])
            await asyncio.sleep(1)
            await self.send_at_command(device.port, self.SIERRA_COMMANDS['RADIO_ON'])
            return True
            
        return False

    async def check_temperature(self, device: Device) -> Dict[str, float]:
        """Get device temperature information"""
        response = await self.send_at_command(
            device.port,
            self.SIERRA_COMMANDS['TEMPERATURE']
        )
        
        if response:
            try:
                # Parse temperature response
                matches = re.findall(r'(\w+)=(-?\d+\.\d+)', response)
                return {name: float(temp) for name, temp in matches}
            except Exception:
                pass
                
        return {} 