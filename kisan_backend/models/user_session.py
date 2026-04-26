import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, String, DateTime, Relationship

if TYPE_CHECKING:
    from kisan_backend.models.user import User

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    
    # Hardware Metadata
    device_id: str = Field(sa_column=Column(String, index=True))
    brand: str = Field(default="unknown")
    model: str = Field(default="unknown")
    os_name: str = Field(default="unknown")
    os_version: str = Field(default="unknown")
    app_version: str = Field(default="unknown")
    ip_address: Optional[str] = Field(default=None)
    
    # Status and Lifecycle
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    last_login_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    logout_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="sessions")

    class Config:
        arbitrary_types_allowed = True
