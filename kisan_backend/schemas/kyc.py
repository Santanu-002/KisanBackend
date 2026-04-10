from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from kisan_backend.models.kyc import KYCStatus

class KYCBase(BaseModel):
    document_type: str
    id_number: Optional[str] = None
    latitude: float
    longitude: float
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str

class KYCSubmissionResponse(KYCBase):
    id: UUID
    user_id: UUID
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
