from typing import List, Dict
import asyncio
import re
from .base import BaseModemManager, ModemCommand
from src.models import Device, SMS
import logging

logger = logging.getLogger(__name__)

class FibocomManager(BaseModemManager):
    """
    Manager for Fibocom L850-GL modems
    Includes advanced configuration and firmware features
    """
    
    FIBOCOM_COMMANDS = {
        # Basic Commands
        'GET_VERSION': 'AT+CGMR',
        'GET_MODEL': 'AT+CGMM',
        'GET_IMEI': 'AT+CGSN',
        'GET_ICCID': 'AT+ICCID',
        
        # Mode Configuration
        'SET_MODE': 'AT+GTUSBMODE=',
        'GET_MODE': 'AT+GTUSBMODE?',
        'SET_MBIM': 'AT+GTUSBMODE=17',  # MBIM Mode
        'SET_ECM': 'AT+GTUSBMODE=16',   # ECM Mode
        'SET_RNDIS': 'AT+GTUSBMODE=18', # RNDIS Mode
        
        # Network Commands
        'SET_RAT': 'AT+GTRAT=',         # Radio Access Technology
        'GET_RAT': 'AT+GTRAT?',
        'SET_BANDS': 'AT+GTBANDSEL=',
        'GET_BANDS': 'AT+GTBANDSEL?',
        'GET_SIGNAL': 'AT+GTCCINFO?',
        'GET_CELL_INFO': 'AT+COPS?',
        
        # Advanced Settings
        'ENGINEERING_MODE': 'AT+GTENG=',
        'DEBUG_MODE': 'AT+GTDBG=',
        'POWER_MODE': 'AT+GTPWR=',
        'THERMAL_MITIGATION': 'AT+GTTMP=',
        
        # Firmware Commands
        'FIRMWARE_VERSION': 'AT+GTSWV?',
        'FIRMWARE_UPDATE': 'AT+GTFWUPDATE=',
        'FACTORY_RESET': 'AT+GTRESET',
        
        # Carrier Aggregation
        'CA_CONFIG': 'AT+GTCAINFO=',
        'CA_STATUS': 'AT+GTCAINFO?',
        
        # VoLTE Settings
        'VOLTE_ENABLE': 'AT+GTVOLTE=1',
        'VOLTE_DISABLE': 'AT+GTVOLTE=0',
        'VOLTE_STATUS': 'AT+GTVOLTE?'
    }

    # Network modes
    NETWORK_MODES = {
        'auto': '2,2,0',      # Auto (all modes)
        'lte_only': '3,3,0',  # LTE only
        'wcdma_only': '2,2,0' # WCDMA only
    }

    # Band configurations
    BAND_CONFIGS = {
        'all': '1,1,1,1,1,1,1,1',  # All bands enabled
        'us': '1,1,1,0,0,0,0,0',   # US bands
        'eu': '0,0,0,1,1,0,0,0',   # EU bands
        'asia': '0,0,0,0,0,1,1,1'  # Asian bands
    }

    async def initialize_device(self, device: Device) -> bool:
        """Initialize device with optimal settings"""
        try:
            # Get device info
            model = await self.send_at_command(device.port, self.FIBOCOM_COMMANDS['GET_MODEL'])
            device.model = model.replace('+CGMM: ', '').strip() if model else None
            
            iccid = await self.send_at_command(device.port, self.FIBOCOM_COMMANDS['GET_ICCID'])
            device.sim_iccid = iccid.replace('+ICCID: ', '').strip() if iccid else None
            
            # Enable engineering mode for advanced features
            await self.send_at_command(device.port, f"{self.FIBOCOM_COMMANDS['ENGINEERING_MODE']}1")
            
            # Configure optimal power mode
            await self.send_at_command(device.port, f"{self.FIBOCOM_COMMANDS['POWER_MODE']}1")
            
            # Enable thermal mitigation
            await self.send_at_command(device.port, f"{self.FIBOCOM_COMMANDS['THERMAL_MITIGATION']}1")
            
            return True
            
        except Exception as e:
            logger.error(f"Fibocom initialization error: {str(e)}")
            return False

    async def check_status(self, device: Device) -> str:
        """Check device status and signal strength"""
        try:
            response = await self.send_at_command(
                device.port,
                self.FIBOCOM_COMMANDS['GET_SIGNAL']
            )
            
            if response and "+GTCCINFO:" in response:
                # Parse detailed signal info
                parts = response.split(',')
                
                device.signal_details = {
                    'rat': parts[1],           # Radio Access Technology
                    'band': parts[2],          # Current Band
                    'rsrp': int(parts[3]),     # Reference Signal Received Power
                    'rsrq': int(parts[4]),     # Reference Signal Received Quality
                    'sinr': int(parts[5]),     # Signal to Interference + Noise Ratio
                    'cell_id': parts[6],       # Cell ID
                    'pci': parts[7],           # Physical Cell ID
                    'earfcn': parts[8]         # E-UTRA Absolute Radio Frequency Channel Number
                }
                
                # Convert RSRP to percentage (-140 dBm = 0%, -80 dBm = 100%)
                rsrp = int(parts[3])
                device.signal_strength = min(100, max(0, (rsrp + 140) * 100 // 60))
                
                return 'online'
                
        except Exception as e:
            logger.error(f"Fibocom status check error: {str(e)}")
            
        return 'offline'

    async def set_network_mode(self, device: Device, mode: str) -> bool:
        """Set network mode (Auto/LTE/WCDMA)"""
        if mode not in self.NETWORK_MODES:
            return False
            
        try:
            cmd = f"{self.FIBOCOM_COMMANDS['SET_RAT']}{self.NETWORK_MODES[mode]}"
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
            cmd = f"{self.FIBOCOM_COMMANDS['SET_BANDS']}{self.BAND_CONFIGS[bands]}"
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"Band configuration error: {str(e)}")
            return False

    async def set_usb_mode(self, device: Device, mode: str) -> bool:
        """Switch USB mode (MBIM/ECM/RNDIS)"""
        mode_cmd = {
            'mbim': self.FIBOCOM_COMMANDS['SET_MBIM'],
            'ecm': self.FIBOCOM_COMMANDS['SET_ECM'],
            'rndis': self.FIBOCOM_COMMANDS['SET_RNDIS']
        }
        
        if mode not in mode_cmd:
            return False
            
        try:
            response = await self.send_at_command(device.port, mode_cmd[mode])
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"USB mode error: {str(e)}")
            return False

    async def update_firmware(self, device: Device, firmware_path: str) -> bool:
        """Update device firmware"""
        try:
            cmd = f"{self.FIBOCOM_COMMANDS['FIRMWARE_UPDATE']}\"{firmware_path}\""
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"Firmware update error: {str(e)}")
            return False

    async def factory_reset(self, device: Device) -> bool:
        """Perform factory reset"""
        try:
            response = await self.send_at_command(
                device.port,
                self.FIBOCOM_COMMANDS['FACTORY_RESET']
            )
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"Factory reset error: {str(e)}")
            return False

    async def configure_carrier_aggregation(self, device: Device, enabled: bool) -> bool:
        """Configure carrier aggregation settings"""
        try:
            cmd = f"{self.FIBOCOM_COMMANDS['CA_CONFIG']}{'1' if enabled else '0'}"
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"CA configuration error: {str(e)}")
            return False

    async def toggle_volte(self, device: Device, enabled: bool) -> bool:
        """Enable/disable VoLTE"""
        try:
            cmd = self.FIBOCOM_COMMANDS['VOLTE_ENABLE'] if enabled else self.FIBOCOM_COMMANDS['VOLTE_DISABLE']
            response = await self.send_at_command(device.port, cmd)
            return "OK" in response if response else False
        except Exception as e:
            logger.error(f"VoLTE configuration error: {str(e)}")
            return False

    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new SMS messages"""
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