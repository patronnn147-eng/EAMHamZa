"""Add health score snapshot columns to OrdresTravail

Adds two nullable Float columns to support post-maintenance recovery tracking:
  - health_score_at_creation: unified_health_score at WO creation time
  - health_score_at_completion: unified_health_score just before WO completion

These snapshots enable the Post-Maintenance Recovery feature, which computes
the delta between current unified_health_score and the pre-maintenance baseline
to classify a machine as Recovered / Recovering / No improvement.

Revision ID: add_health_snapshots
Revises: universal_archive_columns
Create Date: 2026-05-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "add_health_snapshots"
down_revision: Union[str, Sequence[str], None] = "universal_archive_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _column_exists("OrdresTravail", "health_score_at_creation"):
        op.add_column(
            "OrdresTravail",
            sa.Column("health_score_at_creation", sa.Float(), nullable=True),
        )
    if not _column_exists("OrdresTravail", "health_score_at_completion"):
        op.add_column(
            "OrdresTravail",
            sa.Column("health_score_at_completion", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("OrdresTravail", "health_score_at_completion")
    op.drop_column("OrdresTravail", "health_score_at_creation")
