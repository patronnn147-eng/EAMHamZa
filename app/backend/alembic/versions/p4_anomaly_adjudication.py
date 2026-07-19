"""Add P4 anomaly-flag adjudication columns to ml_prediction_logs

Revision ID: p4_anomaly_adjudication
Revises: OrdresIntervention_is_synthetic
Create Date: 2026-07-19

P4 (Behavioral Anomaly) is unsupervised — there has never been a way to
know if a flag was real. ml_prediction_logs already records is_anomaly/
anomaly_score/sensor-snapshot on every prediction call, so rather than a
new table (which would just duplicate the flag side), this extends the
same row with the technician-adjudication side: was this flag real, and
what caused it. Mirrors the existing p7_parts_demand column pattern
(extend the shadow-log row, don't fork a parallel table).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p4_anomaly_adjudication"
down_revision: Union[str, Sequence[str], None] = "OrdresIntervention_is_synthetic"
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
    if not _column_exists(table, "anomaly_verdict"):
        op.add_column(
            table,
            sa.Column("anomaly_verdict", sa.String(30), nullable=True),
        )  # CONFIRMED / FALSE_POSITIVE / BENIGN_TRANSIENT
    if not _column_exists(table, "anomaly_root_cause"):
        op.add_column(
            table,
            sa.Column("anomaly_root_cause", sa.Text(), nullable=True),
        )
    if not _column_exists(table, "anomaly_reviewed_by"):
        op.add_column(
            table,
            sa.Column("anomaly_reviewed_by", sa.Integer(), nullable=True),
        )
    if not _column_exists(table, "anomaly_reviewed_at"):
        op.add_column(
            table,
            sa.Column("anomaly_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    table = "ml_prediction_logs"
    op.drop_column(table, "anomaly_reviewed_at")
    op.drop_column(table, "anomaly_reviewed_by")
    op.drop_column(table, "anomaly_root_cause")
    op.drop_column(table, "anomaly_verdict")
