import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Column, Float, String, Relationship

if TYPE_CHECKING:
    from kisan_backend.models.user import User

class KYCStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class KYCDetails(SQLModel, table=True):
    __tablename__ = "kyc_details"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, unique=True)
    
    document_type: str = Field(sa_column=Column(String, nullable=False))
    id_number: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    
    front_image_url: str = Field(sa_column=Column(String, nullable=False))
    back_image_url: str = Field(sa_column=Column(String, nullable=False))
    
    latitude: float = Field(sa_column=Column(Float, nullable=False))
    longitude: float = Field(sa_column=Column(Float, nullable=False))
    
    address_line1: str = Field(sa_column=Column(String, nullable=False))
    address_line2: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    city: str = Field(sa_column=Column(String, nullable=False))
    state: str = Field(sa_column=Column(String, nullable=False))
    pincode: str = Field(sa_column=Column(String, nullable=False))
    
    status: KYCStatus = Field(default=KYCStatus.PENDING, sa_column=Column(String, nullable=False))
    remarks: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship to User
    user: "User" = Relationship(back_populates="kyc_details")

    class Config:
        arbitrary_types_allowed = True
