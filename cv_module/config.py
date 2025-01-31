import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

import dotenv
import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
dotenv.load_dotenv()

logger = logging.getLogger("cv_module.config")


class CameraType(str, Enum):
    WEBCAM = "webcam"
    REALSENSE = "realsense"


class DetectorType(str, Enum):
    YOLO = "yolo"


class YOLOModel(str, Enum):
    NANO = "yolov8n.pt"
    SMALL = "yolov8s.pt"
    MEDIUM = "yolov8m.pt"
    LARGE = "yolov8l.pt"
    XLARGE = "yolov8x.pt"


class CameraConfig(BaseModel):
    type: CameraType
    params: Dict[str, Any]

    @validator("params")
    def validate_camera_params(cls, v, values):
        if values["type"] == CameraType.WEBCAM:
            required = {"camera_id"}
        elif values["type"] == CameraType.REALSENSE:
            required = {"resolution", "fps"}

        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required params for {values['type']}: {missing}")
        return v


class DetectorConfig(BaseModel):
    type: DetectorType
    model: Dict[str, Any]

    @validator("model")
    def validate_model_config(cls, v):
        required = {"name", "confidence_threshold"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required model parameters: {missing}")

        if v["name"] not in [model.value for model in YOLOModel]:
            raise ValueError(f"Invalid YOLO model name: {v['name']}")

        if not 0 <= v["confidence_threshold"] <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")

        # Set defaults for optional parameters
        v.setdefault("verbose", False)
        v.setdefault("summary_interval", 30)

        return v


class WebSocketConfig(BaseModel):
    max_clients: int = Field(gt=0)
    message_queue_size: int = Field(gt=0)
    ping_interval: int = Field(gt=0)
    ping_timeout: int = Field(gt=0)


class ServiceConfig(BaseModel):
    service: dict = Field(..., description="Service configuration settings")
    camera: CameraConfig
    detector: DetectorConfig
    websocket: WebSocketConfig
    environment: str = Field(default="development")

    @property
    def host(self) -> str:
        return self.service["host"]

    @property
    def port(self) -> int:
        return self.service["port"]

    @property
    def log_dir(self) -> Path:
        return Path(self.service["log_dir"])

    @validator("service")
    def validate_service(cls, v):
        required = {"host", "port", "log_dir"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"Missing required service parameters: {missing}")

        if not (0 < v["port"] < 65536):
            raise ValueError("Port must be between 1 and 65535")

        return v


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CVModuleSettings(BaseSettings):
    """Environment-based settings for CV module."""
    # Environment
    CV_MODULE_ENV: str = Field(
        "development",
        description="Environment name (development/production)"
    )
    
    # Service settings
    CV_MODULE_HOST: str = Field(
        "localhost",
        description="Service host address"
    )
    CV_MODULE_PORT: int = Field(
        8765,
        description="Service port number",
        gt=0,
        lt=65536
    )
    CV_MODULE_LOG_DIR: Path = Field(
        Path("logs/dev"),
        description="Log directory path"
    )
    CV_MODULE_LOG_LEVEL: LogLevel = Field(
        LogLevel.INFO,
        description="Logging level"
    )
    
    # Camera settings
    CV_MODULE_CAMERA_TYPE: CameraType = Field(
        CameraType.WEBCAM,
        description="Camera type (webcam/realsense)"
    )
    CV_MODULE_CAMERA_ID: Optional[int] = Field(
        None,
        description="Camera device ID for webcam"
    )
    
    # Detector settings
    CV_MODULE_MODEL_NAME: str = Field(
        "yolov8n.pt",
        description="YOLO model name"
    )
    CV_MODULE_MODEL_CONFIDENCE: float = Field(
        0.4,
        description="Detection confidence threshold",
        ge=0.0,
        le=1.0
    )

    @validator("CV_MODULE_LOG_DIR")
    def create_log_dir(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v

    @validator("CV_MODULE_MODEL_NAME")
    def validate_model_name(cls, v):
        valid_models = {"yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"}
        if v not in valid_models:
            raise ValueError(f"Invalid model name. Must be one of: {valid_models}")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


class ConfigLoader:
    def __init__(self, config_dir: Path):
        """Initialize config loader with hierarchical configuration support."""
        if not isinstance(config_dir, Path):
            config_dir = Path(config_dir)
            
        if not config_dir.exists():
            raise FileNotFoundError(f"CV module config directory not found: {config_dir}")
            
        self.config_dir = config_dir
        self.shared_config_dir = config_dir.parent.parent / "config"
        
        logger.info(f"Using config directories: module={self.config_dir}, shared={self.shared_config_dir}")
        self.env_settings = self._load_env_settings()

    def _load_env_settings(self) -> CVModuleSettings:
        """Load environment-based settings."""
        logger.debug("Loading environment settings")
        try:
            settings = CVModuleSettings()
            logger.info(f"Environment settings loaded successfully: {settings.model_dump_json(indent=2)}")
            return settings
        except Exception as e:
            logger.error(f"Failed to load environment settings: {e}")
            raise

    def _load_yaml(self, filename: str) -> dict:
        """Load YAML configuration file."""
        config_file = self.config_dir / filename
        logger.info(f"Loading config file: {config_file}")  # Added more logging
        
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return {}
            
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded config content: {config}")  # Log the content
                if not isinstance(config, dict):
                    raise ValueError(f"Invalid config format in {filename}, expected dict got {type(config)}")
                return config
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            raise

    def _merge_configs(self, base: dict, override: dict) -> dict:
        """Deep merge configuration dictionaries."""
        logger.debug(f"Merging configurations:\nBase: {base}\nOverride: {override}")
        result = base.copy()
        for key, value in override.items():
            if isinstance(value, dict) and key in result:
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def load_config(self) -> ServiceConfig:
        """Load configuration following the hierarchy."""
        try:
            # Load configs
            default_config = self._load_yaml("default.yaml")
            logger.info(f"Loaded default config: {default_config}")  # Added logging
            
            env_name = self.env_settings.CV_MODULE_ENV
            env_config = self._load_yaml(f"{env_name}.yaml")
            logger.info(f"Loaded {env_name} config: {env_config}")  # Added logging
            
            # Merge configs
            config = self._merge_configs(default_config, env_config)
            logger.info(f"Merged config: {config}")  # Added logging
            
            # Validate required sections
            required_sections = {"service", "camera", "detector", "websocket"}
            missing = required_sections - set(config.keys())
            if missing:
                raise ValueError(f"Missing required configuration sections: {missing}")
            
            # Validate camera config specifically
            if "camera" not in config:
                raise ValueError("Camera configuration is missing")
            if "type" not in config["camera"]:
                raise ValueError("Camera type is missing from configuration")
            if "params" not in config["camera"]:
                raise ValueError("Camera parameters are missing from configuration")
                
            return ServiceConfig(**config)
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _apply_env_overrides(self, config: dict) -> dict:
        """Apply environment variable overrides to configuration."""
        env = self.env_settings

        # Service overrides
        config.setdefault("service", {})
        config["service"].update({
            "host": env.CV_MODULE_HOST,
            "port": env.CV_MODULE_PORT,
            "log_dir": env.CV_MODULE_LOG_DIR
        })

        # Camera overrides
        if env.CV_MODULE_CAMERA_TYPE:
            config["camera"]["type"] = env.CV_MODULE_CAMERA_TYPE
            if env.CV_MODULE_CAMERA_ID is not None:
                config["camera"]["params"]["camera_id"] = env.CV_MODULE_CAMERA_ID

        # Detector overrides
        if "detector" in config:
            config["detector"]["model"].update({
                "name": env.CV_MODULE_MODEL_NAME,
                "confidence_threshold": env.CV_MODULE_MODEL_CONFIDENCE
            })

        return config

@lru_cache()
def get_settings() -> ServiceConfig:
    """Get cached settings instance."""
    try:
        # Get the absolute path to the cv_module/config directory
        module_dir = Path(__file__).resolve().parent
        config_dir = module_dir / "config"
        
        logger.info(f"Module directory: {module_dir}")
        logger.info(f"Config directory: {config_dir}")
        
        if not config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")
            
        # List available config files for debugging
        config_files = list(config_dir.glob("*.yaml"))
        logger.info(f"Available config files: {config_files}")
        
        loader = ConfigLoader(config_dir=config_dir)
        return loader.load_config()
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise