from typing import List, Optional
import asyncio
import re
import logging
from datetime import datetime
import json
import adb_shell.adb_device
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen
import os

from .base import BaseModemManager
from src.models import Device, SMS

logger = logging.getLogger(__name__)

class AndroidManager(BaseModemManager):
    """Manager for Android devices using ADB"""
    
    def __init__(self, db):
        super().__init__(db)
        self._adb_connections = {}
        self._initialize_adb_auth()

    def _initialize_adb_auth(self):
        """Initialize ADB authentication"""
        try:
            # Create ADB keys directory if it doesn't exist
            adb_dir = os.path.expanduser('~/.android')
            if not os.path.exists(adb_dir):
                os.makedirs(adb_dir)

            # Generate ADB key pair if they don't exist
            priv_key_path = os.path.join(adb_dir, 'adbkey')
            pub_key_path = os.path.join(adb_dir, 'adbkey.pub')
            
            if not (os.path.exists(priv_key_path) and os.path.exists(pub_key_path)):
                keygen(priv_key_path)

            # Load the keys
            with open(priv_key_path, 'rb') as f:
                priv_key = f.read()
            with open(pub_key_path, 'rb') as f:
                pub_key = f.read()

            self.signer = PythonRSASigner(pub_key, priv_key)
            
        except Exception as e:
            logger.error(f"ADB auth initialization error: {str(e)}")
            raise

    async def _initialize_modem(self, device: Device) -> bool:
        """Initialize Android device connection"""
        try:
            # Connect to device via ADB
            adb_device = adb_shell.adb_device.AdbDeviceTcp(
                device.config.get('ip', '127.0.0.1'),
                device.config.get('port', 5555),
                default_transport_timeout_s=30
            )
            
            # Connect and authenticate
            adb_device.connect(rsa_keys=[self.signer], auth_timeout_s=30)
            
            # Store connection
            self._adb_connections[device.id] = adb_device
            
            # Get device information
            device_info = await self._get_device_info(device)
            if device_info:
                device.config.update(device_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Android device initialization error: {str(e)}")
            return False

    async def _get_device_info(self, device: Device) -> dict:
        """Get Android device information"""
        try:
            adb = self._adb_connections.get(device.id)
            if not adb:
                return {}

            info = {}
            # Get device model
            model = adb.shell('getprop ro.product.model').strip()
            info['model'] = model

            # Get Android version
            version = adb.shell('getprop ro.build.version.release').strip()
            info['android_version'] = version

            # Get IMEI
            imei = adb.shell('service call iphonesubinfo 1').strip()
            if imei:
                # Parse IMEI from service call response
                imei = re.findall(r"'([0-9a-fA-F]+)'", imei)
                if imei:
                    info['imei'] = ''.join(imei).replace('.', '')

            return info
            
        except Exception as e:
            logger.error(f"Get device info error: {str(e)}")
            return {}

    async def check_messages(self, device: Device) -> List[SMS]:
        """Check for new messages using Android content provider"""
        messages = []
        try:
            adb = self._adb_connections.get(device.id)
            if not adb:
                return messages

            # Query SMS content provider
            cmd = (
                'content query --uri content://sms/inbox '
                '--projection "_id,address,body,date,read" '
                '--where "read=0"'
            )
            output = adb.shell(cmd)

            # Parse messages
            for line in output.splitlines():
                if not line.strip():
                    continue
                    
                try:
                    # Parse content query output
                    msg_data = dict(item.split('=', 1) for item in line.split(' '))
                    
                    message = SMS(
                        device_id=device.id,
                        from_number=msg_data['address'].strip('"'),
                        to_number=device.phone_number,
                        text=msg_data['body'].strip('"'),
                        received_at=datetime.fromtimestamp(int(msg_data['date'])/1000),
                        delivered=False
                    )
                    messages.append(message)
                    
                    # Mark message as read
                    adb.shell(
                        f'content update --uri content://sms/{msg_data["_id"]} '
                        '--bind read:i:1'
                    )
                    
                except Exception as e:
                    logger.error(f"Message parsing error: {str(e)}")
                    continue

            return messages
            
        except Exception as e:
            logger.error(f"Check messages error: {str(e)}")
            return messages

    async def send_message(self, device: Device, to_number: str, text: str) -> bool:
        """Send SMS using Android telephony manager"""
        try:
            adb = self._adb_connections.get(device.id)
            if not adb:
                return False

            # Create and execute intent to send SMS
            cmd = (
                'am broadcast -a android.provider.Telephony.SMS_SEND '
                f'-n com.android.mms/.transaction.SmsReceiverService '
                f'--es "address" "{to_number}" '
                f'--es "sms_body" "{text}"'
            )
            output = adb.shell(cmd)
            
            return "Broadcast completed" in output
            
        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
            return False

    async def get_signal_strength(self, device: Device) -> Optional[int]:
        """Get signal strength using Android telephony manager"""
        try:
            adb = self._adb_connections.get(device.id)
            if not adb:
                return None

            # Get signal strength using telephony manager
            cmd = (
                'dumpsys telephony.registry | '
                'grep -i signalstrength'
            )
            output = adb.shell(cmd)
            
            # Parse signal strength
            match = re.search(r'SignalStrength:\s*(\d+)', output)
            if match:
                signal = int(match.group(1))
                return min(signal * 3.226, 100)  # Convert to percentage
                
            return None
            
        except Exception as e:
            logger.error(f"Signal strength error: {str(e)}")
            return None

    async def cleanup(self, device: Device):
        """Cleanup Android device connection"""
        try:
            adb = self._adb_connections.pop(device.id, None)
            if adb:
                adb.close()
            await super().cleanup(device)
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")