from typing import Optional, Any
import uuid
from pydantic import BaseModel, Field
from datetime import datetime

class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: uuid.UUID
    phone_number: str
    role: str
    language: str
    is_active: bool
    is_kyc_completed: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    # Flattened profile data
    full_name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Granular permissions
    permissions: list[str] = []
    
    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user: Any) -> "UserResponse":
        """Explicitly create a UserResponse from a User model and its Profile."""
        from kisan_backend.core.permissions import get_role_permissions
        profile = getattr(user, "profile", None)
        return cls(
            id=user.id,
            phone_number=user.phone_number,
            role=user.role,
            language=user.language,
            is_active=user.is_active,
            is_kyc_completed=user.is_kyc_completed,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            full_name=profile.full_name if profile else None,
            email=profile.email if profile else None,
            gender=profile.gender if profile else None,
            avatar_url=profile.avatar_url if profile else None,
            permissions=[p.value for p in get_role_permissions(user.role)]
        )

class AvatarUploadUrlResponse(BaseModel):
    upload_url: str
    file_key: str

class PredefinedAvatarResponse(BaseModel):
    avatars: list[str]
