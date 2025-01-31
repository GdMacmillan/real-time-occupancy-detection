from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger("backend.config")

class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

class DatabaseConfig(BaseModel):
    type: DatabaseType
    url: str

    @validator("url")
    def validate_database_url(cls, v, values):
        if values["type"] == DatabaseType.SQLITE:
            if not v.startswith("sqlite:///"):
                raise ValueError("SQLite URL must start with sqlite:///")
        return v

class WebSocketConfig(BaseModel):
    host: str
    port: int
    path: str = "/ws"

class APIConfig(BaseModel):
    websocket: WebSocketConfig

class ServiceConfig(BaseModel):
    """Service configuration model."""
    api: APIConfig = Field(..., description="API configuration")
    service: Dict[str, Any] = Field(..., description="Service configuration")
    database: DatabaseConfig = Field(..., description="Database configuration")
    logging: Dict[str, Any] = Field(..., description="Logging configuration")

    @validator("service")
    def validate_service(cls, v):
        required = {"host", "port", "log_dir"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required service parameters: {missing}")
        return v

    @validator("logging")
    def validate_logging(cls, v):
        required = {"level"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required logging parameters: {missing}")
        return v

class Settings(BaseSettings):
    # API Settings
    APP_NAME: str = "Occupancy Detection API"
    DEBUG: bool = False
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./occupancy.db"
    
    # WebSocket
    WS_HOST: str = "127.0.0.1"
    WS_PORT: int = 8765
    WS_PATH: str = "/ws"
    WS_URL: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DIR: str = "logs/dev"

    @validator("WS_URL", pre=True, always=True)
    def assemble_ws_url(cls, v, values):
        if v is not None:
            return v
        ws_host = values.get("WS_HOST", "127.0.0.1")
        ws_port = values.get("WS_PORT", 8765)
        ws_path = values.get("WS_PATH", "/ws")
        return f"ws://{ws_host}:{ws_port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def log_config(self):
        """Log current configuration."""
        logger.info(f"Settings loaded:")
        logger.info(f"  HOST: {self.HOST}")
        logger.info(f"  PORT: {self.PORT}")
        logger.info(f"  WS_URL: {self.WS_URL}")

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.log_config()
    return settings 