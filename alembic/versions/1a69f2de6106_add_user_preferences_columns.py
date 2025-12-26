"""add_user_preferences_columns

Revision ID: 1a69f2de6106
Revises: 0c90da49f79c
Create Date: 2025-12-26 12:00:47.803177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a69f2de6106'
down_revision: Union[str, Sequence[str], None] = '0c90da49f79c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add global_preferences column
    op.add_column('users', 
        sa.Column('global_preferences', 
                  sa.JSON(), 
                  nullable=True, 
                  server_default='{}'))
    
    # Add org_preferences column
    op.add_column('users', 
        sa.Column('org_preferences', 
                  sa.JSON(), 
                  nullable=True, 
                  server_default='{}'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'org_preferences')
    op.drop_column('users', 'global_preferences')
