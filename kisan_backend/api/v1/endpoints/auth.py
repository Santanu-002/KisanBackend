from typing import Annotated
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from kisan_backend.db.session import get_db
from kisan_backend.db.redis import get_redis
from kisan_backend.schemas.auth import (
    SendOTPRequest, VerifyOTPRequest, TokenResponse, 
    RefreshTokenRequest, DeviceMetadata
)
from kisan_backend.core.responses import SuccessResponse, ApiResponse
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.services.auth_service import AuthService
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.repositories.user_session_repository import UserSessionRepository
from kisan_backend.services.sms_service import get_sms_provider
from fastapi import Request

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_device_meta(request: Request) -> DeviceMetadata:
    """Helper to extract device metadata from mandatory headers."""
    return DeviceMetadata(
        device_id=request.headers.get("X-Device-Id", "unknown"),
        brand=request.headers.get("X-Device-Brand", "unknown"),
        model=request.headers.get("X-Device-Model", "unknown"),
        os_name=request.headers.get("X-Device-OS", "unknown"),
        os_version=request.headers.get("X-Device-OS-Version", "unknown"),
        app_version=request.headers.get("X-App-Version", "unknown"),
        ip_address=request.client.host if request.client else None
    )

async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)]
) -> AuthService:
    """Factory dependency to inject AuthService with its required repositories and providers."""
    user_repo = UserRepository(db)
    user_session_repo = UserSessionRepository(db)
    sms_provider = get_sms_provider()
    return AuthService(user_repo, user_session_repo, redis, sms_provider)

# Type alias for AuthService dependency
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

@router.post("/send-otp")
async def send_otp(
    request: SendOTPRequest,
    auth_service: AuthServiceDep
):
    otp_response = await auth_service.send_otp(request.phone_number, channel=request.channel)
    
    # Format channel name clearly (SMS/WHATSAPP)
    channel_name = request.channel.value.upper() if hasattr(request.channel, 'value') else str(request.channel).upper()
    
    return SuccessResponse(
        message=ResponseMessages.OTP_SENT.format(channel=channel_name),
        data=otp_response
    )

@router.post("/verify-otp")
async def verify_otp(
    request: Request,
    verify_req: VerifyOTPRequest,
    response: Response,
    auth_service: AuthServiceDep
):
    user, is_new = await auth_service.verify_otp(verify_req.phone_number, verify_req.otp)
    
    # Extract metadata from headers
    device_meta = get_device_meta(request)
    
    tokens = await auth_service.create_tokens(str(user.id), device_meta=device_meta)
    
    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    
    return SuccessResponse(
        message=ResponseMessages.OTP_VERIFIED,
        data={
            "user_id": user.id,
            "is_new_user": is_new,
            "is_kyc_completed": user.is_kyc_completed,
            "is_verified": user.is_verified,
            **tokens
        }
    )

@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_req: RefreshTokenRequest,
    auth_service: AuthServiceDep
):
    user_id, session_id = await auth_service.verify_refresh_token(refresh_req.refresh_token)
    
    # Extract metadata from headers
    device_meta = get_device_meta(request)
    
    tokens = await auth_service.create_tokens(user_id, device_meta=device_meta, session_id=session_id)
    
    return SuccessResponse(
        message=ResponseMessages.TOKEN_REFRESHED,
        data=tokens
    )

@router.post("/logout")
async def logout(
    request: Request,
    logout_req: RefreshTokenRequest,
    auth_service: AuthServiceDep
):
    user_id, session_id = await auth_service.verify_refresh_token(logout_req.refresh_token)
    await auth_service.invalidate_session(user_id, session_id)
    return SuccessResponse(
        message=ResponseMessages.LOGOUT_SUCCESS,
        data=None
    )

