"""add discernment to survey

Revision ID: 0c90da49f79c
Revises: 748d45abbe8a
Create Date: 2025-12-26 02:09:52.788760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c90da49f79c'
down_revision: Union[str, Sequence[str], None] = '748d45abbe8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('surveys', sa.Column('discernment', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('surveys', 'discernment')
