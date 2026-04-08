import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from kisan_backend.models.user import User

class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)
    
    full_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    # Relationship back to User
    user: "User" = Relationship(back_populates="profile")

    class Config:
        arbitrary_types_allowed = True
