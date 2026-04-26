import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, String, Relationship
from enum import Enum

if TYPE_CHECKING:
    from kisan_backend.models.profile import Profile
    from kisan_backend.models.kyc import KYCDetails
    from kisan_backend.models.user_session import UserSession

class UserRole(str, Enum):
    FARMER = "FARMER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone_number: str = Field(sa_column=Column(String, unique=True, index=True))
    role: UserRole = Field(default=UserRole.FARMER)
    language: str = Field(default="en")
    is_active: bool = Field(default=True)
    is_kyc_completed: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    fcm_token: Optional[str] = Field(default=None)
    
    # Relationships
    profile: Optional["Profile"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False})
    kyc_details: Optional["KYCDetails"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False})
    sessions: list["UserSession"] = Relationship(back_populates="user")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
