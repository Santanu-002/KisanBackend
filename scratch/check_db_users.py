import asyncio
from kisan_backend.db.session import AsyncSessionLocal
from kisan_backend.models.user import User
from sqlalchemy.future import select

async def check_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Total Users in DB: {len(users)}")
        for u in users:
            print(f"ID: {u.id}, Phone: {u.phone_number}, Role: {u.role}")

if __name__ == "__main__":
    asyncio.run(check_users())
