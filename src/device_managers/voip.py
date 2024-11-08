from typing import List
import asyncio
from .base import BaseModemManager
from src.models import Device, SMS

class VoipManager(BaseModemManager):
    """
    Manager for VoIP/SIP devices
    """
    
    async def check_status(self, device: Device) -> str:
        # TODO: Implement actual VoIP status check
        # For now, return offline to prevent errors
        return 'offline'

    async def check_messages(self, device: Device) -> List[SMS]:
        # TODO: Implement actual VoIP message checking
        return [] 