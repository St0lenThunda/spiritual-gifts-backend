"""add_role_column

Revision ID: e23de9ac059d
Revises: 5a42da649428
Create Date: 2025-12-21 11:34:27.393725

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e23de9ac059d"
down_revision: Union[str, Sequence[str], None] = "5a42da649428"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add column as nullable
    op.add_column("users", sa.Column("role", sa.String(), nullable=True))
    
    # 2. Update existing rows to "user"
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    
    # 3. Alter column to be non-nullable
    op.alter_column("users", "role", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "role")
