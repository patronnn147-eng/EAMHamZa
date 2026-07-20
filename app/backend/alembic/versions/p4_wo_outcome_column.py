"""Add P4 flag-to-outcome tracking column to ml_prediction_logs

Revision ID: p4_wo_outcome_column
Revises: telemetry_synthetic_flag
Create Date: 2026-07-19

Phase 4.3 (P1-P7 roadmap): P4's technician adjudication (p4_anomaly_adjudication
migration) captures manual review of a flag. This adds the automated
counterpart — did a real work order actually follow this flag within N days.
Mirrors the p7_parts_demand pattern: extend the same shadow-log row that made
the prediction rather than fork a parallel table. Written by
modules/ml/services/p4_feedback.py at intervention completion, read back by a
future Phase 5 precision/recall@k backtest.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p4_wo_outcome_column"
down_revision: Union[str, Sequence[str], None] = "telemetry_synthetic_flag"
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
    table = "ml_prediction_logs"
    if not _column_exists(table, "p4_wo_outcome"):
        op.add_column(
            table,
            sa.Column("p4_wo_outcome", sa.Text(), nullable=True),
        )  # JSON: {flag_preceded_wo, intervention_id, days_between, window_days}


def downgrade() -> None:
    op.drop_column("ml_prediction_logs", "p4_wo_outcome")
