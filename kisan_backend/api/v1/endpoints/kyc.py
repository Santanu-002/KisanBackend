from typing import Annotated
from fastapi import APIRouter, Depends, Form, File, UploadFile, status
from loguru import logger
from kisan_backend.api.v1.dependencies.auth_deps import get_current_user, PermissionChecker
from kisan_backend.core.permissions import Permission
from kisan_backend.models.user import User
from kisan_backend.schemas.kyc import KYCSubmissionResponse
from kisan_backend.services.kyc_service import KYCService
from kisan_backend.repositories.kyc_repository import KYCRepository
from kisan_backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from kisan_backend.core.responses import SuccessResponse, ErrorResponse, ApiResponse

router = APIRouter(prefix="/kyc", tags=["KYC"])

async def get_kyc_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> KYCService:
    kyc_repo = KYCRepository(db)
    return KYCService(kyc_repo)

KYCServiceDep = Annotated[KYCService, Depends(get_kyc_service)]

@router.post("/submit", response_model=ApiResponse[KYCSubmissionResponse])
async def submit_kyc(
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_EDIT))],
    kyc_service: KYCServiceDep,
    document_type: str = Form(...),
    district: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...),
    front_image: UploadFile = File(...),
    back_image: UploadFile = File(...),
    landmark: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
):
    """
    Submits KYC details including document photos.
    Uses MultiPart Form-Data to handle both text fields and files atomically.
    """
    try:
        kyc = await kyc_service.submit_kyc(
            user_id=current_user.id,
            document_type=document_type,
            district=district,
            landmark=landmark,
            city=city,
            state=state,
            pincode=pincode,
            latitude=latitude,
            longitude=longitude,
            front_image=front_image,
            back_image=back_image,
        )
        
        # Commit the transaction
        await kyc_service.kyc_repo.session.commit()
        
        return SuccessResponse(
            message="KYC details submitted successfully",
            data=KYCSubmissionResponse.model_validate(kyc)
        )
    except Exception as e:
        logger.error(f"KYC Submission API error: {str(e)}")
        return ErrorResponse(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST
        )
