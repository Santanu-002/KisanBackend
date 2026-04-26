from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from kisan_backend.models.kyc import KYCStatus

class KYCBase(BaseModel):
    document_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district: str
    landmark: Optional[str] = None
    city: str
    state: str
    pincode: str

class KYCSubmissionResponse(KYCBase):
    id: UUID
    user_id: UUID
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    front_image_url: str
    back_image_url: str
    status: KYCStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class KYCStatusUpdate(BaseModel):
    status: KYCStatus
    remarks: Optional[str] = None
