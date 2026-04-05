import hashlib
import hmac
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import jwt, JWTError
from redis.asyncio import Redis

from kisan_backend.core.config import settings
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.exceptions import AuthException
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.services.sms_service import SMSProvider
from kisan_backend.schemas.auth import ChannelType, SendOTPResponse
from kisan_backend.models.user import User, UserRole

class AuthService:
    """Service for handling user authentication, OTP generation, and token management."""

    def __init__(self, user_repo: UserRepository, redis: Redis, sms: SMSProvider):
        self.user_repo = user_repo
        self.redis = redis
        self.sms = sms

    def _hash_otp(self, otp: str) -> str:
        """Create a SHA-256 hash of an OTP using the secret key as HMAC key."""
        return hmac.new(
            settings.SECRET_KEY.encode(),
            otp.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_otp_hash(self, otp: str, stored_hash: str) -> bool:
        """Verify an OTP against its stored hash using a constant-time comparison."""
        expected = self._hash_otp(otp)
        return hmac.compare_digest(expected, stored_hash)

    async def send_otp(self, phone_number: str, channel: ChannelType = ChannelType.SMS) -> SendOTPResponse:
        """
        Generate, store, and send an OTP to a user.
        Tracks retry attempts and calculates exponential backoff.
        """
        # 1. (Removed mock bypass to enforce rate-limiting on test numbers)

        # 2. Check retry attempts
        attempts_key = f"otp_attempts:{phone_number}"
        attempts_str = await self.redis.get(attempts_key)
        attempts = int(attempts_str) if attempts_str else 0

        if attempts >= 5:
            # Re-set expiry to 24 hours to ensure the block sticks if they keep trying
            await self.redis.expire(attempts_key, 86400)
            raise AuthException(ResponseMessages.MAX_RETRIES_REACHED)

        # 3. Generate OTP
        otp = str(random.randint(100000, 999999))
        hashed_otp = self._hash_otp(otp)

        # 4. Store OTP in Redis
        otp_key = f"otp:{phone_number}"
        await self.redis.set(otp_key, hashed_otp, ex=settings.OTP_EXPIRY_SECONDS)

        # 5. Increment attempts and set 24h TTL
        new_attempts = attempts + 1
        await self.redis.set(attempts_key, str(new_attempts), ex=86400)

        # 6. Calculate next wait time (30, 60, 120, 240, 86400)
        if new_attempts == 1:
            next_wait = 30
        elif new_attempts == 2:
            next_wait = 60
        elif new_attempts == 3:
            next_wait = 120
        elif new_attempts == 4:
            next_wait = 240
        else:
            next_wait = 86400  # 24 hours block

        # 6. Send message via chosen channel
        prefix = "<#> "
        message = f"{prefix}Your Kisan app login OTP is {otp}."
        
        if settings.ANDROID_APP_HASH and channel == ChannelType.SMS:
            message = f"{message} {settings.ANDROID_APP_HASH}"

        try:
            # Skip actual SMS delivery for the mock test account
            if phone_number not in {"+911111111111", "+91 1111111111"}:
                sent = await self.sms.send_sms(phone_number, message, channel=channel)
                if not sent:
                    raise AuthException(ResponseMessages.INTERNAL_SERVER_ERROR)
        except Exception as e:
            if isinstance(e, AuthException):
                raise e
            raise AuthException(f"SMS service error: {str(e)}")

        accepts_at = datetime.now(timezone.utc) + timedelta(seconds=next_wait)

        return SendOTPResponse(
            phone_number=phone_number,
            remaining_attempts=5 - new_attempts,
            resend_accepts_at=accepts_at.isoformat().replace("+00:00", "Z")
        )

    async def verify_otp(self, phone_number: str, otp: str) -> Tuple[User, bool]:
        """
        Verify an OTP and return the User.
        Creates a new user if they don't exist.
        """
        otp_key = f"otp:{phone_number}"

        if phone_number in {"+911111111111", "+91 1111111111"}:
            if otp != "222222":
                raise AuthException(ResponseMessages.INVALID_OTP)
        else:
            stored_hash = await self.redis.get(otp_key)
            if not stored_hash:
                raise AuthException(ResponseMessages.OTP_EXPPIRED)

            if not self._verify_otp_hash(otp, stored_hash):
                raise AuthException(ResponseMessages.INVALID_OTP)

        # Success — clear OTP and attempts from Redis
        await self.redis.delete(otp_key)
        await self.redis.delete(f"otp_attempts:{phone_number}")

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

    async def create_tokens(self, user_id: str, session_id: Optional[str] = None) -> dict:
        """
        Create a pair of access and refresh tokens for a user ID.
        If session_id is not provided, a new one is generated.
        The session is stored in Redis to allow for invalidation.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        now_utc = datetime.now(timezone.utc)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        access_expire_at = now_utc + access_token_expires
        refresh_expire_at = now_utc + refresh_token_expires

        # Store session in Redis
        session_key = f"session:{user_id}:{session_id}"
        await self.redis.set(
            session_key,
            "active",
            ex=int(refresh_token_expires.total_seconds())
        )

        access_token = self._create_token(
            {"sub": user_id, "type": "access", "sid": session_id},
            access_token_expires
        )
        refresh_token = self._create_token(
            {"sub": user_id, "type": "refresh", "sid": session_id},
            refresh_token_expires
        )

        return {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_token_expire_at": access_expire_at.isoformat().replace("+00:00", "Z"),
            "refresh_token_expire_at": refresh_expire_at.isoformat().replace("+00:00", "Z"),
            "token_issued_at": now_utc.isoformat().replace("+00:00", "Z"),
            "session_id": session_id
        }

    def _create_token(self, data: dict, expires_delta: timedelta) -> str:
        """Internal helper for JWT encoding."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    async def verify_refresh_token(self, token: str) -> Tuple[str, str]:
        """Verify a refresh token and check if its session is still active."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "refresh":
                raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

            user_id = payload.get("sub")
            session_id = payload.get("sid")

            if not user_id or not session_id:
                raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

            # Check session in Redis
            session_key = f"session:{user_id}:{session_id}"
            if not await self.redis.get(session_key):
                raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

            return user_id, session_id
        except JWTError:
            raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

    async def invalidate_session(self, user_id: str, session_id: str):
        """Delete a session from Redis to invalidate all associated tokens."""
        session_key = f"session:{user_id}:{session_id}"
        await self.redis.delete(session_key)
