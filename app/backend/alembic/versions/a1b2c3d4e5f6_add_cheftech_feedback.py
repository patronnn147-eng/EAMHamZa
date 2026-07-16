"""Add cheftech_feedback column to OrdresTravail

Revision ID: a1b2c3d4e5f6
Revises: e0fddb28a2cf
Create Date: 2026-03-24 12:38:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e0fddb28a2cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cheftech_feedback text column."""
    op.add_column(
        "OrdresTravail", sa.Column("cheftech_feedback", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove cheftech_feedback column."""
    op.drop_column("OrdresTravail", "cheftech_feedback")
