from typing import Any, Optional, Dict
from pydantic import BaseModel, ConfigDict, Field

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ErrorResponseDetail(BaseModel):
    code: str
    message: str
    type: str

class ErrorResponse(BaseModel):
    success: bool = False
    data: Any = None
    error: ErrorResponseDetail
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ResponseWrapperMiddleware:
    # This will be integrated in main.py instead of a separate middleware class 
    # to avoid double-processing with exception handlers.
    pass
