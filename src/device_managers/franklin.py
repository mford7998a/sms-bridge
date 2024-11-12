from typing import List, Optional
import re
import aiohttp
import hashlib
import asyncio
import logging
from datetime import datetime

from .base import BaseModemManager
from src.models import Device, SMS

logger = logging.getLogger(__name__)

class FranklinManager(BaseModemManager):
    """Manager for Franklin Wireless modems"""
    
    # API Endpoints
    ENDPOINTS = {
        'login': '/api/v1/login',
        'sms_list': '/api/v1/sms/list',
        'sms_send': '/api/v1/sms/send',
        'sms_delete': '/api/v1/sms/delete',
        'device_info': '/api/v1/device/info',
        'signal_info': '/api/v1/device/signal',
        'network_info': '/api/v1/network/info',
        'change_password': '/api/v1/settings/password'
    }

    def __init__(self, db):
        super().__init__(db)
        self.auth_token = None
        self.base_url = None
        self._session = None

    @property
    async def session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _initialize_modem(self, device: Device) -> bool:
        """Initialize Franklin modem"""
        try:
            # Set base URL
            self.base_url = f"http://{device.config.get('ip', '192.168.1.1')}"
            
            # Login to device
            if not await self._login(device):
                return False
                
            # Get device information
            device_info = await self._get_device_info(device)
            if device_info:
                device.config.update(device_info)
                
            return True
            
        except Exception as e:
            logger.error(f"Franklin initialization error: {str(e)}")
            return False

    async def _login(self, device: Device) -> bool:
        """Login to device API"""
        try:
            password = device.config.get('password', 'admin')
            payload = {
                'password': hashlib.md5(password.encode()).hexdigest()
            }
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['login']}", 
                json=payload
            ) as response:
                data = await response.json()
                if data.get('success'):
                    self.auth_token = data.get('token')
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new messages"""
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
                if not data.get('success'):
                    return messages
                    
                for msg in data.get('messages', []):
                    message = SMS(
                        device_id=device.id,
                        from_number=msg['sender'],
                        to_number=device.phone_number,
                        text=msg['text'],
                        received_at=datetime.fromtimestamp(msg['timestamp']),
                        delivered=False
                    )
                    messages.append(message)
                    
                    # Delete processed message
                    await self._delete_message(msg['id'])
                    
                return messages
                
        except Exception as e:
            logger.error(f"Check messages error: {str(e)}")
            return messages

    async def send_message(self, device: Device, to_number: str, text: str) -> bool:
        """Send SMS message"""
        if not self.auth_token and not await self._login(device):
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            payload = {
                'to': to_number,
                'text': text
            }
            
            client = await self.session
            async with client.post(
                f"{self.base_url}{self.ENDPOINTS['sms_send']}", 
                headers=headers,
                json=payload
            ) as response:
                data = await response.json()
                return data.get('success', False)
                
        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
            return False

    async def get_signal_strength(self, device: Device) -> Optional[int]:
        """Get current signal strength"""
        if not self.auth_token and not await self._login(device):
            return None
            
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            client = await self.session
            async with client.get(
                f"{self.base_url}{self.ENDPOINTS['signal_info']}", 
                headers=headers
            ) as response:
                data = await response.json()
                if data.get('success'):
                    signal = data.get('signal', {}).get('rssi')
                    if signal is not None:
                        return min(abs(signal + 100), 100)  # Convert dBm to percentage
                return None
                
        except Exception as e:
            logger.error(f"Signal strength error: {str(e)}")
            return None

    async def cleanup(self, device: Device):
        """Cleanup resources"""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            self.auth_token = None
            await super().cleanup(device)
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")