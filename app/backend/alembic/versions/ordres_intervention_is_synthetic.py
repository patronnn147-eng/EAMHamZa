"""Add is_synthetic flag to OrdresIntervention to quarantine seed-generated rows

Revision ID: OrdresIntervention_is_synthetic
Revises: quick_action_runs
Create Date: 2026-07-19

seed_ml_data_all.py writes real OrdresIntervention rows (actual_failure_type,
priority, etc. all derived from a deterministic tool_wear-threshold formula)
directly into the same table real technician-confirmed interventions live in.
The ML retrain pipeline's "real ground truth" query currently can't tell
them apart, so seed rows silently poison what should be real-data training
for P1/P2/P5. This adds a queryable flag and backfills existing seed rows
(identified via their Plannings.identifiant_planning LIKE 'SEED-PLAN-%'
marker, which seed_ml_data_all.py sets on every synthetic cycle).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "OrdresIntervention_is_synthetic"
down_revision: Union[str, Sequence[str], None] = "quick_action_runs"
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
    if not _column_exists("OrdresIntervention", "is_synthetic"):
        op.add_column(
            "OrdresIntervention",
            sa.Column(
                "is_synthetic",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    op.execute(
        sa.text(
            """
            UPDATE "OrdresIntervention"
            SET is_synthetic = TRUE
            WHERE planning_id IN (
                SELECT id FROM plannings
                WHERE identifiant_planning LIKE 'SEED-PLAN-%'
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("OrdresIntervention", "is_synthetic")
