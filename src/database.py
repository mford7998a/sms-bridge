from typing import List, Optional, Dict
import asyncio
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import text
import redis.asyncio as redis
from contextlib import asynccontextmanager
from tenacity import retry, stop_after_attempt, wait_exponential
from src.models import Device, SMS

logger = logging.getLogger(__name__)

Base = declarative_base()

class DeviceModel(Base):
    __tablename__ = 'devices'
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    sim_iccid = Column(String)
    signal_strength = Column(Integer)
    status = Column(String, nullable=False)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    config = Column(JSON, default={})
    signal_details = Column(JSON, default={})
    device_metadata = Column(JSON, default={})

class SMSModel(Base):
    __tablename__ = 'sms_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.id'), nullable=False)
    from_number = Column(String, nullable=False)
    to_number = Column(String, nullable=False)
    text = Column(String, nullable=False)
    received_at = Column(DateTime, nullable=False)
    delivered = Column(Boolean, default=False)
    delivery_attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime)
    error_message = Column(String)

class Database:
    def __init__(self, connection_url: str = None, redis_url: str = None):
        # Default to PostgreSQL if no URL provided
        self.db_url = connection_url or "postgresql+asyncpg://smsuser:audioplex@localhost/smsdb"
        self.redis_url = redis_url or "redis://localhost"
        
        # Configure SQLAlchemy engine with connection pooling
        self.engine = create_async_engine(
            self.db_url,
            pool_size=20,
            max_overflow=30,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Initialize Redis for caching
        self.redis = redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize database and create tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """Get database session with automatic cleanup"""
        session = self.async_session()
        try:
            yield session
        finally:
            await session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_all_devices(self) -> List[Device]:
        """Get all devices with caching"""
        # Try cache first
        cached = await self.redis.get("all_devices")
        if cached:
            return [Device.parse_raw(d) for d in cached.split('|||')]
            
        async with self.get_session() as session:
            result = await session.execute(select(DeviceModel))
            devices = []
            for row in result.scalars():
                device = Device(
                    id=row.id,
                    type=row.type,
                    phone_number=row.phone_number,
                    sim_iccid=row.sim_iccid,
                    signal_strength=row.signal_strength,
                    status=row.status,
                    first_seen=row.first_seen,
                    last_seen=row.last_seen
                )
                devices.append(device)
                
            # Cache results
            cache_data = '|||'.join(d.json() for d in devices)
            await self.redis.setex("all_devices", self.cache_ttl, cache_data)
            
            return devices

    async def update_device_status(self, device_id: str, status: str):
        """Update device status and invalidate cache"""
        async with self.get_session() as session:
            await session.execute(
                update(DeviceModel)
                .where(DeviceModel.id == device_id)
                .values(
                    status=status,
                    last_seen=datetime.utcnow()
                )
            )
            await session.commit()
            
        # Invalidate cache
        await self.redis.delete("all_devices")

    async def mark_sms_delivered(self, sms_id: int):
        """Mark SMS as delivered"""
        async with self.get_session() as session:
            await session.execute(
                update(SMSModel)
                .where(SMSModel.id == sms_id)
                .values(
                    delivered=True,
                    delivery_attempts=SMSModel.delivery_attempts + 1,
                    last_attempt=datetime.utcnow()
                )
            )
            await session.commit()

    async def queue_sms_retry(self, sms_id: int, error: str = None):
        """Queue SMS for retry with exponential backoff"""
        async with self.get_session() as session:
            sms = await session.get(SMSModel, sms_id)
            if sms:
                attempts = sms.delivery_attempts + 1
                # Calculate next retry with exponential backoff
                retry_after = datetime.utcnow() + timedelta(
                    seconds=min(300, 2 ** attempts)
                )
                
                await session.execute(
                    update(SMSModel)
                    .where(SMSModel.id == sms_id)
                    .values(
                        delivery_attempts=attempts,
                        last_attempt=datetime.utcnow(),
                        error_message=error,
                        retry_after=retry_after
                    )
                )
                await session.commit()

    async def cleanup_old_messages(self, days: int = 30):
        """Cleanup old messages"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with self.get_session() as session:
            await session.execute(
                text(
                    "DELETE FROM sms_messages WHERE "
                    "delivered = true AND received_at < :cutoff"
                ),
                {"cutoff": cutoff}
            )
            await session.commit()

    async def get_device_stats(self, device_id: str) -> Dict:
        """Get device statistics"""
        async with self.get_session() as session:
            result = await session.execute(
                text("""
                    SELECT 
                        COUNT(*) as total_messages,
                        SUM(CASE WHEN delivered THEN 1 ELSE 0 END) as delivered,
                        AVG(delivery_attempts) as avg_attempts,
                        MAX(received_at) as last_message
                    FROM sms_messages 
                    WHERE device_id = :device_id
                    AND received_at > NOW() - INTERVAL '24 hours'
                """),
                {"device_id": device_id}
            )
            return dict(result.fetchone()) 