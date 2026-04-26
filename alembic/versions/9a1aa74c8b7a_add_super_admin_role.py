"""add_super_admin_role

Revision ID: 9a1aa74c8b7a
Revises: 602527b6291c
Create Date: 2026-04-26 09:14:45.520192

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1aa74c8b7a'
down_revision: Union[str, Sequence[str], None] = '602527b6291c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
