import os
import uuid
from typing import List, Optional, Tuple
import aioboto3
from botocore.config import Config
from datetime import datetime, timezone

from sqlalchemy.future import select
from kisan_backend.core.config import settings
from kisan_backend.models.user import User
from kisan_backend.models.profile import Profile
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.schemas.user import UserUpdate

from kisan_backend.services.storage_service import StorageService
from fastapi import UploadFile

class UserService:
    def __init__(self, user_repo: UserRepository, storage_service: StorageService):
        self.user_repo = user_repo
        self.storage_service = storage_service

    async def get_user(self, user_id: str) -> Optional[User]:
        return await self.user_repo.get_by_id(user_id)

    async def update_profile(self, user_id: str, update_data: UserUpdate, avatar_file: Optional[UploadFile] = None) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            from kisan_backend.core.exceptions import NotFoundException
            raise NotFoundException("User not found")
        
        # Check if profile exists, if not create one
        profile = user.profile
        if not profile:
            profile = Profile(user_id=user.id)
            self.user_repo.session.add(profile)
        
        # Update profile fields
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        # Handle avatar file upload if provided
        if avatar_file:
            timestamp = int(datetime.utcnow().timestamp())
            avatar_url = await self.storage_service.upload_file(
                avatar_file,
                folder=f"profile/uploads/{user_id}",
                filename=f"avatar_{timestamp}.jpg"
            )
            profile.avatar_url = avatar_url
        
        profile.updated_at = datetime.utcnow()
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user, ["profile"])
        return user

    async def create_profile(
        self, 
        user_id: str, 
        full_name: str, 
        email: Optional[str] = None, 
        gender: Optional[str] = None, 
        avatar_url: Optional[str] = None,
        avatar_file: Optional[UploadFile] = None
    ) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            from kisan_backend.core.exceptions import NotFoundException
            raise NotFoundException("User not found")
            
        profile = user.profile
        if not profile:
            profile = Profile(user_id=user.id)
            self.user_repo.session.add(profile)
            
        profile.full_name = full_name
        if email is not None:
            profile.email = email
        if gender is not None:
            profile.gender = gender

        # If a file is uploaded, it takes precedence over avatar_url (predefined)
        if avatar_file:
            timestamp = int(datetime.utcnow().timestamp())
            avatar_url = await self.storage_service.upload_file(
                avatar_file,
                folder=f"profile/uploads/{user_id}",
                filename=f"avatar_{timestamp}.jpg"
            )
            profile.avatar_url = avatar_url
        elif avatar_url is not None:
            profile.avatar_url = avatar_url
            
        profile.updated_at = datetime.utcnow()
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user, ["profile"])
        return user

    async def get_avatar_upload_url(self, user_id: str, content_type: str = "image/jpeg") -> Tuple[str, str]:
        """Generates a presigned URL for uploading a profile picture."""
        file_key = f"profile/uploads/{user_id}/avatar.jpg"
        url = await self.storage_service.get_presigned_url(file_key, content_type)
        return url, file_key

    async def get_kyc_upload_url(self, user_id: str, filename: str, content_type: str = "image/jpeg") -> Tuple[str, str]:
        """Generates a presigned URL for uploading a KYC document."""
        ext = os.path.splitext(filename)[1] or ".jpg"
        file_key = f"profile/kyc/{user_id}/{uuid.uuid4()}{ext}"
        url = await self.storage_service.get_presigned_url(file_key, content_type)
        return url, file_key

    async def submit_kyc(self, user_id: str) -> User:
        """Marks the user's KYC as completed."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            from kisan_backend.core.exceptions import NotFoundException
            raise NotFoundException("User not found")
        
        user.is_kyc_completed = True
        user.updated_at = datetime.utcnow()
        await self.user_repo.session.flush()
        return user

    async def get_predefined_avatars(self) -> List[str]:
        """Lists available avatars from the predefined path."""
        prefix = "profile/avatars/"
        return await self.storage_service.list_objects(prefix)
