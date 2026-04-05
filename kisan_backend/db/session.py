from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel
from kisan_backend.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
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
        yield session

async def init_db():
    """Bootstrap the database by creating tables if they don't exist."""
    async with engine.begin() as conn:
        from kisan_backend.models.user import User  # noqa
        await conn.run_sync(SQLModel.metadata.create_all)
