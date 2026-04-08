from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from kisan_backend.core.config import settings
from kisan_backend.core.responses import ErrorResponse

class DeviceMetadataMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only enforce for API endpoints
        if request.url.path.startswith(settings.API_V1_STR):
            mandatory_headers = [
                "X-Device-Id",
                "X-Device-Brand",
                "X-Device-Model",
                "X-Device-OS",
                "X-Device-OS-Version",
                "X-App-Version"
            ]
            
            missing = [h for h in mandatory_headers if h not in request.headers]
            
            if missing:
                return ErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Missing mandatory device metadata headers: {', '.join(missing)}"
                )
                
        response = await call_next(request)
        return response
