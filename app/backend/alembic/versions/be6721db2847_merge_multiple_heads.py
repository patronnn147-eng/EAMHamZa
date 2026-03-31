"""merge multiple heads

Revision ID: be6721db2847
Revises: b9e76d0812f5, f44d6d0416f4
Create Date: 2026-03-29 14:04:16.154584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be6721db2847'
down_revision: Union[str, Sequence[str], None] = ('b9e76d0812f5', 'f44d6d0416f4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass