from typing import List, Dict
import asyncio
import re
from .base import BaseModemManager, ModemCommand
from src.models import Device, SMS
import logging

logger = logging.getLogger(__name__)

class HuaweiManager(BaseModemManager):
    """
    Manager for Huawei modems (E303, E1732, E3372)
    Includes advanced commands and unlocking features
    """
    
    HUAWEI_COMMANDS = {
        # Basic Commands
        'GET_VERSION': 'AT+CGMR',
        'GET_MODEL': 'AT+CGMM',
        'GET_IMEI': 'AT+CGSN',
        'GET_ICCID': 'AT^ICCID?',
        
        # Mode Switching
        'SWITCH_MODE': 'AT^SETPORT=',
        'GET_MODE': 'AT^GETPORTMODE',
        'SET_MODEM_MODE': 'AT^SETPORT="A1,A2"',
        'SET_CDROM_MODE': 'AT^SETPORT="FF"',
        
        # Network Commands
        'GET_SIGNAL_EXT': 'AT^HCSQ?',
        'SET_NETWORK_MODE': 'AT^SYSCFGEX=',
        'GET_NETWORK_MODE': 'AT^SYSCFGEX?',
        'SET_PREFERRED_MODE': 'AT+COPS=',
        'GET_CELL_INFO': 'AT^MONSC',
        
        # Band Configuration
        'GET_BANDS': 'AT^SYSCFGEX?',
        'SET_BANDS': 'AT^SYSCFGEX="',
        
        # Unlock Commands
        'UNLOCK_CODE': 'AT^CARDLOCK=',
        'GET_UNLOCK_STATUS': 'AT^CARDLOCK?',
        'ENTER_PIN': 'AT+CPIN=',
        'REMOVE_SIMLOCK': 'AT^SIMLOCK=0,"00000000"',
        
        # Advanced Engineering Commands
        'ENGINEERING_MODE': 'AT^CURC=0',
        'DEBUG_PORT': 'AT^TRACECTRL=0',
        'TEST_MODE': 'AT^DSFLOWCLR',
        
        # E3372 Specific
        'HILINK_MODE': 'AT^NVRESTORE',
        'STICK_MODE': 'AT^REMAP'
    }

    # Network modes mapping
    NETWORK_MODES = {
        'auto': '00',  # Automatic
        '4g_only': '03',  # LTE only
        '3g_only': '02',  # WCDMA only
        '2g_only': '01',  # GSM only
        '4g_preferred': '0301',  # LTE preferred
        '3g_preferred': '0201',  # WCDMA preferred
        '2g_preferred': '0102'   # GSM preferred
    }

    # Band configurations
    BAND_CONFIGS = {
        'all': '3FFFFFFF',  # All bands
        'eu': '0080080C0',  # European bands
        'us': '00800C5',    # US bands
        'asia': '00300000'  # Asian bands
    }

    async def initialize_device(self, device: Device) -> bool:
        """Initialize device with optimal settings"""
        try:
            # Switch to modem mode if needed
            await self.send_at_command(device.port, self.HUAWEI_COMMANDS['SET_MODEM_MODE'])
            await asyncio.sleep(2)
            
            # Enable engineering mode for advanced features
            await self.send_at_command(device.port, self.HUAWEI_COMMANDS['ENGINEERING_MODE'])
            
            # Configure for SMS
            await self.send_at_command(device.port, ModemCommand.SET_SMS_MODE)
            
            # Get device info
            model = await self.send_at_command(device.port, self.HUAWEI_COMMANDS['GET_MODEL'])
            device.model = model.replace('+CGMM: ', '').strip() if model else None
            
            iccid = await self.send_at_command(device.port, self.HUAWEI_COMMANDS['GET_ICCID'])
            device.sim_iccid = iccid.replace('^ICCID: ', '').strip() if iccid else None
            
            return True
            
        except Exception as e:
            logger.error(f"Huawei initialization error: {str(e)}")
            return False

    async def check_status(self, device: Device) -> str:
        # Try enhanced signal check first
        response = await self.send_at_command(
            device.port, 
            self.HUAWEI_COMMANDS['GET_SIGNAL_EXT']
        )
        
        if response and "^HCSQ:" in response:
            try:
                # Parse enhanced signal info
                parts = response.split(',')
                mode = parts[0].split(':')[1].strip()
                signal = int(parts[1])
                
                # Store detailed signal info
                device.signal_details = {
                    'mode': mode,
                    'rssi': signal,
                    'rsrp': int(parts[2]) if len(parts) > 2 else None,
                    'sinr': int(parts[3]) if len(parts) > 3 else None,
                    'rsrq': int(parts[4]) if len(parts) > 4 else None
                }
                
                # Convert signal to percentage based on mode
                if mode == "LTE":
                    device.signal_strength = min(100, max(0, (signal + 140) * 100 // 60))
                elif mode == "WCDMA":
                    device.signal_strength = min(100, max(0, (signal + 120) * 100 // 60))
                else:
                    device.signal_strength = min(100, max(0, (signal + 110) * 100 // 50))
                    
                return 'online'
                
            except Exception as e:
                logger.error(f"Signal parsing error: {str(e)}")
        
        # Fallback to basic signal check
        response = await self.send_at_command(device.port, ModemCommand.CHECK_SIGNAL)
        if response and "+CSQ:" in response:
            signal = int(response.split(':')[1].split(',')[0].strip())
            device.signal_strength = (signal * 100) // 31
            return 'online'
            
        return 'offline'

    async def unlock_device(self, device: Device, unlock_code: str) -> bool:
        """Unlock device with provided code"""
        try:
            response = await self.send_at_command(
                device.port,
                f"{self.HUAWEI_COMMANDS['UNLOCK_CODE']}{unlock_code}"
            )
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"Unlock error: {str(e)}")
            return False

    async def set_network_mode(self, device: Device, mode: str) -> bool:
        """Configure network mode (2G/3G/4G/Auto)"""
        if mode not in self.NETWORK_MODES:
            return False
            
        try:
            cmd = f"{self.HUAWEI_COMMANDS['SET_NETWORK_MODE']}{self.NETWORK_MODES[mode]}"
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"Network mode error: {str(e)}")
            return False

    async def configure_bands(self, device: Device, bands: str) -> bool:
        """Configure supported bands"""
        if bands not in self.BAND_CONFIGS:
            return False
            
        try:
            cmd = f"{self.HUAWEI_COMMANDS['SET_BANDS']}{self.BAND_CONFIGS[bands]}\""
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"Band configuration error: {str(e)}")
            return False

    async def switch_mode(self, device: Device, mode: str) -> bool:
        """Switch between HiLink and Stick mode (E3372)"""
        if device.model and 'E3372' in device.model:
            cmd = self.HUAWEI_COMMANDS['HILINK_MODE'] if mode == 'hilink' else self.HUAWEI_COMMANDS['STICK_MODE']
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        return False

    async def remove_carrier_lock(self, device: Device) -> bool:
        """Remove carrier lock (if possible)"""
        try:
            response = await self.send_at_command(
                device.port,
                self.HUAWEI_COMMANDS['REMOVE_SIMLOCK']
            )
            return "OK" in response if response else False
        except Exception:
            return False

    async def get_cell_info(self, device: Device) -> Dict:
        """Get detailed cell information"""
        try:
            response = await self.send_at_command(
                device.port,
                self.HUAWEI_COMMANDS['GET_CELL_INFO']
            )
            if response:
                # Parse cell info response
                info = {}
                for line in response.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                return info
        except Exception as e:
            logger.error(f"Cell info error: {str(e)}")
        return {}

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