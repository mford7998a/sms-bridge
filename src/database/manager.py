from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete
from typing import List, Optional, Dict
import logging
from datetime import datetime, timedelta

from .models import Base, Device, Message, DeviceStats, SystemSettings, SystemLog

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, connection_string: str):
        self.engine = create_async_engine(connection_string, echo=True)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self):
        """Initialize database"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def cleanup(self):
        """Cleanup database connections"""
        await self.engine.dispose()

    # Device Operations
    async def add_device(self, device: Device) -> Device:
        async with self.async_session() as session:
            session.add(device)
            await session.commit()
            return device

    async def get_device(self, device_id: str) -> Optional[Device]:
        async with self.async_session() as session:
            result = await session.execute(
                select(Device).where(Device.id == device_id)
            )
            return result.scalar_one_or_none()

    async def get_devices(self) -> List[Device]:
        async with self.async_session() as session:
            result = await session.execute(select(Device))
            return result.scalars().all()

    async def update_device_status(self, device_id: str, status: str):
        async with self.async_session() as session:
            await session.execute(
                update(Device)
                .where(Device.id == device_id)
                .values(status=status, last_seen=datetime.utcnow())
            )
            await session.commit()

    # Message Operations
    async def add_message(self, message: Message) -> Message:
        async with self.async_session() as session:
            session.add(message)
            await session.commit()
            return message

    async def update_message_status(self, message_id: int, status: str):
        async with self.async_session() as session:
            await session.execute(
                update(Message)
                .where(Message.id == message_id)
                .values(status=status, forwarded_at=datetime.utcnow())
            )
            await session.commit()

    # Stats Operations
    async def add_device_stats(self, stats: DeviceStats) -> DeviceStats:
        async with self.async_session() as session:
            session.add(stats)
            await session.commit()
            return stats

    async def get_device_stats(self, device_id: str, hours: int = 24) -> List[DeviceStats]:
        async with self.async_session() as session:
            result = await session.execute(
                select(DeviceStats)
                .where(DeviceStats.device_id == device_id)
                .where(DeviceStats.timestamp >= datetime.utcnow() - timedelta(hours=hours))
                .order_by(DeviceStats.timestamp.desc())
            )
            return result.scalars().all()

    # Settings Operations
    async def get_settings(self) -> Dict:
        async with self.async_session() as session:
            result = await session.execute(select(SystemSettings))
            settings = {}
            for row in result.scalars().all():
                settings[row.key] = row.value
            return settings

    async def update_settings(self, settings: Dict):
        async with self.async_session() as session:
            for key, value in settings.items():
                await session.merge(SystemSettings(
                    key=key,
                    value=value,
                    updated_at=datetime.utcnow()
                ))
            await session.commit()

    # Logging Operations
    async def add_log(self, level: str, message: str, source: str = None, details: Dict = None):
        async with self.async_session() as session:
            log = SystemLog(
                level=level,
                message=message,
                source=source,
                details=details
            )
            session.add(log)
            await session.commit()

    async def get_logs(self, level: str = None, search: str = None, 
                      limit: int = 100) -> List[SystemLog]:
        async with self.async_session() as session:
            query = select(SystemLog).order_by(SystemLog.timestamp.desc())
            
            if level and level != "all":
                query = query.where(SystemLog.level == level)
            if search:
                query = query.where(SystemLog.message.ilike(f"%{search}%"))
                
            query = query.limit(limit)
            result = await session.execute(query)
            return result.scalars().all() 