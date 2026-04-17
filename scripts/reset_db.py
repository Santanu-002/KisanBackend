import asyncio
import os
import sys
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the project root to sys.path so we can import our modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from kisan_backend.core.config import settings

async def reset_db():
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        print("Truncating child tables with CASCADE...")
        await conn.execute(sa_text("TRUNCATE TABLE user_sessions, profiles, kyc_details CASCADE;"))

        print("Removing standard users...")
        await conn.execute(sa_text("DELETE FROM users WHERE role != 'admin';"))

        print("Checking for existing admin user...")
        result = await conn.execute(sa_text("SELECT id FROM users WHERE phone_number = '+912222222222' LIMIT 1;"))
        admin_exists = result.scalar()

        if not admin_exists:
            import uuid
            from datetime import datetime
            print("Seeding admin user...")
            admin_id = uuid.uuid4()
            now = datetime.utcnow()
            await conn.execute(sa_text("""
                INSERT INTO users (id, phone_number, role, is_active, is_kyc_completed, is_verified, created_at, updated_at, language)
                VALUES (:id, :phone, :role, :is_active, :is_kyc, :is_verified, :now, :now, 'en')
            """), {
                "id": admin_id,
                "phone": "+912222222222",
                "role": "admin",
                "is_active": True,
                "is_kyc": True,
                "is_verified": True,
                "now": now
            })
            print("Admin user seeded with phone +912222222222")
        else:
            print("Admin user already exists. Preserving...")

    await engine.dispose()
    print("Database reset complete!")

if __name__ == "__main__":
    asyncio.run(reset_db())
