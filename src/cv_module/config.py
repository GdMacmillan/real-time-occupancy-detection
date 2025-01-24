import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict

import dotenv
import yaml
from pydantic import BaseModel, Field, validator

# Load environment variables from .env file
dotenv.load_dotenv()


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


class ConfigLoader:

    def __init__(self, config_dir: Path):
        """Config loader class with environment and profile support."""
        self.config_dir = config_dir
        self.env_prefix = "OCCUPANCY_"

    def _load_yaml(self, profile: str) -> dict:
        """Load YAML configuration file for given profile."""
        config_file = self.config_dir / f"service_config_{profile}.yaml"
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    def _apply_environment_variables(self, config: dict) -> dict:
        """Override configuration with environment variables."""
        env_mappings = {
            "WEBSOCKET_HOST": ("service", "host"),
            "WEBSOCKET_PORT": ("service", "port"),
            "CAMERA_ID": ("camera", "params", "camera_id"),
            "MODEL_CONFIDENCE": ("detector", "model", "confidence_threshold"),
        }

        for env_key, config_path in env_mappings.items():
            env_value = os.getenv(f"{self.env_prefix}{env_key}")
            if env_value is not None:
                current = config
                for key in config_path[:-1]:
                    current = current[key]
                current[config_path[-1]] = self._convert_env_value(env_value)

        return config

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        try:
            # Try converting to int
            return int(value)
        except ValueError:
            try:
                # Try converting to float
                return float(value)
            except ValueError:
                # Try converting to boolean
                if value.lower() in ("true", "false"):
                    return value.lower() == "true"
                # Return as string
                return value

    def load_config(self, profile: str = None) -> ServiceConfig:
        """Load configuration with optional profile overrid."""
        # Determine profile from environment or parameter
        profile = profile or os.getenv(f"{self.env_prefix}PROFILE", "development")

        # Load base configuration
        config_dict = self._load_yaml(profile)

        # Apply environment variables
        config_dict = self._apply_environment_variables(config_dict)

        # Create and validate configuration
        try:
            return ServiceConfig(**config_dict)
        except Exception as e:
            logging.error(f"Configuration validation failed: {e}")
            raise
