from enum import Enum
from typing import Set, Dict
from kisan_backend.models.user import UserRole

class Permission(str, Enum):
    # User Management
    USERS_VIEW = "users:view"
    USERS_EDIT = "users:edit"
    USERS_DELETE = "users:delete"
    
    # KYC Management
    KYC_VIEW = "kyc:view"
    KYC_APPROVE = "kyc:approve"
    
    # Profile (Self)
    PROFILE_VIEW = "profile:view"
    PROFILE_EDIT = "profile:edit"
    
    # Dashboard / Stats
    STATS_VIEW = "stats:view"

    # Admin Management (SUPER_ADMIN only)
    ADMIN_MANAGE = "admin:manage"
    SYSTEM_CONFIG = "system:config"

# Mapping of Roles to their allowed Permissions
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.SUPER_ADMIN: {p for p in Permission},
    UserRole.ADMIN: {
        Permission.USERS_VIEW,
        Permission.USERS_EDIT,
        Permission.KYC_VIEW,
        Permission.KYC_APPROVE,
        Permission.PROFILE_VIEW,
        Permission.PROFILE_EDIT,
        Permission.STATS_VIEW,
    },
    UserRole.FARMER: {
        Permission.PROFILE_VIEW,
        Permission.PROFILE_EDIT,
    },
}

def get_role_permissions(role: UserRole) -> Set[Permission]:
    """Returns the set of permissions associated with a given role."""
    return ROLE_PERMISSIONS.get(role, set())
