"""Add PDCA ML prediction logs table and feedback columns

Revision ID: add_pdca_ml_tables
Revises: interventions_approval_workflow
Create Date: 2026-03-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


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


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return result.first() is not None


revision: str = "add_pdca_ml_tables"
down_revision: Union[str, Sequence[str], None] = "add_granular_planning_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ml_prediction_logs table (PDCA Shadow Logging)
    if not _table_exists("ml_prediction_logs"):
        op.create_table(
            "ml_prediction_logs",
            sa.Column(
                "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
            ),
            sa.Column("machine_id", sa.Integer(), nullable=False, index=True),
            sa.Column("machine_name", sa.String(), nullable=True),
            sa.Column("risk_level", sa.String(20), nullable=True),
            sa.Column("failure_probability", sa.Float(), nullable=True),
            sa.Column("rul_days", sa.Float(), nullable=True),
            sa.Column("predicted_failure_date", sa.String(), nullable=True),
            sa.Column("predicted_priority", sa.String(20), nullable=True),
            sa.Column(
                "is_anomaly", sa.Boolean(), nullable=True, server_default="false"
            ),
            sa.Column("anomaly_score", sa.Float(), nullable=True),
            sa.Column("p2_failure_types", sa.Text(), nullable=True),
            sa.Column("data_points", sa.Integer(), nullable=True),
            sa.Column(
                "ml_model_used", sa.Boolean(), nullable=True, server_default="false"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # 2. Add PDCA feedback columns to ordres_intervention
    if not _column_exists("ordres_intervention", "actual_failure_type"):
        op.add_column(
            "ordres_intervention",
            sa.Column("actual_failure_type", sa.String(20), nullable=True),
        )

    if not _column_exists("ordres_intervention", "ml_prediction_matched"):
        op.add_column(
            "ordres_intervention",
            sa.Column("ml_prediction_matched", sa.Boolean(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("ordres_intervention", "ml_prediction_matched")
    op.drop_column("ordres_intervention", "actual_failure_type")
    op.drop_table("ml_prediction_logs")
