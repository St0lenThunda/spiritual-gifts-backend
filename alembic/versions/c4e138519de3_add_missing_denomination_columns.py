"""add_missing_denomination_columns

Revision ID: c4e138519de3
Revises: 5a3d1d8d8492
Create Date: 2025-12-31 18:26:43.919431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e138519de3'
down_revision: Union[str, Sequence[str], None] = '5a3d1d8d8492'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('denominations', sa.Column('active_gift_keys', sa.JSON(), nullable=True))
    op.add_column('denominations', sa.Column('pastoral_overlays', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('denominations', 'pastoral_overlays')
    op.drop_column('denominations', 'active_gift_keys')
