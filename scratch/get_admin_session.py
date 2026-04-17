import asyncio
from kisan_backend.db.session import AsyncSessionLocal
from kisan_backend.models.user_session import UserSession
from kisan_backend.models.user import User, UserRole
from sqlmodel import select

async def get_token():
    async with AsyncSessionLocal() as session:
        # Find an admin user first
        admin_query = select(User).where(User.role == UserRole.ADMIN).limit(1)
        admin_res = await session.execute(admin_query)
        admin = admin_res.scalar_one_or_none()
        
        if not admin:
            print("No admin user found")
            return

        # Find their active session
        session_query = select(UserSession).where(UserSession.user_id == admin.id).where(UserSession.is_active == True).limit(1)
        session_res = await session.execute(session_query)
        s = session_res.scalar_one_or_none()
        
        if s:
            print(f"SESSION_ID:{s.id}")
        else:
            print(f"No active session for admin {admin.id}")

if __name__ == "__main__":
    asyncio.run(get_token())
