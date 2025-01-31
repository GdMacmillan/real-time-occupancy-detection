from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, JSON, Relationship
from uuid import UUID, uuid4
import json

class Detection(SQLModel, table=True):
    """Detection event model linked to devices."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    detected: bool
    count: int
    confidence: str = Field(default="[]", sa_type=JSON)  # Store as JSON string
    frame_number: int
    fps: float
    
    # Device relationship
    device_id: UUID = Field(foreign_key="device.id")
    device: "Device" = Relationship(back_populates="detections")
    
    def __init__(self, **data):
        # Convert confidence list to JSON string if it's a list
        if "confidence" in data and isinstance(data["confidence"], list):
            data["confidence"] = json.dumps(data["confidence"])
        super().__init__(**data)
    
    @property
    def confidence_list(self) -> List[float]:
        """Get confidence values as a list."""
        try:
            return json.loads(self.confidence)
        except (json.JSONDecodeError, TypeError):
            return []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "detected": True,
                "count": 2,
                "confidence": "[0.95, 0.87]",
                "frame_number": 1,
                "fps": 30.0
            }
        } 