from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import uuid

from kisan_backend.db.session import get_db
from kisan_backend.db.redis import get_redis
from kisan_backend.schemas.auth import SendOTPRequest, VerifyOTPRequest, TokenResponse, RefreshTokenRequest
from kisan_backend.schemas.response import SuccessResponse
from kisan_backend.services.auth_service import AuthService
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.services.sms_service import get_sms_provider

router = APIRouter(prefix="/auth", tags=["Authentication"])

async def get_auth_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> AuthService:
    user_repo = UserRepository(db)
    sms_provider = get_sms_provider()
    return AuthService(user_repo, redis, sms_provider)

@router.post("/send-otp", response_model=SuccessResponse)
async def send_otp(
    request: SendOTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    await auth_service.send_otp(request.phone_number)
    return SuccessResponse(data={"message": "OTP sent successfully"})

@router.post("/verify-otp", response_model=SuccessResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    user, is_new = await auth_service.verify_otp(request.phone_number, request.otp)
    tokens = auth_service.create_tokens(str(user.id))
    
    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    
    return SuccessResponse(data={
        "user_id": user.id,
        "is_new_user": is_new,
        **tokens
    })

@router.post("/refresh-token", response_model=SuccessResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    user_id = auth_service.verify_refresh_token(request.refresh_token)
    tokens = auth_service.create_tokens(user_id)
    
    return SuccessResponse(data=tokens)
