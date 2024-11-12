from pydantic import BaseSettings
from typing import Dict, Any
import os
import json
from pathlib import Path

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "SMS Bridge"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/smsbridge"
    
    # Redis Settings (for caching)
    REDIS_URL: str = "redis://localhost"
    
    # SMS Hub Settings
    SMSHUB_API_KEY: str = ""
    SMSHUB_BASE_URL: str = "https://smshub.example.com/api"
    
    # Device Settings
    DEVICE_SCAN_INTERVAL: int = 5  # seconds
    MESSAGE_CHECK_INTERVAL: int = 10  # seconds
    MAX_RETRY_ATTEMPTS: int = 3
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "sms_bridge.log"
    
    # Security Settings
    CORS_ORIGINS: list = ["*"]
    ALLOWED_HOSTS: list = ["*"]
    
    # Default Device Configurations
    DEFAULT_DEVICE_CONFIGS: Dict[str, Dict[str, Any]] = {
        "huawei": {
            "baudrate": 115200,
            "timeout": 1,
            "init_commands": [
                "AT",
                "AT+CMGF=1",
                "AT+CSCS=\"GSM\""
            ]
        },
        "sierra": {
            "baudrate": 115200,
            "timeout": 1,
            "init_commands": [
                "AT",
                "AT+CMGF=1",
                "AT+CSCS=\"GSM\""
            ]
        },
        "franklin": {
            "ip": "192.168.1.1",
            "port": 80,
            "timeout": 5
        },
        "android": {
            "adb_port": 5555,
            "timeout": 10
        },
        "voip": {
            "timeout": 30
        }
    }

    class Config:
        env_file = ".env"
        
    @classmethod
    def load_from_file(cls, config_file: str = "config.json") -> "Settings":
        """Load settings from JSON file"""
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                return cls(**config_data)
        return cls()

    def save_to_file(self, config_file: str = "config.json"):
        """Save current settings to JSON file"""
        config_data = self.dict()
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=4)

    def update(self, **kwargs):
        """Update settings"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

# Create global settings instance
settings = Settings.load_from_file()

def initialize_logging():
    """Initialize logging configuration"""
    import logging
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_dir / settings.LOG_FILE),
            logging.StreamHandler()
        ]
    )

    # Set third-party loggers to WARNING
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING) 