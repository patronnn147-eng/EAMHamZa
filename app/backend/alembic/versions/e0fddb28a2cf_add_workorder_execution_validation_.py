"""Add WorkOrder execution validation fields

Revision ID: e0fddb28a2cf
Revises: add_machine_telemetry_columns
Create Date: 2026-03-24 11:22:01.543007

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e0fddb28a2cf"
down_revision: Union[str, Sequence[str], None] = "add_machine_telemetry_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only add the columns required for the technician work order execution lifecycle
    op.add_column(
        "ordres_travail",
        sa.Column("date_debut", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ordres_travail",
        sa.Column("date_fin", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("ordres_travail", sa.Column("rapport", sa.Text(), nullable=True))
    op.add_column(
        "ordres_travail",
        sa.Column("failure_type", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("ordres_travail", "failure_type")
    op.drop_column("ordres_travail", "rapport")
    op.drop_column("ordres_travail", "date_fin")
    op.drop_column("ordres_travail", "date_debut")
