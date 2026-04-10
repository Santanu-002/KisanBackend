from typing import Optional
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from kisan_backend.models.kyc import KYCDetails
from kisan_backend.models.user import User

class KYCRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, kyc: KYCDetails) -> KYCDetails:
        self.session.add(kyc)
        await self.session.flush()
        return kyc

    async def get_by_user_id(self, user_id: UUID) -> Optional[KYCDetails]:
        statement = select(KYCDetails).where(KYCDetails.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def update_user_kyc_status(self, user_id: UUID, is_completed: bool) -> None:
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().first()
        if user:
            user.is_kyc_completed = is_completed
            # Note: caller should commit
