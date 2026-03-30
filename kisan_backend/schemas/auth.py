from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

class SendOTPRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+91[6-9]\d{9}$", description="Indian phone number starting with +91")

class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+91[6-9]\d{9}$")
    otp: str = Field(..., min_length=4, max_length=6)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str
