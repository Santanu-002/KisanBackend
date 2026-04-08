import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
import os
import sys

# Add the project root to sys.path so we can import our modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from kisan_backend.core.config import settings
from kisan_backend.models.user import User
from kisan_backend.models.profile import Profile

async def reset_db():
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(SQLModel.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
    
    await engine.dispose()
    print("Database reset complete!")

if __name__ == "__main__":
    asyncio.run(reset_db())
