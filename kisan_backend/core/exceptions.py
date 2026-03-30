from enum import Enum
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class ErrorCode(str, Enum):
    AUTH_001 = "AUTH_001"  # Invalid OTP
    AUTH_002 = "AUTH_002"  # OTP expired
    AUTH_003 = "AUTH_003"  # Too many attempts
    AUTH_004 = "AUTH_004"  # User not found
    SYS_001 = "SYS_001"    # Internal server error
    VAL_001 = "VAL_001"    # Validation error
    RAT_001 = "RAT_001"    # Rate limit exceeded

class ErrorType(str, Enum):
    AUTH_ERROR = "AUTH_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"

class AppBaseException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        type: ErrorType,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message
        self.type = type

class AuthException(AppBaseException):
    def __init__(self, code: ErrorCode, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code, code, message, ErrorType.AUTH_ERROR)

class ValidationException(AppBaseException):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, code, message, ErrorType.VALIDATION_ERROR)

class RateLimitException(AppBaseException):
    def __init__(self, message: str = "Too many requests"):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, ErrorCode.RAT_001, message, ErrorType.RATE_LIMIT_ERROR)

class SystemException(AppBaseException):
    def __init__(self, message: str = "Internal server error"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.SYS_001, message, ErrorType.SYSTEM_ERROR)
