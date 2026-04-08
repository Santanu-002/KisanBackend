from enum import Enum
from pydantic import BaseModel, Field

class ChannelType(str, Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"

class SendOTPRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+91 ?(?:1111111111|[6-9]\d{9})$", description="Indian phone number starting with +91")
    channel: ChannelType = Field(default=ChannelType.SMS)

class SendOTPResponse(BaseModel):
    phone_number: str
    remaining_attempts: int
    resend_accepts_at: str

class VerifyOTPRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+91 ?(?:1111111111|[6-9]\d{9})$")
    otp: str = Field(..., min_length=4, max_length=6)

class TokenResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    access_token_expire_at: str
    refresh_token_expire_at: str
    token_issued_at: str
    session_id: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class DeviceMetadata(BaseModel):
    device_id: str
    brand: str = "unknown"
    model: str = "unknown"
    os_name: str = "unknown"
    os_version: str = "unknown"
    app_version: str = "unknown"
    ip_address: str | None = None
