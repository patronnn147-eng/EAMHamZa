"""Extend is_synthetic quarantine to machine_telemetry_logs and ml_prediction_logs

Revision ID: telemetry_synthetic_flag
Revises: p4_anomaly_adjudication
Create Date: 2026-07-19

OrdresIntervention_is_synthetic only flagged the intervention/label side.
seed_ml_data_all.py also writes MachineTelemetry and MlPredictionLog rows
directly (its own sensor snapshots + a wear-threshold-derived is_anomaly/
anomaly_score, same tautology family as the label formulas) — neither
had a way to be excluded. That gap was live in production: the P4
anomaly-review queue (built this session) was pulling from
ml_prediction_logs with no synthetic filter, so a technician reviewing
"flagged anomalies" could have been confirming/dismissing fake
seed-generated wear>180 triggers rather than real ensemble-model output.

Backfill: MachineTelemetry rows are identifiable directly via the
notes field seed_ml_data_all.py sets ('Seed C%'). MlPredictionLog rows
have no such marker of their own, but seed_ml_data_all.py sets
created_at to the exact same recorded_at timestamp as the paired
telemetry row for the same machine_id in the same loop iteration, so
they're identifiable via that exact (machine_id, created_at) join.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "telemetry_synthetic_flag"
down_revision: Union[str, Sequence[str], None] = "p4_anomaly_adjudication"
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
    if not _column_exists("machine_telemetry_logs", "is_synthetic"):
        op.add_column(
            "machine_telemetry_logs",
            sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _column_exists("ml_prediction_logs", "is_synthetic"):
        op.add_column(
            "ml_prediction_logs",
            sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    op.execute(
        sa.text(
            """
            UPDATE machine_telemetry_logs
            SET is_synthetic = TRUE
            WHERE notes LIKE 'Seed %'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ml_prediction_logs AS pl
            SET is_synthetic = TRUE
            FROM machine_telemetry_logs AS mt
            WHERE mt.is_synthetic = TRUE
              AND mt.machine_id = pl.machine_id
              AND mt.recorded_at = pl.created_at
            """
        )
    )


def downgrade() -> None:
    op.drop_column("ml_prediction_logs", "is_synthetic")
    op.drop_column("machine_telemetry_logs", "is_synthetic")
