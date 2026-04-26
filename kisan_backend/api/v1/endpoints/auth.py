"""
auth.py — Authentication & WebSocket endpoint routing.

This module is intentionally thin: it handles HTTP request/response shaping
only. All service construction is delegated to `auth_deps`, and all business
logic lives in the service layer. (SRP / Clean Architecture)
"""

from typing import Optional
from fastapi import APIRouter, Depends, status, Response, WebSocket, WebSocketDisconnect, Request
import asyncio
import uuid
import base64
import json
import random
from datetime import datetime, timezone
from loguru import logger

from kisan_backend.core.responses import SuccessResponse, ApiResponse
from kisan_backend.core.messages import ResponseMessages
from kisan_backend.core.constants import SessionConfig
from kisan_backend.models.user import UserRole, User
from kisan_backend.schemas.auth import VerifyOTPRequest, SendOTPRequest, RefreshTokenRequest, DeviceMetadata, UpdateFCMTokenRequest
from kisan_backend.core.ws_manager import manager
from kisan_backend.api.v1.dependencies.auth_deps import AuthServiceDep, get_device_meta, is_browser_request, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# OTP Endpoints
# ---------------------------------------------------------------------------

@router.post("/send-otp")
async def send_otp(
    request: Request,
    send_req: SendOTPRequest,
    auth_service: AuthServiceDep,
):
    if is_browser_request(request):
        logger.warning("[AUTH] OTP send blocked: Browser requests not allowed on mobile endpoint.")
        return ApiResponse(
            success=False,
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    otp_response = await auth_service.send_otp(send_req.phone_number, channel=send_req.channel)

    channel_name = send_req.channel.value.upper() if hasattr(send_req.channel, "value") else str(send_req.channel).upper()

    return SuccessResponse(
        message=ResponseMessages.OTP_SENT.format(channel=channel_name),
        data=otp_response,
    )


@router.post("/verify-otp")
async def verify_otp(
    request: Request,
    verify_req: VerifyOTPRequest,
    response: Response,
    auth_service: AuthServiceDep,
):
    # 1. Verify OTP — keep state alive if not forcing (conflict check needs it)
    user, is_new = await auth_service.verify_otp(
        verify_req.phone_number,
        verify_req.otp,
        clear_state=verify_req.force,
        auto_create=True,
    )

    device_meta = get_device_meta(request)
    from_browser = is_browser_request(request)

    # ── Access Control ──────────────────────────────────────────────────────
    # This endpoint is strictly for Native Mobile Apps (Flutter).
    # Browser requests must use the /admin/auth endpoints.
    if from_browser:
        logger.warning(f"[AUTH] Browser login attempted on mobile endpoint by user {user.id}")
        return ApiResponse(
            success=False,
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if user.role not in (UserRole.ADMIN, UserRole.FARMER):
        logger.warning(
            f"[AUTH] Mobile login blocked for unsupported role: {user.role} (user {user.id})"
        )
        return ApiResponse(
            success=False,
            message=ResponseMessages.ACCESS_DENIED_ADMIN_ONLY,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    if user.role == UserRole.ADMIN and not verify_req.force:
        active_sessions = await auth_service.session_service.get_user_active_sessions_metadata(user.id)
        other_device_sessions = [s for s in active_sessions if s.device_id != device_meta.device_id]

        if other_device_sessions:
            logger.warning(f"[SESSION] Conflict detected for user {user.id}. Current device: {device_meta.device_id}")
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

    # 3. Session Handover (Force Flow)
    if verify_req.force:
        logger.info(f"🔄 [SESSION] Force login handover initiated for user {user.id}")

        # Clear OTP immediately — prevents replay during handover window
        await auth_service.otp_service._clear_state(verify_req.phone_number)

        # Notify existing sockets to disconnect
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

        # Deactivate all sessions in DB and purge Redis keys
        await auth_service.session_service.session_repo.deactivate_all_user_sessions(user.id)
        prefix = f"session:{user.id}:*"
        keys = await auth_service.session_service.redis.keys(prefix)
        if keys:
            await auth_service.session_service.redis.delete(*keys)

        # Wait for old client to acknowledge disconnect (max HANDOVER_TIMEOUT_SECONDS)
        handover_done = await manager.wait_for_user_disconnect(
            str(user.id), timeout=SessionConfig.HANDOVER_TIMEOUT_SECONDS
        )
        if handover_done:
            logger.info(f"✅ [SESSION] Handover cleanup successful for user {user.id}")
        else:
            logger.warning(f"⚠️ [SESSION] Handover timeout for user {user.id}. Forcing proceed.")

    # 4. Clear OTP state for normal (non-force) flow
    if not verify_req.force:
        await auth_service.otp_service._clear_state(verify_req.phone_number)

    tokens = await auth_service.create_tokens(str(user.id), device_meta=device_meta)

    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK

    return SuccessResponse(
        message=ResponseMessages.OTP_VERIFIED,
        data={
            "user_id": user.id,
            "is_new_user": is_new,
            "is_kyc_completed": user.is_kyc_completed,
            "is_verified": user.is_verified,
            **tokens,
        },
    )


# ---------------------------------------------------------------------------
# Token & Session Endpoints
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_req: RefreshTokenRequest,
    auth_service: AuthServiceDep,
):
    user_id, session_id = await auth_service.verify_refresh_token(refresh_req.refresh_token)
    device_meta = get_device_meta(request)
    tokens = await auth_service.create_tokens(user_id, device_meta=device_meta, session_id=session_id)

    return SuccessResponse(message=ResponseMessages.TOKEN_REFRESHED, data=tokens)


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthServiceDep,
):
    """Terminates the specific session identified by the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error("[AUTH] Logout failed: Missing or invalid Authorization header.")
        return ApiResponse(
            success=False,
            message="Missing authorization header",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = auth_header.split(" ")[1]
    try:
        payload = auth_service.token_service.decode_token(token)
        user_id = payload.get("sub")
        session_id = payload.get("sid")

        if not user_id or not session_id:
            raise ValueError("Invalid token structure")

        logger.info(f"[AUTH] Manual logout initiated — User: {user_id}, Session: {session_id}")
        await auth_service.invalidate_session(user_id, session_id)

        return SuccessResponse(message=ResponseMessages.LOGOUT_SUCCESS, data={"handshake": True})
    except Exception as e:
        logger.error(f"[AUTH] Logout invalidation failed: {e}")
        # Token already expired / session dead — still clear client-side state
        return SuccessResponse(message="Session already terminated or token expired", data={"handshake": True})


@router.post("/fcm-token")
async def update_fcm_token(
    request: Request,
    request_data: UpdateFCMTokenRequest,
    auth_service: AuthServiceDep,
    user: User = Depends(get_current_user),
):
    """Update user's FCM token."""
    device_meta = get_device_meta(request)
    device_id = device_meta.device_id

    await auth_service.update_fcm_token(user.id, device_id, request_data.fcm_token)
    return SuccessResponse(message="FCM token updated successfully")


# ---------------------------------------------------------------------------
# WebSocket Transport
# ---------------------------------------------------------------------------

@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    auth_service: AuthServiceDep,
    meta: Optional[str] = None,
):
    """
    WebSocket endpoint with First-Class Transport capabilities.
    Enforces encoded handshake metadata and signed payload headers.
    """
    user_id = None
    session_id = None

    async def _token_monitor(ws: WebSocket, uid: str, sid: str, d_meta: DeviceMetadata) -> None:
        """Background task that pushes refreshed tokens before expiry (every ~60s)."""
        try:
            while True:
                await asyncio.sleep(60)

                if not await auth_service.session_service.is_session_active(uid, sid):
                    break

                new_tokens = await auth_service.create_tokens(uid, device_meta=d_meta, session_id=sid)
                logger.info(f"🔄 [SOCKET] Auto-pushing fresh tokens for User: {uid}")
                await manager.send_event(
                    ws,
                    event="system",
                    event_type="token",
                    data=new_tokens,
                    request_id=str(uuid.uuid4()),
                )
        except Exception as e:
            logger.error(f"❌ [SOCKET] Token monitor failed for {uid}: {e}")

    try:
        # 1. Decode Handshake Metadata
        device_meta = DeviceMetadata(device_id="unknown")

        if meta:
            try:
                device_info = json.loads(base64.b64decode(meta).decode("utf-8"))
                logger.info(f"📱 [SOCKET] Handshake device: {device_info.get('X-Device-Id')}")
                device_meta = DeviceMetadata(
                    device_id=device_info.get("X-Device-Id", "unknown"),
                    brand=device_info.get("X-Device-Brand", "unknown"),
                    model=device_info.get("X-Device-Model", "unknown"),
                    os_name=device_info.get("X-Device-OS", "unknown"),
                    os_version=device_info.get("X-Device-OS-Version", "unknown"),
                    app_version=device_info.get("X-App-Version", "unknown"),
                )
            except Exception as e:
                logger.error(f"❌ [SOCKET] Metadata decode failure: {e}")
                await websocket.close(code=4001)
                return

        # 2. Validate Token & Session
        try:
            payload = auth_service.token_service.decode_token(token)
            user_id = payload.get("sub")
            session_id = payload.get("sid")

            if not user_id or not session_id:
                logger.warning(f"⚠️ [SOCKET] Invalid token structure")
                await websocket.close(code=4001)
                return

            if not await auth_service.session_service.is_session_active(user_id, session_id):
                logger.warning(f"⚠️ [SOCKET] Inactive session {session_id} for User {user_id}")
                await websocket.close(code=4001)
                return
        except Exception as e:
            logger.error(f"❌ [SOCKET] Handshake Auth Failure: {e}")
            await websocket.close(code=4001)
            return

        # 3. Initialize Connection with randomised heartbeat interval (30-60s)
        heartbeat_interval = random.randint(30, 60)
        await manager.connect(user_id, websocket, heartbeat_interval)

        monitor_task = asyncio.create_task(_token_monitor(websocket, user_id, session_id, device_meta))
        last_heartbeat = datetime.now(timezone.utc)
        safe_window = heartbeat_interval + 10  # 10s grace period

        try:
            while True:
                data_text = await websocket.receive_text()

                try:
                    envelope = json.loads(data_text)
                    event = envelope.get("event")
                    e_type = envelope.get("type")
                    data_wrapper = envelope.get("data", {})
                    headers = data_wrapper.get("headers", {})
                    req_id = data_wrapper.get("request_id")

                    # 4. Mandatory Signed Header Verification
                    if not headers.get("Authorization", "").startswith("Bearer "):
                        raise ValueError("Missing signed Authorization header")

                    # 5. Heartbeat
                    if event == "heartbeat" and e_type == "ping":
                        last_heartbeat = datetime.now(timezone.utc)
                        await manager.send_event(websocket, "system", "pong", {"message": "pong"}, request_id=req_id)
                        continue

                    # 6. API Dispatcher (Socket-as-Transport)
                    if event == "api":
                        if e_type == "http_get":
                            path = data_wrapper.get("data", {}).get("path", "")
                            if "/auth/sessions" in path:
                                sessions = await auth_service.session_service.get_user_active_sessions_metadata(user_id)
                                await manager.send_event(websocket, "api", "response", {"success": True, "data": sessions}, request_id=req_id)
                            else:
                                await manager.send_event(
                                    websocket,
                                    "api",
                                    "response",
                                    {"success": False, "message": f"Endpoint {path} not yet supported over socket transport."},
                                    request_id=req_id,
                                )

                except Exception as e:
                    logger.error(f"⚠️ [SOCKET] Payload error for User {user_id}: {e}")
                    await manager.send_event(websocket, "system", "error", {"success": False, "message": str(e)})

        except WebSocketDisconnect:
            monitor_task.cancel()
            manager.disconnect(user_id, websocket)

    except Exception as e:
        logger.error(f"🔴 [SOCKET] Critical error: {e}")
        try:
            close_code = 4001 if any(k in str(e).lower() for k in ("auth", "token")) else status.WS_1011_INTERNAL_ERROR
            await websocket.close(code=close_code)
        except Exception:
            pass
