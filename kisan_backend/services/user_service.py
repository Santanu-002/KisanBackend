import os
import uuid
from typing import List, Optional, Tuple
import aioboto3
from botocore.config import Config
from datetime import datetime

from sqlalchemy.future import select
from kisan_backend.core.config import settings
from kisan_backend.models.user import User
from kisan_backend.models.profile import Profile
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.schemas.user import UserUpdate

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.session = aioboto3.Session()

    async def get_user(self, user_id: str) -> Optional[User]:
        # User repo should ideally load profile too. 
        # For SQLModel Relationship, it might need explicit selection or lazy load.
        return await self.user_repo.get_by_id(user_id)

    async def update_profile(self, user_id: str, update_data: UserUpdate) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise Exception("User not found")
        
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
        
        profile.updated_at = datetime.utcnow()
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user, ["profile"])
        return user

    async def get_avatar_upload_url(self, user_id: str, content_type: str = "image/jpeg") -> Tuple[str, str]:
        """Generates a presigned URL for uploading a profile picture to R2."""
        file_key = f"profile/uploads/{user_id}/avatar.jpg"
        
        async with self.session.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name=settings.S3_REGION
        ) as s3:
            url = await s3.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': settings.S3_BUCKET_NAME,
                    'Key': file_key,
                    'ContentType': content_type,
                },
                ExpiresIn=3600  # 1 hour
            )
            return url, file_key

    async def get_predefined_avatars(self) -> List[str]:
        """Lists available avatars from the predefined path in R2."""
        prefix = "profile/avatars/"

        async with self.session.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION
        ) as s3:
            response = await s3.list_objects_v2(
                Bucket=settings.S3_BUCKET_NAME,
                Prefix=prefix
            )
            
            avatars = []
            if 'Contents' in response:
                public_prefix = settings.S3_PUBLIC_URL_PREFIX or settings.S3_ENDPOINT_URL
                for obj in response['Contents']:
                    if obj['Key'] != prefix: # Skip the prefix directory itself
                        avatars.append(f"{public_prefix}/{obj['Key']}")
            
            return avatars
