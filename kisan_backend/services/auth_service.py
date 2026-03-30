import random
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
from passlib.context import CryptContext
from redis.asyncio import Redis

from kisan_backend.core.config import settings
from kisan_backend.core.exceptions import AuthException, ErrorCode
from kisan_backend.models.user import User, UserRole
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.services.sms_service import SMSProvider

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, user_repo: UserRepository, redis: Redis, sms: SMSProvider):
        self.user_repo = user_repo
        self.redis = redis
        self.sms = sms

    def _hash_otp(self, otp: str) -> str:
        return pwd_context.hash(otp)

    def _verify_otp_hash(self, otp: str, hashed_otp: str) -> bool:
        return pwd_context.verify(otp, hashed_otp)

    async def send_otp(self, phone_number: str):
        # 1. Rate Limit Check
        rate_limit_key = f"otp_limit:{phone_number}"
        requests = await self.redis.get(rate_limit_key)
        if requests and int(requests) >= settings.OTP_RATE_LIMIT_REQUESTS:
            raise AuthException(ErrorCode.AUTH_003, "Too many OTP requests. Please try again later.")
        
        # 2. Generate OTP
        otp = str(random.randint(100000, 999999))
        hashed_otp = self._hash_otp(otp)
        
        # 3. Store in Redis
        otp_key = f"otp:{phone_number}"
        await self.redis.set(otp_key, hashed_otp, ex=settings.OTP_EXPIRY_SECONDS)
        await self.redis.set(f"otp_attempts:{phone_number}", 0, ex=settings.OTP_EXPIRY_SECONDS)
        
        # 4. Increment Rate Limit
        if not requests:
            await self.redis.set(rate_limit_key, 1, ex=settings.OTP_RATE_LIMIT_WINDOW_SECONDS)
        else:
            await self.redis.incr(rate_limit_key)

        # 5. Send SMS
        message = f"Your Kisan app login OTP is {otp}. Valid for 5 minutes."
        await self.sms.send_sms(phone_number, message)
        return True

    async def verify_otp(self, phone_number: str, otp: str) -> Tuple[User, bool]:
        otp_key = f"otp:{phone_number}"
        attempts_key = f"otp_attempts:{phone_number}"
        
        hashed_otp = await self.redis.get(otp_key)
        if not hashed_otp:
            raise AuthException(ErrorCode.AUTH_002, "OTP expired")
        
        attempts = await self.redis.get(attempts_key)
        if attempts and int(attempts) >= settings.OTP_MAX_ATTEMPTS:
            await self.redis.delete(otp_key)
            raise AuthException(ErrorCode.AUTH_003, "Too many failed attempts")
        
        if not self._verify_otp_hash(otp, hashed_otp):
            await self.redis.incr(attempts_key)
            raise AuthException(ErrorCode.AUTH_001, "Invalid OTP")
        
        # Success - Clear Redis
        await self.redis.delete(otp_key)
        await self.redis.delete(attempts_key)
        
        # Get or Create User
        user = await self.user_repo.get_by_phone(phone_number)
        is_new = False
        if not user:
            user = await self.user_repo.create({
                "phone_number": phone_number,
                "role": UserRole.FARMER,
                "is_active": True
            })
            is_new = True
        else:
            await self.user_repo.update_last_login(user)
            
        return user, is_new

    def create_tokens(self, user_id: str) -> dict:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = self._create_token({"sub": user_id, "type": "access"}, access_token_expires)
        refresh_token = self._create_token({"sub": user_id, "type": "refresh"}, refresh_token_expires)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        }

    def _create_token(self, data: dict, expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_refresh_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "refresh":
                raise AuthException(ErrorCode.AUTH_001, "Invalid token type")
            user_id = payload.get("sub")
            if not user_id:
                raise AuthException(ErrorCode.AUTH_001, "Invalid token")
            return user_id
        except JWTError:
            raise AuthException(ErrorCode.AUTH_001, "Invalid refresh token")
