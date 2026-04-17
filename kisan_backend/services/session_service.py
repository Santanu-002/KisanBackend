import uuid
from typing import Optional, List
from redis.asyncio import Redis

from sqlalchemy.future import select
from kisan_backend.models.user_session import UserSession
from kisan_backend.repositories.user_session_repository import UserSessionRepository
from kisan_backend.schemas.auth import DeviceMetadata

class SessionService:
    """Manages user sessions across Redis (live state) and Database (audit log)."""

    def __init__(self, session_repo: UserSessionRepository, redis: Redis):
        self.session_repo = session_repo
        self.redis = redis

    async def init_session(self, user_id: uuid.UUID, device_meta: DeviceMetadata, force_single_device: bool = False) -> str:
        """
        Creates a new session.
        If force_single_device is True, it deactivates ALL other sessions for the user.
        Otherwise, it only deactivates sessions for the same device ID.
        """
        session_id = str(uuid.uuid4())
        
        if force_single_device:
            # Deactivate everything for this user
            old_sessions = await self.session_repo.deactivate_all_user_sessions(user_id)
        else:
            # Deactivate old sessions for just THIS device (standard policy)
            old_sessions = await self.session_repo.deactivate_device_sessions(user_id, device_meta.device_id)
        
        # Purge all identified old sessions from Redis live state
        for old_sid in old_sessions:
            await self.redis.delete(f"session:{user_id}:{old_sid}")

        # Audit in DB
        await self.session_repo.upsert_session(
            user_id=user_id,
            session_id=uuid.UUID(session_id),
            device_meta=device_meta
        )
        
        return session_id

    async def activate_session(self, user_id: str, session_id: str, device_meta: DeviceMetadata, expiry_seconds: int):
        """Sets the session as active in Redis (MetaStore Protocol)."""
        key = f"session:{user_id}:{session_id}"
        meta_dict = device_meta.model_dump(exclude_none=True)
        # Convert all values to strings for robust Hash storage
        mapping = {k: str(v) for k, v in meta_dict.items()}
        await self.redis.hset(key, mapping=mapping)
        await self.redis.expire(key, expiry_seconds)

    async def is_session_active(self, user_id: str, session_id: str) -> bool:
        """Checks if a session exists and is active in Redis MetaStore."""
        key = f"session:{user_id}:{session_id}"
        exists = await self.redis.exists(key)
        return exists > 0

    async def invalidate_session(self, user_id: str, session_id: str):
        """Permanently deactivates a session."""
        await self.redis.delete(f"session:{user_id}:{session_id}")
        try:
            await self.session_repo.deactivate_session(uuid.UUID(session_id))
        except Exception:
            pass # Fail gracefully for audit cleanup
    async def get_user_active_sessions_metadata(self, user_id: uuid.UUID) -> List[DeviceMetadata]:
        """Retrieves metadata for all active sessions of a user instantly from the Redis MetaStore."""
        prefix = f"session:{user_id}:*"
        keys = await self.redis.keys(prefix)
        
        from redis.exceptions import ResponseError

        sessions = []
        for key in keys:
            try:
                data = await self.redis.hgetall(key)
                if data:
                    # Ensure compatibility whether Redis decode_responses is True or False
                    decoded = {
                        k.decode('utf-8') if isinstance(k, bytes) else k: 
                        v.decode('utf-8') if isinstance(v, bytes) else v 
                        for k, v in data.items()
                    }
                    
                    # Verify it's a valid MetaStore payload
                    if 'device_id' in decoded:
                        sessions.append(DeviceMetadata(**decoded))
            except ResponseError:
                # Ghost session from before the MetaStore Hash migration (stored as raw string)
                # Purge it automatically to heal the environment
                await self.redis.delete(key)
                continue
                    
        # Primary MetaStore response
        if sessions:
            return sessions

        # Fallback to DB Audit Log if MetaStore is inexplicably cleared (but valid)
        result = await self.session_repo.session.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        db_sessions = result.scalars().all()
        return [
            DeviceMetadata(
                device_id=s.device_id,
                brand=s.brand,
                model=s.model,
                os_name=s.os_name,
                os_version=s.os_version,
                app_version=s.app_version,
                ip_address=s.ip_address
            ) for s in db_sessions
        ]
