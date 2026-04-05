from typing import Annotated
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from kisan_backend.db.session import get_db
from kisan_backend.db.redis import get_redis
from kisan_backend.schemas.auth import SendOTPRequest, VerifyOTPRequest, TokenResponse, RefreshTokenRequest
from kisan_backend.core.responses import SuccessResponse, ApiResponse
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.services.auth_service import AuthService
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.services.sms_service import get_sms_provider

router = APIRouter(prefix="/auth", tags=["Authentication"])

async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)]
) -> AuthService:
    """Factory dependency to inject AuthService with its required repositories and providers."""
    user_repo = UserRepository(db)
    sms_provider = get_sms_provider()
    return AuthService(user_repo, redis, sms_provider)

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
    request: VerifyOTPRequest,
    response: Response,
    auth_service: AuthServiceDep
):
    user, is_new = await auth_service.verify_otp(request.phone_number, request.otp)
    tokens = await auth_service.create_tokens(str(user.id))
    
    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    
    return SuccessResponse(
        message=ResponseMessages.OTP_VERIFIED,
        data={
            "user_id": user.id,
            "is_new_user": is_new,
            **tokens
        }
    )

@router.post("/refresh-token")
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthServiceDep
):
    user_id, session_id = await auth_service.verify_refresh_token(request.refresh_token)
    tokens = await auth_service.create_tokens(user_id, session_id=session_id)
    
    return SuccessResponse(
        message=ResponseMessages.TOKEN_REFRESHED,
        data=tokens
    )

@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    auth_service: AuthServiceDep
):
    user_id, session_id = await auth_service.verify_refresh_token(request.refresh_token)
    await auth_service.invalidate_session(user_id, session_id)
    return SuccessResponse(
        message=ResponseMessages.LOGOUT_SUCCESS,
        data=None
    )

