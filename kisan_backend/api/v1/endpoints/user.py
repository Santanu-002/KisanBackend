from typing import Annotated, Optional
from fastapi import APIRouter, Depends, status, Form, File, UploadFile
from kisan_backend.api.v1.dependencies.auth_deps import get_current_user, PermissionChecker
from kisan_backend.core.permissions import Permission
from kisan_backend.models.user import User
from kisan_backend.schemas.user import UserResponse, UserUpdate, AvatarUploadUrlResponse, PredefinedAvatarResponse
from kisan_backend.services.user_service import UserService
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.responses import SuccessResponse, ApiResponse

router = APIRouter(prefix="/users", tags=["Users"])

from kisan_backend.services.storage_service import storage_service

async def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserService:
    user_repo = UserRepository(db)
    return UserService(user_repo, storage_service)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]

@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_my_profile(
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_VIEW))]
):
    return SuccessResponse(
        message=ResponseMessages.PROFILE_FETCHED,
        data=UserResponse.from_user(current_user)
    )

@router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_my_profile(
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_EDIT))],
    user_service: UserServiceDep,
    full_name: Annotated[Optional[str], Form()] = None,
    email: Annotated[Optional[str], Form()] = None,
    gender: Annotated[Optional[str], Form()] = None,
    avatar_url: Annotated[Optional[str], Form()] = None,
    avatar_file: Annotated[Optional[UploadFile], File()] = None,
):
    update_data = UserUpdate(
        full_name=full_name,
        email=email,
        gender=gender,
        avatar_url=avatar_url
    )
    user = await user_service.update_profile(
        str(current_user.id), 
        update_data, 
        avatar_file=avatar_file
    )
    return SuccessResponse(
        message=ResponseMessages.PROFILE_UPDATED,
        data=UserResponse.from_user(user)
    )


@router.post("/profile", response_model=ApiResponse[UserResponse])
async def create_profile(
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_EDIT))],
    user_service: UserServiceDep,
    full_name: Annotated[str, Form()],
    email: Annotated[Optional[str], Form()] = None,
    gender: Annotated[Optional[str], Form()] = None,
    avatar_url: Annotated[Optional[str], Form()] = None,
    avatar_file: Annotated[Optional[UploadFile], File()] = None,
):
    user = await user_service.create_profile(
        user_id=str(current_user.id),
        full_name=full_name,
        email=email,
        gender=gender,
        avatar_url=avatar_url,
        avatar_file=avatar_file
    )
    return SuccessResponse(
        message=ResponseMessages.PROFILE_CREATED,
        data=UserResponse.from_user(user)
    )


@router.get("/kyc-upload-url", response_model=ApiResponse[AvatarUploadUrlResponse])
async def get_kyc_upload_url(
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_EDIT))],
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
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_EDIT))],
    user_service: UserServiceDep,
):
    user = await user_service.submit_kyc(str(current_user.id))
    return SuccessResponse(
        message=ResponseMessages.KYC_SUBMITTED,
        data=UserResponse.from_user(user)
    )

@router.get("/predefined-avatars", response_model=ApiResponse[PredefinedAvatarResponse])
async def get_predefined_avatars(
    current_user: Annotated[User, Depends(PermissionChecker(Permission.PROFILE_VIEW))],
    user_service: UserServiceDep
):
    avatars = await user_service.get_predefined_avatars()
    return SuccessResponse(
        message="Predefined avatars fetched successfully",
        data={"avatars": avatars}
    )
