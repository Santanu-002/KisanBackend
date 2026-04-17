from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from kisan_backend.core.config import settings
from kisan_backend.db.session import get_db
from kisan_backend.db.redis import get_redis
from kisan_backend.repositories.user_repository import UserRepository
from kisan_backend.models.user import User, UserRole

reusable_oauth2 = HTTPBearer()

async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    token: Annotated[HTTPAuthorizationCredentials, Depends(reusable_oauth2)]
) -> User:
    try:
        payload = jwt.decode(
            token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        session_id: str = payload.get("sid")
        token_type: str = payload.get("type")
        
        if user_id is None or session_id is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
            
        # Check session in Redis
        session_key = f"session:{user_id}:{session_id}"
        if not await redis.exists(session_key):
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalidated",
            )
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
        
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Ensures the current user has the 'ADMIN' role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have administrative privileges"
        )
    return current_user
