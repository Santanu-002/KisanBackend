"""
auth_deps.py — Auth-specific FastAPI dependency factories.

Centralizes service construction and request parsing helpers so that
endpoint files contain only HTTP request/response shaping logic (SRP).
"""

from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from kisan_backend.db.session import get_db
from kisan_backend.db.redis import get_redis
from kisan_backend.schemas.auth import DeviceMetadata
from kisan_backend.services.auth_service import AuthService
from kisan_backend.services.otp_service import OTPService
from kisan_backend.services.token_service import TokenService
from kisan_backend.services.session_service import SessionService
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.repositories.user_session_repository import UserSessionRepository
from kisan_backend.services.sms_service import get_sms_provider


def get_device_meta(request: Request) -> DeviceMetadata:
    """Extracts device identification metadata from the request headers."""
    return DeviceMetadata(
        device_id=request.headers.get("X-Device-Id", "unknown"),
        brand=request.headers.get("X-Device-Brand", "unknown"),
        model=request.headers.get("X-Device-Model", "unknown"),
        os_name=request.headers.get("X-Device-OS", "unknown"),
        os_version=request.headers.get("X-Device-OS-Version", "unknown"),
        app_version=request.headers.get("X-App-Version", "unknown"),
        ip_address=request.client.host if request.client else None,
    )


def is_browser_request(request: Request) -> bool:
    """
    Returns True when the request originates from a web browser.

    Detection logic:
    - Native mobile apps (Flutter) send ``X-Device-Browser: N/A``.
    - Browser clients (Admin Web, any browser) either omit the header or
      supply a real browser name (e.g. ``Chrome``, ``Safari``).

    Rule summary:
        browser = True  → only ADMINs are permitted
        browser = False → both ADMINs and FARMERs are permitted
    """
    browser_header = request.headers.get("X-Device-Browser", "").strip()
    # "N/A" is the explicit sentinel sent by the Flutter app
    return browser_header.lower() not in ("n/a", "")


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthService:
    """Constructs AuthService with all required sub-services injected."""
    user_repo = UserRepository(db)
    user_session_repo = UserSessionRepository(db)
    sms_provider = get_sms_provider()

    otp_service = OTPService(redis, sms_provider)
    token_service = TokenService()
    session_service = SessionService(user_session_repo, redis)

    return AuthService(user_repo, otp_service, token_service, session_service)


# Convenience type alias — use this in endpoint function signatures
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
