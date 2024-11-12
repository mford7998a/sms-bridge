from typing import List, Optional
import asyncio
import logging
from datetime import datetime
import aiohttp
import json
from urllib.parse import urljoin

from .base import BaseModemManager
from src.models import Device, SMS

logger = logging.getLogger(__name__)

class VoipManager(BaseModemManager):
    """Manager for VoIP/SIP SMS services"""
    
    def __init__(self, db):
        super().__init__(db)
        self._sessions = {}
        self._api_tokens = {}

    async def _initialize_modem(self, device: Device) -> bool:
        """Initialize VoIP service connection"""
        try:
            # Get service configuration
            service_type = device.config.get('service_type')
            if not service_type:
                logger.error("VoIP service type not specified")
                return False

            # Initialize service-specific client
            if service_type == 'twilio':
                return await self._initialize_twilio(device)
            elif service_type == 'nexmo':
                return await self._initialize_nexmo(device)
            elif service_type == 'plivo':
                return await self._initialize_plivo(device)
            else:
                logger.error(f"Unsupported VoIP service type: {service_type}")
                return False
                
        except Exception as e:
            logger.error(f"VoIP initialization error: {str(e)}")
            return False

    async def _initialize_twilio(self, device: Device) -> bool:
        """Initialize Twilio client"""
        try:
            account_sid = device.config.get('account_sid')
            auth_token = device.config.get('auth_token')
            
            if not (account_sid and auth_token):
                logger.error("Twilio credentials not provided")
                return False

            # Create session for API calls
            auth = aiohttp.BasicAuth(account_sid, auth_token)
            session = aiohttp.ClientSession(auth=auth)
            self._sessions[device.id] = session

            # Test authentication
            async with session.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
            ) as response:
                if response.status != 200:
                    logger.error("Twilio authentication failed")
                    return False

            return True
            
        except Exception as e:
            logger.error(f"Twilio initialization error: {str(e)}")
            return False

    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new messages from VoIP service"""
        messages = []
        try:
            service_type = device.config.get('service_type')
            if service_type == 'twilio':
                messages = await self._check_twilio_messages(device)
            elif service_type == 'nexmo':
                messages = await self._check_nexmo_messages(device)
            elif service_type == 'plivo':
                messages = await self._check_plivo_messages(device)
                
            return messages
            
        except Exception as e:
            logger.error(f"Check messages error: {str(e)}")
            return messages

    async def _check_twilio_messages(self, device: Device) -> List[SMS]:
        """Check for new Twilio messages"""
        messages = []
        try:
            session = self._sessions.get(device.id)
            if not session:
                return messages

            account_sid = device.config.get('account_sid')
            last_check = device.config.get('last_check', datetime.utcnow().isoformat())

            # Get messages since last check
            url = (
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
                f"?DateSent>={last_check}"
            )
            
            async with session.get(url) as response:
                if response.status != 200:
                    return messages
                    
                data = await response.json()
                for msg in data.get('messages', []):
                    if msg['direction'] == 'inbound':
                        message = SMS(
                            device_id=device.id,
                            from_number=msg['from'],
                            to_number=msg['to'],
                            text=msg['body'],
                            received_at=datetime.fromisoformat(msg['date_created']),
                            delivered=False
                        )
                        messages.append(message)

            # Update last check time
            device.config['last_check'] = datetime.utcnow().isoformat()
            return messages
            
        except Exception as e:
            logger.error(f"Check Twilio messages error: {str(e)}")
            return messages

    async def send_message(self, device: Device, to_number: str, text: str) -> bool:
        """Send message through VoIP service"""
        try:
            service_type = device.config.get('service_type')
            if service_type == 'twilio':
                return await self._send_twilio_message(device, to_number, text)
            elif service_type == 'nexmo':
                return await self._send_nexmo_message(device, to_number, text)
            elif service_type == 'plivo':
                return await self._send_plivo_message(device, to_number, text)
                
            return False
            
        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
            return False

    async def _send_twilio_message(self, device: Device, to_number: str, text: str) -> bool:
        """Send message through Twilio"""
        try:
            session = self._sessions.get(device.id)
            if not session:
                return False

            account_sid = device.config.get('account_sid')
            from_number = device.phone_number

            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            payload = {
                'To': to_number,
                'From': from_number,
                'Body': text
            }
            
            async with session.post(url, data=payload) as response:
                return response.status == 201
                
        except Exception as e:
            logger.error(f"Send Twilio message error: {str(e)}")
            return False

    async def get_signal_strength(self, device: Device) -> Optional[int]:
        """VoIP services don't have signal strength"""
        return None

    async def cleanup(self, device: Device):
        """Cleanup VoIP service resources"""
        try:
            session = self._sessions.pop(device.id, None)
            if session:
                await session.close()
            await super().cleanup(device)
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

    # Additional VoIP-specific methods
    async def get_account_balance(self, device: Device) -> Optional[float]:
        """Get current account balance"""
        try:
            service_type = device.config.get('service_type')
            if service_type == 'twilio':
                return await self._get_twilio_balance(device)
            # Implement other services as needed
            return None
            
        except Exception as e:
            logger.error(f"Get balance error: {str(e)}")
            return None

    async def _get_twilio_balance(self, device: Device) -> Optional[float]:
        """Get Twilio account balance"""
        try:
            session = self._sessions.get(device.id)
            if not session:
                return None

            account_sid = device.config.get('account_sid')
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Balance.json"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                return float(data.get('balance', 0))
                
        except Exception as e:
            logger.error(f"Get Twilio balance error: {str(e)}")
            return None