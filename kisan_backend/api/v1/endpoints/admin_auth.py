"""
admin_auth.py — Dedicated authentication for Admin Web Panel.

Enforces strict channel-role isolation:
1. Only browser requests are permitted here.
2. Only ADMIN role users can verify OTP here.
"""

from fastapi import APIRouter, Depends, status, Response, Request
from loguru import logger

from kisan_backend.core.responses import SuccessResponse, ApiResponse, ErrorResponse
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.constants import SessionConfig
from kisan_backend.models.user import UserRole
from kisan_backend.schemas.auth import VerifyOTPRequest, SendOTPRequest
from kisan_backend.core.ws_manager import manager
from kisan_backend.api.v1.dependencies.auth_deps import AuthServiceDep, get_device_meta, is_browser_request

router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])

@router.post("/send-otp")
async def send_admin_otp(
    request: Request,
    send_req: SendOTPRequest,
    auth_service: AuthServiceDep,
):
    """
    Sends OTP for Admin login. 
    Strictly restricted to browser requests.
    """
    if not is_browser_request(request):
        logger.warning("[ADMIN-AUTH] OTP send blocked: Non-browser request.")
        return ApiResponse(
            success=False,
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
            status_code=status.HTTP_403_FORBIDDEN
        )

    # 2. Admin Role Check - Fail early if user is not an admin
    user = await auth_service.user_repo.get_by_phone(send_req.phone_number)
    if not user or user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        logger.warning(f"[ADMIN-AUTH] OTP send blocked: {send_req.phone_number} is not an authorized admin.")
        return ApiResponse(
            success=False,
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
            status_code=status.HTTP_403_FORBIDDEN
        )

    otp_response = await auth_service.send_otp(send_req.phone_number, channel=send_req.channel)
    channel_name = send_req.channel.value.upper() if hasattr(send_req.channel, "value") else str(send_req.channel).upper()

    return SuccessResponse(
        message=ResponseMessages.OTP_SENT.format(channel=channel_name),
        data=otp_response,
    )

@router.post("/verify-otp")
async def verify_admin_otp(
    request: Request,
    verify_req: VerifyOTPRequest,
    response: Response,
    auth_service: AuthServiceDep,
):
    """
    Verifies OTP and issues tokens for Admin login.
    Enforces browser-only and admin-only rules.
    """
    # 1. Channel Gating
    if not is_browser_request(request):
        logger.warning("[ADMIN-AUTH] OTP verification blocked: Non-browser request.")
        return ErrorResponse(
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY
        )

    # 2. Verify OTP
    user, is_new = await auth_service.verify_otp(
        verify_req.phone_number,
        verify_req.otp,
        clear_state=verify_req.force,
    )

    # 3. Role Gating (Since this is the ADMIN portal, only ADMINS/SUPER_ADMINS are allowed)
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        logger.warning(f"[ADMIN-AUTH] Non-admin login attempt by {user.id} (role={user.role})")
        return ErrorResponse(
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
            status_code=status.HTTP_403_FORBIDDEN
        )

    device_meta = get_device_meta(request)

    # 4. Session Conflict Handling (Admin specific)
    if not verify_req.force:
        active_sessions = await auth_service.session_service.get_user_active_sessions_metadata(user.id)
        other_device_sessions = [s for s in active_sessions if s.device_id != device_meta.device_id]

        if other_device_sessions:
            logger.info(f"[ADMIN-AUTH] Session conflict for admin {user.id}")
            return SuccessResponse(
                message=ResponseMessages.SESSION_CONFLICT,
                data={
                    "session_conflict": True,
                    "active_session": other_device_sessions[0],
                    "user_id": user.id,
                    "phone_number": verify_req.phone_number,
                    "otp": verify_req.otp,
                },
            )

    # 5. Handover Flow (Force login)
    if verify_req.force:
        logger.info(f"🔄 [ADMIN-AUTH] Force login handover for admin {user.id}")
        await auth_service.otp_service._clear_state(verify_req.phone_number)
        
        # Notify existing sockets
        logout_event = {
            "event": "system",
            "type": "session_revoked",
            "data": {
                "success": True,
                "message": ResponseMessages.SESSION_REVOKED,
                "data": {"reason": "handover"},
            },
        }
        await manager.broadcast_to_user(str(user.id), logout_event)

        # Deactivate sessions
        await auth_service.session_service.session_repo.deactivate_all_user_sessions(user.id)
        prefix = f"session:{user.id}:*"
        keys = await auth_service.session_service.redis.keys(prefix)
        if keys:
            await auth_service.session_service.redis.delete(*keys)

        await manager.wait_for_user_disconnect(
            str(user.id), timeout=SessionConfig.HANDOVER_TIMEOUT_SECONDS
        )

    # 6. Issue Tokens
    if not verify_req.force:
        await auth_service.otp_service._clear_state(verify_req.phone_number)

    tokens = await auth_service.create_tokens(str(user.id), device_meta=device_meta)
    
    return SuccessResponse(
        message=ResponseMessages.OTP_VERIFIED,
        data={
            "is_new_user": is_new,
            **tokens,
        },
    )
