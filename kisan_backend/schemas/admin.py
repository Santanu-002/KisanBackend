from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from kisan_backend.schemas.user import UserResponse
from kisan_backend.schemas.kyc import KYCSubmissionResponse

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

class AdminUserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    size: int
