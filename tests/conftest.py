import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
from src.database.models import Base
from src.config import settings

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_smsbridge"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """Create a test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
def test_client():
    """Create a test client for FastAPI app."""
    return TestClient(app)

@pytest.fixture
def test_settings():
    """Create test settings."""
    return settings

@pytest.fixture
def mock_serial(mocker):
    """Mock serial port communications."""
    mock = mocker.patch('serial.Serial')
    mock.return_value.read.return_value = b'OK\r\n'
    mock.return_value.write.return_value = len(b'AT\r\n')
    return mock

@pytest.fixture
def mock_smshub(mocker):
    """Mock SMS Hub client."""
    mock = mocker.patch('src.smshub_client.SMSHubClient')
    mock.return_value.push_sms.return_value = True
    return mock

@pytest.fixture
def mock_websocket(mocker):
    """Mock WebSocket connections."""
    mock = mocker.patch('fastapi.WebSocket')
    return mock 