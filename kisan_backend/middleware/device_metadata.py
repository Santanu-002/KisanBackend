from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from kisan_backend.core.config import settings
from kisan_backend.core.responses import ErrorResponse

class DeviceMetadataMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight OPTIONS requests to bypass header checks
        if request.method == "OPTIONS":
            return await call_next(request)

        # Only enforce for API endpoints
        if request.url.path.startswith(settings.API_V1_STR):
            mandatory_headers = [
                "X-Device-Id",
                "X-Device-Brand",
                "X-Device-Model",
                "X-Device-OS",
                "X-Device-OS-Version",
                "X-App-Version",
                "X-Device-Browser"
            ]
            
            missing = [h for h in mandatory_headers if h not in request.headers]
            
            if missing:
                return ErrorResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Device header missing"
                )
                
        response = await call_next(request)
        return response
