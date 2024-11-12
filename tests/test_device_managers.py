import pytest
from src.device_managers import (
    HuaweiManager,
    SierraManager,
    FranklinManager,
    AndroidManager,
    VoipManager
)
from src.models import Device, SMS
from datetime import datetime

@pytest.mark.asyncio
class TestHuaweiManager:
    async def test_initialization(self, test_session, mock_serial):
        manager = HuaweiManager(test_session)
        device = Device(
            id="test_huawei",
            type="huawei",
            phone_number="+1234567890",
            port="COM1"
        )
        
        result = await manager.initialize(device)
        assert result is True
        mock_serial.assert_called_once_with(
            port="COM1",
            baudrate=115200,
            timeout=1
        )

    async def test_check_messages(self, test_session, mock_serial):
        manager = HuaweiManager(test_session)
        device = Device(
            id="test_huawei",
            type="huawei",
            phone_number="+1234567890",
            port="COM1"
        )
        
        # Mock SMS response
        mock_serial.return_value.read.return_value = (
            b'+CMGL: 1,"REC UNREAD","+1234567890",,'
            b'"Test message"\r\nOK\r\n'
        )
        
        messages = await manager.check_messages(device)
        assert len(messages) == 1
        assert messages[0].from_number == "+1234567890"
        assert messages[0].text == "Test message"

    async def test_send_message(self, test_session, mock_serial):
        manager = HuaweiManager(test_session)
        device = Device(
            id="test_huawei",
            type="huawei",
            phone_number="+1234567890",
            port="COM1"
        )
        
        result = await manager.send_message(
            device,
            to_number="+0987654321",
            text="Test outgoing message"
        )
        assert result is True

@pytest.mark.asyncio
class TestSierraManager:
    async def test_band_configuration(self, test_session, mock_serial):
        manager = SierraManager(test_session)
        device = Device(
            id="test_sierra",
            type="sierra",
            phone_number="+1234567890",
            port="COM1"
        )
        
        result = await manager.set_bands(device, "b2_b4_b12")
        assert result is True
        mock_serial.return_value.write.assert_any_call(b'AT!BAND=11\r\n')

@pytest.mark.asyncio
class TestFranklinManager:
    async def test_api_authentication(self, test_session, mocker):
        mock_session = mocker.patch('aiohttp.ClientSession')
        mock_session.return_value.post.return_value.__aenter__.return_value.json.return_value = {
            'success': True,
            'token': 'test_token'
        }
        
        manager = FranklinManager(test_session)
        device = Device(
            id="test_franklin",
            type="franklin",
            phone_number="+1234567890",
            config={'ip': '192.168.1.1', 'password': 'admin'}
        )
        
        result = await manager._login(device)
        assert result is True
        assert manager.auth_token == 'test_token'

@pytest.mark.asyncio
class TestAndroidManager:
    async def test_adb_connection(self, test_session, mocker):
        mock_adb = mocker.patch('adb_shell.adb_device.AdbDeviceTcp')
        
        manager = AndroidManager(test_session)
        device = Device(
            id="test_android",
            type="android",
            phone_number="+1234567890",
            config={'ip': '192.168.1.100', 'port': 5555}
        )
        
        result = await manager._initialize_modem(device)
        assert result is True
        mock_adb.assert_called_once_with(
            '192.168.1.100',
            5555,
            default_transport_timeout_s=30
        )

@pytest.mark.asyncio
class TestVoipManager:
    async def test_twilio_integration(self, test_session, mocker):
        mock_session = mocker.patch('aiohttp.ClientSession')
        mock_session.return_value.post.return_value.__aenter__.return_value.status = 201
        
        manager = VoipManager(test_session)
        device = Device(
            id="test_voip",
            type="voip",
            phone_number="+1234567890",
            config={
                'service_type': 'twilio',
                'account_sid': 'test_sid',
                'auth_token': 'test_token'
            }
        )
        
        result = await manager.send_message(
            device,
            to_number="+0987654321",
            text="Test message"
        )
        assert result is True 