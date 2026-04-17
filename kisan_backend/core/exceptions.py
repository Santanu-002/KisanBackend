from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class AppBaseException(HTTPException):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.message = message

class AuthException(AppBaseException):
    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code, message)

class ValidationException(AppBaseException):
    def __init__(self, message: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, message)

class RateLimitException(AppBaseException):
    def __init__(self, message: str = "Too many requests"):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, message)

class SystemException(AppBaseException):
    def __init__(self, message: str = "Internal server error"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, message)

class NotFoundException(AppBaseException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, message)
