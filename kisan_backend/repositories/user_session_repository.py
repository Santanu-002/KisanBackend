from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from kisan_backend.models.user_session import UserSession
from kisan_backend.schemas.auth import DeviceMetadata

class UserSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[UserSession]:
        result = await self.session.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        return result.scalars().first()

    async def upsert_session(
        self, 
        user_id: uuid.UUID, 
        session_id: uuid.UUID, 
        device_meta: DeviceMetadata
    ) -> UserSession:
        """
        Create or update a session instance.
        """
        db_session = await self.get_by_id(session_id)
        
        now = datetime.utcnow()
        
        if not db_session:
            db_session = UserSession(
                id=session_id,
                user_id=user_id,
                device_id=device_meta.device_id,
                brand=device_meta.brand,
                model=device_meta.model,
                os_name=device_meta.os_name,
                os_version=device_meta.os_version,
                app_version=device_meta.app_version,
                ip_address=device_meta.ip_address,
                is_active=True,
                last_login_at=now,
                created_at=now,
                updated_at=now
            )
            self.session.add(db_session)
        else:
            db_session.is_active = True
            db_session.last_login_at = now
            db_session.logout_at = None
            db_session.updated_at = now
            db_session.app_version = device_meta.app_version
            db_session.ip_address = device_meta.ip_address
            # Ensure we update status if it was inactive
            self.session.add(db_session)

        await self.session.commit()
        await self.session.refresh(db_session)
        return db_session

    async def get_active_sessions_by_device(self, user_id: uuid.UUID, device_id: str) -> list[UserSession]:
        """Find all active sessions for a user on a specific device."""
        result = await self.session.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.device_id == device_id,
                UserSession.is_active == True
            )
        )
        return list(result.scalars().all())

    async def deactivate_device_sessions(self, user_id: uuid.UUID, device_id: str) -> list[str]:
        """
        Deactivate all active sessions for a device. 
        Returns the list of session IDs that were deactivated.
        """
        active_sessions = await self.get_active_sessions_by_device(user_id, device_id)
        deactivated_ids = []
        
        now = datetime.utcnow()
        for session in active_sessions:
            session.is_active = False
            session.logout_at = now
            session.updated_at = now
            self.session.add(session)
            deactivated_ids.append(str(session.id))
            
        if deactivated_ids:
            await self.session.commit()
            
        return deactivated_ids

    async def deactivate_all_user_sessions(self, user_id: uuid.UUID) -> list[str]:
        """
        Deactivate every active session for a specific user across all devices.
        Returns the list of session IDs that were deactivated.
        """
        result = await self.session.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        active_sessions = list(result.scalars().all())
        deactivated_ids = []
        
        now = datetime.now()
        for session in active_sessions:
            session.is_active = False
            session.logout_at = now
            session.updated_at = now
            self.session.add(session)
            deactivated_ids.append(str(session.id))
            
        if deactivated_ids:
            await self.session.commit()
            
        return deactivated_ids

    async def deactivate_session(self, session_id: uuid.UUID) -> Optional[UserSession]:
        db_session = await self.get_by_id(session_id)
        if db_session:
            db_session.is_active = False
            db_session.logout_at = datetime.now()
            db_session.updated_at = datetime.now()
            self.session.add(db_session)
            await self.session.commit()
            await self.session.refresh(db_session)
        return db_session
