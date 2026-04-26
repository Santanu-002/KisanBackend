import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from kisan_backend.models.user import User, UserRole
from kisan_backend.models.kyc import KYCDetails, KYCStatus

class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_count(
        self, 
        role: Optional[UserRole] = None, 
        search: Optional[str] = None
    ) -> int:
        """Counts users with optional role and search filters."""
        query = select(func.count(User.id))
        
        if role:
            query = query.where(User.role == role)
        if search:
            query = query.where(User.phone_number.contains(search))
            
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_users_paged(
        self, 
        page: int = 1, 
        size: int = 10, 
        search: Optional[str] = None,
        role: Optional[UserRole] = None
    ) -> Tuple[List[User], int]:
        """Fetches a paginated list of users with search and filter."""
        query = select(User).options(selectinload(User.profile), selectinload(User.kyc_details), selectinload(User.sessions))
        
        if search:
            query = query.where(User.phone_number.contains(search))
        
        if role:
            query = query.where(User.role == role)
            
        # Get total count using the dedicated count method
        total = await self.get_user_count(role=role, search=search)
        
        # Apply pagination
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def get_pending_kycs(self) -> List[KYCDetails]:
        """Fetches all KYC submissions with PENDING status for Farmers."""
        query = (
            select(KYCDetails)
            .join(User)
            .where(KYCDetails.status == KYCStatus.PENDING)
            .where(User.role == UserRole.FARMER)
            .options(selectinload(KYCDetails.user).selectinload(User.profile))
            .order_by(KYCDetails.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_kyc_by_user_id(self, user_id: uuid.UUID) -> Optional[KYCDetails]:
        """Fetches KYC details for a specific user."""
        query = (
            select(KYCDetails)
            .where(KYCDetails.user_id == user_id)
            .options(selectinload(KYCDetails.user).selectinload(User.profile))
        )
        result = await self.session.execute(query)
        return result.scalars().first()
