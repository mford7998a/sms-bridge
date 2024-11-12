from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)  # franklin, sierra, huawei, android, voip
    phone_number = Column(String, nullable=False)
    sim_iccid = Column(String)
    port = Column(String)
    model = Column(String)
    config = Column(JSON, default={})
    status = Column(String, default="offline")
    signal_strength = Column(Integer)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="device")
    stats = relationship("DeviceStats", back_populates="device")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String, ForeignKey("devices.id"))
    from_number = Column(String, nullable=False)
    to_number = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    forwarded_at = Column(DateTime)
    status = Column(String, default="pending")  # pending, delivered, failed
    
    device = relationship("Device", back_populates="messages")

class DeviceStats(Base):
    __tablename__ = "device_stats"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String, ForeignKey("devices.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    signal_strength = Column(Integer)
    network_type = Column(String)
    operator = Column(String)
    cell_id = Column(String)
    messages_sent = Column(Integer, default=0)
    messages_received = Column(Integer, default=0)
    
    device = relationship("Device", back_populates="stats")

class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String)
    details = Column(JSON) 