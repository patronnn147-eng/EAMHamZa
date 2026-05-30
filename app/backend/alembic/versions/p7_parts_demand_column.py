"""Add p7_parts_demand JSON column to ml_prediction_logs

Revision ID: p7_parts_demand_col
Revises: add_health_snapshots
Create Date: 2026-05-30

Mirrors the p2_failure_types pattern: stored as JSON-encoded Text.
Guard with _column_exists so the migration is idempotent.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p7_parts_demand_col"
down_revision: Union[str, Sequence[str], None] = "add_health_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _column_exists("ml_prediction_logs", "p7_parts_demand"):
        op.add_column(
            "ml_prediction_logs",
            sa.Column("p7_parts_demand", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("ml_prediction_logs", "p7_parts_demand")
