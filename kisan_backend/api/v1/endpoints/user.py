from typing import Annotated
from fastapi import APIRouter, Depends, status
from kisan_backend.core.security import get_current_user
from kisan_backend.models.user import User
from kisan_backend.schemas.user import UserResponse, UserUpdate, AvatarUploadUrlResponse, PredefinedAvatarResponse
from kisan_backend.services.user_service import UserService
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.responses import SuccessResponse, ApiResponse

router = APIRouter(prefix="/users", tags=["Users"])

async def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserService:
    user_repo = UserRepository(db)
    return UserService(user_repo)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_my_profile(
    current_user: CurrentUserDep
):
    return SuccessResponse(
        message=ResponseMessages.PROFILE_FETCHED,
        data=UserResponse.from_user(current_user)
    )

@router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_my_profile(
    update_data: UserUpdate,
    current_user: CurrentUserDep,
    user_service: UserServiceDep
):
    user = await user_service.update_profile(str(current_user.id), update_data)
    return SuccessResponse(
        message=ResponseMessages.PROFILE_UPDATED,
        data=UserResponse.from_user(user)
    )

@router.get("/avatar-upload-url", response_model=ApiResponse[AvatarUploadUrlResponse])
async def get_avatar_upload_url(
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
    content_type: str = "image/jpeg"
):
    url, file_key = await user_service.get_avatar_upload_url(str(current_user.id), content_type)
    return SuccessResponse(
        message=ResponseMessages.UPLOAD_URL_GENERATED,
        data={
            "upload_url": url,
            "file_key": file_key
        }
    )

@router.get("/kyc-upload-url", response_model=ApiResponse[AvatarUploadUrlResponse])
async def get_kyc_upload_url(
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
    filename: str,
    content_type: str = "image/jpeg"
):
    url, file_key = await user_service.get_kyc_upload_url(str(current_user.id), filename, content_type)
    return SuccessResponse(
        message=ResponseMessages.UPLOAD_URL_GENERATED,
        data={
            "upload_url": url,
            "file_key": file_key
        }
    )

@router.post("/submit-kyc", response_model=ApiResponse[UserResponse])
async def submit_kyc(
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
):
    user = await user_service.submit_kyc(str(current_user.id))
    return SuccessResponse(
        message=ResponseMessages.KYC_SUBMITTED,
        data=UserResponse.from_user(user)
    )

@router.get("/predefined-avatars", response_model=ApiResponse[PredefinedAvatarResponse])
async def get_predefined_avatars(
    user_service: UserServiceDep
):
    avatars = await user_service.get_predefined_avatars()
    return SuccessResponse(
        message="Predefined avatars fetched successfully",
        data={"avatars": avatars}
    )
