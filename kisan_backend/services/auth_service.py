import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Set
from loguru import logger
from kisan_backend.core.config import settings
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.constants import SessionConfig
from kisan_backend.core.exceptions import AuthException
from fastapi import status
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.repositories.fcm_token_repository import FCMTokenRepository
from kisan_backend.schemas.auth import ChannelType, SendOTPResponse, DeviceMetadata
from kisan_backend.models.user import User, UserRole

from .otp_service import OTPService
from .token_service import TokenService
from .session_service import SessionService
from kisan_backend.core.ws_manager import manager
from kisan_backend.core.permissions import get_role_permissions, Permission

class AuthService:
    """Orchestrates authentication flows by delegating to specialized services."""

    def __init__(
        self, 
        user_repo: UserRepository, 
        fcm_repo: FCMTokenRepository,
        otp_service: OTPService,
        token_service: TokenService,
        session_service: SessionService
    ):
        self.user_repo = user_repo
        self.fcm_repo = fcm_repo
        self.otp_service = otp_service
        self.token_service = token_service
        self.session_service = session_service

    async def send_otp(self, phone_number: str, channel: ChannelType = ChannelType.SMS) -> SendOTPResponse:
        """Generates and sends an OTP via the OTPService."""
        return await self.otp_service.generate_and_send(phone_number, channel)

    async def verify_otp(
        self, 
        phone_number: str, 
        otp: str, 
        clear_state: bool = True,
        auto_create: bool = False
    ) -> Tuple[User, bool]:
        """Verifies OTP and prepares/retrieves the user object."""
        logger.debug(f"[AUTH] Verifying OTP for {phone_number}...")
        is_valid = await self.otp_service.verify_otp(phone_number, otp, clear_state=clear_state)
        
        if not is_valid:
            logger.error(f"[AUTH] OTP verification failed for {phone_number}: Invalid code provided.")
            raise AuthException(ResponseMessages.INVALID_OTP)

        user = await self.user_repo.get_by_phone(phone_number)
        is_new = False

        # If user doesn't exist and auto_create is true, create a new FARMER user.
        if not user:
            if auto_create:
                logger.info(f"[AUTH] Creating new user for {phone_number}")
                user = await self.user_repo.create({
                    "phone_number": phone_number,
                    "role": UserRole.FARMER,
                    "is_active": True
                })
                is_new = True
            else:
                logger.warning(f"[AUTH] Login attempt for unknown phone: {phone_number}")
                raise AuthException(
                    ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Check if profile exists without triggering lazy load if possible, 
            # or rely on the fact that for existing users we usually want to check if they have a profile.
            # In this project, get_by_phone uses selectinload(User.profile), so it should be loaded.
            # However, if it's None, it's None. The MissingGreenlet happened because it wasn't loaded.
            try:
                is_new = user.profile is None
            except Exception:
                # Fallback if lazy loading fails
                is_new = False 

        logger.success(f"[AUTH] OTP verified successfully for user {user.id} ({phone_number})")
        return user, is_new

    def get_user_permissions(self, user: User) -> Set[Permission]:
        """Fetch granular permissions for a user based on their role."""
        return get_role_permissions(user.role)


    async def create_tokens(
        self, 
        user_id: str, 
        device_meta: DeviceMetadata,
        session_id: Optional[str] = None
    ) -> dict:
        """Creates a session and returns a fresh pair of tokens."""
        user_uuid = uuid.UUID(user_id)
        
        # 1. Initialize or refresh session state
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthException(ResponseMessages.USER_NOT_FOUND)
            
        is_admin = user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

        if not session_id:
            # Enforce single device login for Admins as requested
            session_id = await self.session_service.init_session(
                user_uuid, 
                device_meta, 
                force_single_device=is_admin
            )
            # Notify other devices/tabs to log out immediately if it's an admin
            if is_admin:
                await manager.broadcast_to_user(user_id, {
                    "event": "security",
                    "type": "session_revoked",
                    "data": { 
                        "reason": "Security Alert: Access detected from a new device/browser.",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                })

        # 2. Determine token durations
        if is_admin:
            refresh_delta = timedelta(hours=SessionConfig.ADMIN_REFRESH_HOURS)
            ttl = SessionConfig.ADMIN_REFRESH_TTL_SECONDS
        else:
            refresh_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * SessionConfig.ADMIN_REFRESH_TTL_SECONDS

        # 3. Generate tokens
        access_token = self.token_service.create_access_token(user_id, session_id)
        refresh_token = self.token_service.create_refresh_token(user_id, session_id, expires_delta=refresh_delta)

        # 4. Activate in Redis Cache (MetaStore)
        await self.session_service.activate_session(user_id, session_id, device_meta, ttl)

        now_utc = datetime.now(timezone.utc)
        access_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        access_token_expire_at = now_utc + access_delta
        refresh_token_expire_at = now_utc + refresh_delta

        # 5. Fetch Permissions for Response
        permissions = self.get_user_permissions(user)

        return {
            "user_id": user_id,
            "role": user.role,
            "permissions": [p.value for p in permissions],
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_token_expire_at": access_token_expire_at.isoformat().replace("+00:00", "Z"),
            "refresh_token_expire_at": refresh_token_expire_at.isoformat().replace("+00:00", "Z"),
            "session_id": session_id,
            "token_issued_at": now_utc.isoformat().replace("+00:00", "Z")
        }

    async def verify_refresh_token(self, token: str) -> Tuple[str, str]:
        """Strict verification of a refresh token and its corresponding session."""
        payload = self.token_service.decode_token(token, verify_exp=False)
        
        if payload.get("type") != "refresh":
            raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        exp_timestamp = payload.get("exp")

        if not user_id or not session_id or not exp_timestamp:
            raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

        curr_timestamp = datetime.now(timezone.utc).timestamp()
        if curr_timestamp >= exp_timestamp:
             raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

        # Check live state in Redis
        active = await self.session_service.is_session_active(user_id, session_id)
        if not active:
            raise AuthException(ResponseMessages.INVALID_REFRESH_TOKEN)

        return user_id, session_id

    async def verify_access_token(self, token: str) -> Tuple[str, str]:
        """Strict verification of an access token and its corresponding session."""
        payload = self.token_service.decode_token(token, verify_exp=True)
        
        if payload.get("type") != "access":
            raise AuthException(ResponseMessages.INVALID_TOKEN)

        user_id = payload.get("sub")
        session_id = payload.get("sid")

        if not user_id or not session_id:
            raise AuthException(ResponseMessages.INVALID_TOKEN)

        # Check live state in Redis
        active = await self.session_service.is_session_active(user_id, session_id)
        if not active:
            raise AuthException(ResponseMessages.INVALID_TOKEN)

        return user_id, session_id

    async def invalidate_session(self, user_id: str, session_id: str):
        """Standardized logout flow."""
        await self.session_service.invalidate_session(user_id, session_id)

    async def update_fcm_token(self, user_id: uuid.UUID, device_id: str, fcm_token: str):
        """Updates the user's FCM token in the database for the specific device."""
        await self.fcm_repo.upsert(user_id, device_id, fcm_token)
