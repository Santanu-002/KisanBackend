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
        print("Fetching all tables in public schema...")
        result = await conn.execute(sa_text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' AND tablename != 'alembic_version';
        """))
        tables = result.scalars().all()
        
        if tables:
            tables_str = ", ".join(f'"{table}"' for table in tables)
            print(f"Truncating tables with CASCADE: {tables_str}")
            await conn.execute(sa_text(f"TRUNCATE TABLE {tables_str} CASCADE;"))
        else:
            print("No tables found in public schema to truncate.")

    await engine.dispose()
    print("Database reset complete!")

if __name__ == "__main__":
    asyncio.run(reset_db())
