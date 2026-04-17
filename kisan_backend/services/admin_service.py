import uuid
from typing import List, Optional, Tuple
from kisan_backend.models.kyc import KYCStatus
from kisan_backend.models.user import User, UserRole
from kisan_backend.repositories.admin_repository import AdminRepository
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.repositories.kyc_repository import KYCRepository
from kisan_backend.schemas.admin import AdminDashboardStats

class AdminService:
    def __init__(self, admin_repo: AdminRepository, user_repo: UserRepository, kyc_repo: KYCRepository):
        self.admin_repo = admin_repo
        self.user_repo = user_repo
        self.kyc_repo = kyc_repo

    async def get_users_paged(
        self, 
        page: int = 1, 
        size: int = 10, 
        search: Optional[str] = None,
        role: Optional[UserRole] = None
    ):
        return await self.admin_repo.get_users_paged(page, size, search, role)

    async def get_user_count(self, role: Optional[UserRole] = None):
        return await self.admin_repo.get_user_count(role=role)

    async def get_pending_kycs(self):
        return await self.admin_repo.get_pending_kycs()

    async def verify_kyc(
        self, 
        user_id: uuid.UUID, 
        approved: bool, 
        remarks: Optional[str] = None
    ):
        """
        Handles the verification logic:
        - Updates the KYCStatus.
        - Updates the User's is_verified flag.
        - Saves administrative remarks.
        """
        kyc = await self.admin_repo.get_kyc_by_user_id(user_id)
        if not kyc:
            raise ValueError("KYC record not found")
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        if approved:
            kyc.status = KYCStatus.APPROVED
            user.is_verified = True
        else:
            kyc.status = KYCStatus.REJECTED
            user.is_verified = False
            # If rejected, we might want to allow them to resubmit
            user.is_kyc_completed = False 

        kyc.remarks = remarks
        
        # Commit changes
        await self.admin_repo.session.commit()
        await self.admin_repo.session.refresh(kyc)
        await self.admin_repo.session.refresh(user)
        
        return kyc

    async def bulk_verify_kyc(
        self,
        user_ids: List[uuid.UUID],
        approved: bool,
        remarks: Optional[str] = None
    ):
        """Processes multiple KYC verifications in a single batch."""
        results = []
        for user_id in user_ids:
            try:
                kyc = await self.verify_kyc(user_id, approved, remarks)
                results.append(kyc)
            except ValueError:
                continue # Skip missing records during bulk
        return results

    async def get_dashboard_stats(self) -> AdminDashboardStats:
        """Calculates high-level metrics for the dashboard."""
        # Get counts directly for better performance and accuracy
        total_farmers = await self.admin_repo.get_user_count(role=UserRole.FARMER)
        pending_kycs = await self.admin_repo.get_pending_kycs()
        
        return AdminDashboardStats(
            total_farmers=total_farmers,
            pending_kyc_count=len(pending_kycs),
            active_plots=0 # Placeholder for future feature
        )
