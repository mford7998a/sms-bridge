import logging
from typing import Dict, Type
from .base import BaseModemManager
from .franklin import FranklinManager
from .sierra import SierraManager
from .huawei import HuaweiManager
from .android import AndroidManager
from .voip import VoipManager

logger = logging.getLogger(__name__)

DEVICE_MANAGERS: Dict[str, Type[BaseModemManager]] = {
    'franklin': FranklinManager,
    'sierra': SierraManager,
    'huawei': HuaweiManager,
    'android': AndroidManager,
    'voip': VoipManager
}

def get_manager(device_type: str) -> BaseModemManager:
    """Get appropriate device manager with error handling"""
    if device_type not in DEVICE_MANAGERS:
        raise ValueError(f"Unsupported device type: {device_type}")
    
    try:
        return DEVICE_MANAGERS[device_type]()
    except Exception as e:
        logger.error(f"Failed to initialize {device_type} manager: {str(e)}")
        raise 