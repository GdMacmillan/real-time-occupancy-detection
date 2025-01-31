from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4

class UserBase(SQLModel):
    """Base user model with shared attributes."""
    email: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class User(UserBase, table=True):
    """User model with authentication and relationships."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    
    # Relationships
    profile: Optional["UserProfile"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False}
    )
    devices: List["Device"] = Relationship(back_populates="owner")

class UserProfile(SQLModel, table=True):
    """Extended user profile information."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    notification_enabled: bool = Field(default=True)
    
    # Relationship back to user
    user: User = Relationship(back_populates="profile")
