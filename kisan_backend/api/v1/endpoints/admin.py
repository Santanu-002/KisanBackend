import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kisan_backend.core.security import get_current_admin
from kisan_backend.models.user import User, UserRole
from kisan_backend.schemas.admin import (
    AdminDashboardStats, 
    KYCVerifyRequest, 
    BulkKYCVerifyRequest,
    AdminUserListResponse
)
from kisan_backend.schemas.user import UserResponse
from kisan_backend.schemas.kyc import KYCSubmissionResponse
from kisan_backend.services.admin_service import AdminService
from kisan_backend.repositories.admin_repository import AdminRepository
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.repositories.kyc_repository import KYCRepository
from kisan_backend.db.session import get_db
from kisan_backend.core.responses import SuccessResponse, ApiResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

async def get_admin_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AdminService:
    admin_repo = AdminRepository(db)
    user_repo = UserRepository(db)
    kyc_repo = KYCRepository(db)
    return AdminService(admin_repo, user_repo, kyc_repo)

AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
AdminUserDep = Annotated[User, Depends(get_current_admin)]

@router.get("/stats", response_model=ApiResponse[AdminDashboardStats])
async def get_stats(
    admin_user: AdminUserDep,
    admin_service: AdminServiceDep
):
    """Fetches high-level metrics for the dashboard overview."""
    stats = await admin_service.get_dashboard_stats()
    return SuccessResponse(message="Stats fetched", data=stats)

@router.get("/users", response_model=ApiResponse[AdminUserListResponse])
async def list_users(
    admin_user: AdminUserDep,
    admin_service: AdminServiceDep,
    page: int = 1,
    size: int = 20,
    search: Optional[str] = None
):
    """Lists field users with pagination and search."""
    users, total = await admin_service.get_users_paged(
        page=page, 
        size=size, 
        search=search, 
        role=UserRole.FARMER
    )
    return SuccessResponse(
        message="Users fetched",
        data={
            "users": [UserResponse.from_user(u) for u in users],
            "total": total,
            "page": page,
            "size": size
        }
    )

@router.get("/kyc/pending", response_model=ApiResponse[List[KYCSubmissionResponse]])
async def list_pending_kyc(
    admin_user: AdminUserDep,
    admin_service: AdminServiceDep
):
    """Lists all users awaiting KYC verification."""
    pending = await admin_service.get_pending_kycs()
    
    # Manually map joined data for the response
    data = []
    for k in pending:
        resp = KYCSubmissionResponse.model_validate(k)
        # Populate enriched fields from joined relationships
        resp.full_name = k.user.profile.full_name if k.user and k.user.profile else "N/A"
        resp.phone_number = k.user.phone_number if k.user else "N/A"
        data.append(resp)
        
    return SuccessResponse(
        message="Pending KYCs fetched",
        data=data
    )

@router.post("/kyc/bulk-verify", response_model=ApiResponse[List[KYCSubmissionResponse]])
async def bulk_verify_kyc(
    verify_data: BulkKYCVerifyRequest,
    admin_user: AdminUserDep,
    admin_service: AdminServiceDep
):
    """Approve or Reject multiple KYC submissions in one go."""
    results = await admin_service.bulk_verify_kyc(
        user_ids=verify_data.user_ids,
        approved=verify_data.approved,
        remarks=verify_data.remarks
    )
    return SuccessResponse(
        message=f"Processed {len(results)} KYC requests",
        data=[KYCSubmissionResponse.model_validate(r) for r in results]
    )

@router.post("/kyc/{user_id}/verify", response_model=ApiResponse[KYCSubmissionResponse])
async def verify_kyc(
    user_id: uuid.UUID,
    verify_data: KYCVerifyRequest,
    admin_user: AdminUserDep,
    admin_service: AdminServiceDep
):
    """Approve or Reject a user's KYC submission."""
    try:
        kyc = await admin_service.verify_kyc(
            user_id=user_id,
            approved=verify_data.approved,
            remarks=verify_data.remarks
        )
        return SuccessResponse(
            message="KYC status updated successfully",
            data=KYCSubmissionResponse.model_validate(kyc)
        )
    except ValueError as e:
        from kisan_backend.core.exceptions import NotFoundException
        raise NotFoundException(str(e))
