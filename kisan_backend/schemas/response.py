from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class SuccessResponse(BaseModel, Generic[T]):
    """Standardized success response envelope for all API endpoints."""
    success: bool = True
    message: str
    data: Optional[T] = None
