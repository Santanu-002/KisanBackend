from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi import status
from fastapi.encoders import jsonable_encoder

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response envelope."""
    success: bool
    message: str
    data: Optional[T] = None

def SuccessResponse(
    message: str, 
    data: Any = None, 
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """Helper to create a standardized success response."""
    # Ensure no redundant fields like 'error' or 'meta'
    content = {
        "success": True,
        "message": message,
        "data": jsonable_encoder(data) if data is not None else None
    }
    return JSONResponse(status_code=status_code, content=content)

def ErrorResponse(
    message: str, 
    status_code: int = status.HTTP_400_BAD_REQUEST,
    data: Any = None
) -> JSONResponse:
    """Helper to create a standardized error response."""
    content = {
        "success": False,
        "message": message,
        "data": jsonable_encoder(data) if data is not None else None
    }
    return JSONResponse(status_code=status_code, content=content)
