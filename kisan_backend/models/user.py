import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, String, DateTime
from enum import Enum

class UserRole(str, Enum):
    FARMER = "farmer"
    OWNER = "owner"

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone_number: str = Field(sa_column=Column(String, unique=True, index=True))
    role: UserRole = Field(default=UserRole.FARMER)
    language: str = Field(default="en")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    last_login: Optional[datetime] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True
