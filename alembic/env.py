import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import SQLModel
from kisan_backend.core.config import settings
# Import ALL models here to ensure they are registered in SQLModel.metadata
from kisan_backend.models.user import User
from kisan_backend.models.profile import Profile
from kisan_backend.models.user_session import UserSession
from kisan_backend.models.kyc import KYCDetails

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Helper to get a sync URL and handle Docker-to-localhost host switching."""
    url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    # If running from host outside Docker, 'db' isn't resolvable
    if "@db:" in url:
        # Check if we are inside docker by looking for common markers
        if not os.path.exists("/.dockerenv"):
            url = url.replace("@db:", "@localhost:")
    return url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import create_engine
    
    url = get_url()
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
