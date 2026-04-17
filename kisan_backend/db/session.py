from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel
from kisan_backend.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True, # Enable verbose SQL logging for CRUD visibility
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    """Dependency for obtaining an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

import os
import sys
import subprocess
from loguru import logger

async def init_db():
    """Bootstrap the database by running Alembic migrations."""
    try:
        # We run the migration via subprocess to ensure it uses the project's
        # alembic configuration and environment properly.
        # This is the "Migration-First" approach mandated by RULEBOOK.md
        logger.info("Applying database migrations...")
        
        # Use sys.executable to ensure we use the same Python environment
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Migrations applied successfully:\n{result.stdout}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to apply migrations: {e.stderr}")
        # In development, we might want to continue, but in Prod this should probably halt.
        # For now, we'll log it and let the app try to start.
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
