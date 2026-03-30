from typing import Optional, List
import uuid
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from kisan_backend.models.user import User
from datetime import datetime

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.phone_number == phone_number))
        return result.scalars().first()

    async def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.session.add(user)
        # Session commit is handled in the get_db dependency but we might need it for ID
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_last_login(self, user: User) -> User:
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        self.session.add(user)
        await self.session.flush()
        return user
