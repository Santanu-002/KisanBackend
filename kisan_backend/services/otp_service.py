import hashlib
import hmac
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from redis.asyncio import Redis

from loguru import logger
from kisan_backend.core.config import settings
from kisan_backend.core.constants import OTPConfig
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.exceptions import AuthException, RateLimitException
from kisan_backend.schemas.auth import ChannelType, SendOTPResponse
from kisan_backend.services.sms_service import SMSProvider

class OTPService:
    """Handles OTP generation, hashing, storage, and rate limiting."""

    def __init__(self, redis: Redis, sms: SMSProvider):
        self.redis = redis
        self.sms = sms

    def _hash_otp(self, otp: str) -> str:
        """Create a SHA-256 hash of an OTP using the secret key."""
        return hmac.new(
            settings.SECRET_KEY.encode(),
            otp.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_otp_hash(self, otp: str, stored_hash: str) -> bool:
        """Verify an OTP against its stored hash using constant-time comparison."""
        expected = self._hash_otp(otp)
        return hmac.compare_digest(expected, stored_hash)

    async def generate_and_send(self, phone_number: str, channel: ChannelType) -> SendOTPResponse:
        """Generates a new OTP, applies rate limiting, and sends it."""
        # Check retry attempts
        attempts_key = f"otp_attempts:{phone_number}"
        attempts_str = await self.redis.get(attempts_key)
        attempts = int(attempts_str) if attempts_str else 0

        if attempts >= settings.OTP_MAX_ATTEMPTS:
            await self.redis.expire(attempts_key, OTPConfig.BLOCK_DURATION_SECONDS)
            raise RateLimitException(ResponseMessages.MAX_RETRIES_REACHED)

        # Generate OTP
        # Force static OTP for development as requested
        otp = OTPConfig.MOCK_CODE
        logger.info(f"[OTP] Generated static OTP {otp} for {phone_number}")
        hashed_otp = self._hash_otp(otp)

        # Store in Redis
        otp_key = f"otp:{phone_number}"
        await self.redis.set(otp_key, hashed_otp, ex=settings.OTP_EXPIRY_SECONDS)

        # Increment attempts logic
        new_attempts = attempts + 1
        await self.redis.set(attempts_key, str(new_attempts), ex=OTPConfig.BLOCK_DURATION_SECONDS)

        # Backoff timing
        next_wait = OTPConfig.BACKOFF_MAP.get(new_attempts, OTPConfig.BLOCK_DURATION_SECONDS)

        # Send via provider
        if settings.SMS_PROVIDER != "mock":
            prefix = "<#> "
            message = f"{prefix}Your Kisan app login OTP is {otp}."
            if settings.ANDROID_APP_HASH and channel == ChannelType.SMS:
                message = f"{message} {settings.ANDROID_APP_HASH}"

            sent = await self.sms.send_sms(phone_number, message, channel=channel)
            if not sent:
                raise AuthException(ResponseMessages.OTP_SEND_FAILED)


        accepts_at = datetime.now(timezone.utc) + timedelta(seconds=next_wait)
        return SendOTPResponse(
            phone_number=phone_number,
            remaining_attempts=settings.OTP_MAX_ATTEMPTS - new_attempts,
            resend_accepts_at=accepts_at.isoformat().replace("+00:00", "Z")
        )

    async def verify_otp(self, phone_number: str, otp: str, clear_state: bool = True) -> bool:
        """
        Verifies OTP and conditionally clears state on success.
        
        Args:
            phone_number: The phone number to verify.
            otp: The OTP code to check.
            clear_state: If True, deletes the OTP and attempt count from Redis upon success.
                         Defaults to True. Should be False if a follow-up request is expected.
        """
        otp_key = f"otp:{phone_number}"
        stored_hash = await self.redis.get(otp_key)
        
        if not stored_hash:
            logger.warning(f"[OTP] Verification failed for {phone_number}: OTP key not found in Redis (expired or already consumed).")
            raise AuthException(ResponseMessages.OTP_EXPIRED)

        if self._verify_otp_hash(otp, stored_hash):
            if clear_state:
                logger.info(f"[OTP] Successfully verified OTP for {phone_number}. Clearing state...")
                await self._clear_state(phone_number)
            else:
                logger.info(f"[OTP] Successfully verified OTP for {phone_number}. State preserved for follow-up.")
            return True
        
        logger.error(f"[OTP] Hash mismatch for {phone_number}. Verification failed.")
        return False

    async def _clear_state(self, phone_number: str):
        """Clears OTP and attempts from Redis."""
        await self.redis.delete(f"otp:{phone_number}")
        await self.redis.delete(f"otp_attempts:{phone_number}")
