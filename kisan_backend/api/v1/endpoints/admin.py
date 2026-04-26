import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from kisan_backend.api.v1.dependencies.auth_deps import PermissionChecker
from kisan_backend.core.permissions import Permission
from kisan_backend.models.user import User, UserRole
from kisan_backend.schemas.admin import (
    AdminDashboardStats, 
    KYCVerifyRequest, 
    BulkKYCVerifyRequest,
    AdminUserListResponse,
    AdminFarmerResponse
)
from kisan_backend.schemas.user import UserResponse
from kisan_backend.schemas.kyc import KYCSubmissionResponse
from kisan_backend.schemas.auth import DeviceMetadata
from kisan_backend.services.admin_service import AdminService
from kisan_backend.services.storage_service import storage_service
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
@router.get("/stats", response_model=ApiResponse[AdminDashboardStats])
async def get_stats(
    admin_user: Annotated[User, Depends(PermissionChecker(Permission.STATS_VIEW))],
    admin_service: AdminServiceDep
):
    """Fetches high-level metrics for the dashboard overview."""
    stats = await admin_service.get_dashboard_stats()
    return SuccessResponse(message="Stats fetched", data=stats)

@router.get("/users", response_model=ApiResponse[AdminUserListResponse])
async def list_users(
    admin_user: Annotated[User, Depends(PermissionChecker(Permission.USERS_VIEW))],
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
    mapped_users = []
    for u in users:
        is_new = u.profile is None
        sessions = getattr(u, "sessions", [])
        last_login_at = max([s.last_login_at for s in sessions if s.last_login_at]) if sessions and any(s.last_login_at for s in sessions) else None
        active_sessions = [
            DeviceMetadata(
                device_id=s.device_id,
                brand=s.brand,
                model=s.model,
                os_name=s.os_name,
                os_version=s.os_version,
                app_version=s.app_version,
                ip_address=s.ip_address
            )
            for s in sessions if s.is_active
        ]
        
        user_resp = UserResponse.from_user(u)
        admin_resp = AdminFarmerResponse(
            **user_resp.model_dump(),
            is_new=is_new,
            last_login_at=last_login_at,
            active_sessions=active_sessions
        )
        mapped_users.append(admin_resp)

    return SuccessResponse(
        message="Users fetched",
        data={
            "users": mapped_users,
            "total": total,
            "page": page,
            "size": size
        }
    )

@router.get("/kyc/pending", response_model=ApiResponse[List[KYCSubmissionResponse]])
async def list_pending_kyc(
    admin_user: Annotated[User, Depends(PermissionChecker(Permission.KYC_VIEW))],
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
        
        # FIX: Generate presigned URLs for private storage
        resp.front_image_url = await storage_service.get_view_url(k.front_image_url)
        resp.back_image_url = await storage_service.get_view_url(k.back_image_url)
        
        data.append(resp)
        
    return SuccessResponse(
        message="Pending KYCs fetched",
        data=data
    )

@router.post("/kyc/bulk-verify", response_model=ApiResponse[List[KYCSubmissionResponse]])
async def bulk_verify_kyc(
    verify_data: BulkKYCVerifyRequest,
    admin_user: Annotated[User, Depends(PermissionChecker(Permission.KYC_APPROVE))],
    admin_service: AdminServiceDep
):
    """Approve or Reject multiple KYC submissions in one go."""
    results = await admin_service.bulk_verify_kyc(
        user_ids=verify_data.user_ids,
        approved=verify_data.approved,
        remarks=verify_data.remarks
    )
    # Fix image URLs in bulk results
    data = []
    for r in results:
        resp = KYCSubmissionResponse.model_validate(r)
        resp.front_image_url = await storage_service.get_view_url(r.front_image_url)
        resp.back_image_url = await storage_service.get_view_url(r.back_image_url)
        data.append(resp)

    return SuccessResponse(
        message=f"Processed {len(results)} KYC requests",
        data=data
    )

@router.post("/kyc/{user_id}/verify", response_model=ApiResponse[KYCSubmissionResponse])
async def verify_kyc(
    user_id: uuid.UUID,
    verify_data: KYCVerifyRequest,
    admin_user: Annotated[User, Depends(PermissionChecker(Permission.KYC_APPROVE))],
    admin_service: AdminServiceDep
):
    """Approve or Reject a user's KYC submission."""
    try:
        kyc = await admin_service.verify_kyc(
            user_id=user_id,
            approved=verify_data.approved,
            remarks=verify_data.remarks
        )
        resp = KYCSubmissionResponse.model_validate(kyc)
        resp.front_image_url = await storage_service.get_view_url(kyc.front_image_url)
        resp.back_image_url = await storage_service.get_view_url(kyc.back_image_url)

        return SuccessResponse(
            message="KYC status updated successfully",
            data=resp
        )
    except ValueError as e:
        from kisan_backend.core.exceptions import NotFoundException
        raise NotFoundException(str(e))
