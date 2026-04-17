"""Change OWNER to ADMIN role

Revision ID: 96d91b0b6750
Revises: 24ef5172cbf0
Create Date: 2026-04-10 16:21:38.290709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96d91b0b6750'
down_revision: Union[str, Sequence[str], None] = '24ef5172cbf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT 1 FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname = 'userrole' AND enumlabel = 'owner'"))
    if result.scalar():
        op.execute("ALTER TYPE userrole RENAME VALUE 'owner' TO 'admin'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE userrole RENAME VALUE 'admin' TO 'owner'")
