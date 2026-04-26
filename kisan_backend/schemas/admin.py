from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from kisan_backend.schemas.user import UserResponse
from kisan_backend.schemas.kyc import KYCSubmissionResponse
from kisan_backend.schemas.auth import DeviceMetadata

class AdminDashboardStats(BaseModel):
    total_farmers: int
    pending_kyc_count: int
    active_plots: int

class KYCVerifyRequest(BaseModel):
    approved: bool
    remarks: Optional[str] = None

class BulkKYCVerifyRequest(BaseModel):
    user_ids: List[UUID]
    approved: bool
    remarks: Optional[str] = None

class AdminFarmerResponse(UserResponse):
    is_new: bool
    last_login_at: Optional[datetime] = None
    active_sessions: List[DeviceMetadata] = []

class AdminUserListResponse(BaseModel):
    users: List[AdminFarmerResponse]
    total: int
    page: int
    size: int
