from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4

class Device(SQLModel, table=True):
    """Camera device model with user ownership."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    device_id: str = Field(index=True)  # Unique identifier from CV service
    name: str
    type: str  # "webcam" or "realsense"
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_online: bool = Field(default=False)
    latest_image_path: Optional[str] = None
    alert_enabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Owner relationship
    owner_id: UUID = Field(foreign_key="user.id")
    owner: "User" = Relationship(back_populates="devices")
    
    # Detection events relationship
    detections: List["Detection"] = Relationship(back_populates="device")

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