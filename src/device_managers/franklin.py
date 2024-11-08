import aiohttp
import asyncio
from typing import List, Dict
import hashlib
import json
import logging
from datetime import datetime
from .base import BaseModemManager
from src.models import Device, SMS

logger = logging.getLogger(__name__)

class FranklinManager(BaseModemManager):
    """
    Manager for Franklin Wireless T9 (R717) and T10 devices
    Includes advanced configuration and unlocking features
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://192.168.1.1"
        self._session = None
        self.auth_token = None
        
        # API endpoints
        self.ENDPOINTS = {
            # Authentication
            'login': '/api/login',
            'change_password': '/api/admin/password',
            
            # Device Info
            'status': '/api/status',
            'device_info': '/api/device/info',
            'signal': '/api/signal',
            
            # Network Configuration
            'network': '/api/network/settings',
            'bands': '/api/network/bands',
            'carrier': '/api/network/carrier',
            'apn': '/api/network/apn',
            'roaming': '/api/network/roaming',
            
            # SMS
            'sms_list': '/api/sms/list',
            'sms_delete': '/api/sms/delete',
            'sms_send': '/api/sms/send',
            
            # Advanced Settings
            'engineering': '/api/device/engineering',
            'carrier_aggr': '/api/network/ca',
            'volte': '/api/network/volte',
            'unlock': '/api/device/unlock',
            'factory_reset': '/api/device/reset'
        }

        # Network modes
        self.NETWORK_MODES = {
            'auto': 0,      # Automatic
            'lte_only': 1,  # LTE Only
            'cdma_only': 2, # CDMA Only
            'gsm_only': 3   # GSM Only
        }

        # Band configurations
        self.BAND_CONFIGS = {
            'all': 0xFFFFFFFF,  # All bands
            'sprint': 0x0000842, # Sprint bands (B2,B4,B12)
            'tmobile': 0x0080842 # T-Mobile bands (B2,B4,B12,B71)
        }

    @property
    async def session(self):
        """Lazy initialization of HTTP session"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _login(self, device: Device) -> bool:
        """Login to device web interface"""
        try:
            password = device.config.get('password', 'admin')
            pwd_hash = hashlib.md5(password.encode()).hexdigest()
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['login']}", 
                json={"password": pwd_hash}
            ) as response:
                data = await response.json()
                if data.get('success'):
                    self.auth_token = data.get('token')
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Franklin login error: {str(e)}")
            return False

    async def initialize_device(self, device: Device) -> bool:
        """Initialize device with optimal settings"""
        try:
            if not await self._login(device):
                return False

            # Get device info
            info = await self._get_device_info(device)
            if info:
                device.model = info.get('model')
                device.sim_iccid = info.get('iccid')
                device.config.update({
                    'imei': info.get('imei'),
                    'firmware': info.get('firmware'),
                    'hardware': info.get('hardware')
                })
            
            return True
            
        except Exception as e:
            logger.error(f"Franklin initialization error: {str(e)}")
            return False

    async def check_status(self, device: Device) -> str:
        """Check device status and signal strength"""
        if not self.auth_token and not await self._login(device):
            return 'offline'

        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            # Get signal info
            client = await self.session
            async with client.get(
                f"{self.base_url}{self.ENDPOINTS['signal']}",
                headers=headers
            ) as response:
                data = await response.json()
                
                if data.get('success'):
                    signal_info = data['data']
                    
                    # Store detailed signal info
                    device.signal_details = {
                        'rssi': signal_info.get('rssi'),
                        'rsrp': signal_info.get('rsrp'),
                        'rsrq': signal_info.get('rsrq'),
                        'sinr': signal_info.get('sinr'),
                        'band': signal_info.get('band'),
                        'bandwidth': signal_info.get('bandwidth'),
                        'cell_id': signal_info.get('cellId'),
                        'pci': signal_info.get('pci')
                    }
                    
                    # Convert RSRP to percentage (-140 dBm = 0%, -80 dBm = 100%)
                    rsrp = int(signal_info.get('rsrp', -140))
                    device.signal_strength = min(100, max(0, (rsrp + 140) * 100 // 60))
                    
                    return 'online'
                    
        except Exception as e:
            logger.error(f"Franklin status check error: {str(e)}")
            
        return 'offline'

    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new SMS messages"""
        messages = []
        
        if not self.auth_token and not await self._login(device):
            return messages

        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            client = await self.session
            async with client.get(
                f"{self.base_url}{self.ENDPOINTS['sms_list']}",
                headers=headers
            ) as response:
                data = await response.json()
                
                if data.get('success') and 'messages' in data:
                    for msg_data in data['messages']:
                        if msg_data['type'] == 'received':
                            sms = SMS(
                                device_id=device.id,
                                from_number=msg_data['sender'],
                                to_number=device.phone_number,
                                text=msg_data['content'],
                                received_at=datetime.fromtimestamp(
                                    int(msg_data['timestamp'])
                                ),
                                delivered=False
                            )
                            messages.append(sms)
                            
                            # Delete processed message
                            await self._delete_message(msg_data['id'])
                            
        except Exception as e:
            logger.error(f"Franklin SMS check error: {str(e)}")
            
        return messages

    async def _delete_message(self, msg_id: str) -> bool:
        """Delete a message by ID"""
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['sms_delete']}",
                headers=headers,
                json={'id': msg_id}
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def _get_device_info(self, device: Device) -> Dict:
        """Get detailed device information"""
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            client = await self.session
            async with client.get(
                f"{self.base_url}{self.ENDPOINTS['device_info']}",
                headers=headers
            ) as response:
                data = await response.json()
                return data.get('data', {}) if data.get('success') else {}
                
        except Exception:
            return {}

    async def change_password(self, device: Device, new_password: str) -> bool:
        """Change admin password"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {
                'new_password': hashlib.md5(new_password.encode()).hexdigest()
            }
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['change_password']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                if data.get('success'):
                    device.config['password'] = new_password
                    return True
                return False
                
        except Exception:
            return False

    async def set_network_mode(self, device: Device, mode: str) -> bool:
        """Set network mode (Auto/LTE/CDMA/GSM)"""
        if mode not in self.NETWORK_MODES:
            return False
            
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {'mode': self.NETWORK_MODES[mode]}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['network']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def configure_bands(self, device: Device, bands: List[int]) -> bool:
        """Configure specific LTE bands"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {'bands': bands}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['bands']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def set_apn(self, device: Device, apn: str, 
                      username: str = None, password: str = None) -> bool:
        """Configure APN settings"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {
                'apn': apn,
                'username': username,
                'password': password
            }
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['apn']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def toggle_carrier_aggregation(self, device: Device, enabled: bool) -> bool:
        """Enable/disable carrier aggregation"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {'enabled': enabled}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['carrier_aggr']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def toggle_volte(self, device: Device, enabled: bool) -> bool:
        """Enable/disable VoLTE (T10 only)"""
        if not device.model or 'T10' not in device.model:
            return False
            
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {'enabled': enabled}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['volte']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def unlock_device(self, device: Device, unlock_code: str) -> bool:
        """Unlock device with provided code"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {'code': unlock_code}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['unlock']}",
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def factory_reset(self, device: Device) -> bool:
        """Perform factory reset"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['factory_reset']}",
                headers=headers
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception:
            return False

    async def close(self):
        """Close the client session"""
        if self._session:
            await self._session.close()
            self._session = None