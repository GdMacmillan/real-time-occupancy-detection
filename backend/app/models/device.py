from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class Device(SQLModel, table=True):
    """Camera device model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(index=True)  # Unique identifier from CV service
    name: str
    type: str  # "webcam" or "realsense"
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_online: bool = Field(default=False)
    latest_image_path: Optional[str] = None
    alert_enabled: bool = Field(default=False)

    class Config:
        schema_extra = {
            "example": {
                "device_id": "cam_01",
                "name": "Living Room Camera",
                "type": "realsense",
                "is_online": True,
                "alert_enabled": False
            }
        } 