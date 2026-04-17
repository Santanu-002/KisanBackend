"""standardize_user_role_case

Revision ID: 922be1c8466e
Revises: 96d91b0b6750
Create Date: 2026-04-11 02:40:12.302578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '922be1c8466e'
down_revision: Union[str, Sequence[str], None] = '96d91b0b6750'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ensure values in existing data reflect the case change if needed
    # However, since these are Enum labels, renaming the label affects the stored representation
    op.execute("ALTER TYPE userrole RENAME VALUE 'admin' TO 'ADMIN'")
    op.execute("ALTER TYPE userrole RENAME VALUE 'farmer' TO 'FARMER'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE userrole RENAME VALUE 'ADMIN' TO 'admin'")
    op.execute("ALTER TYPE userrole RENAME VALUE 'FARMER' TO 'farmer'")
