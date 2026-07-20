"""Create machine_status_change_requests table

Revision ID: machine_status_change_requests
Revises: p4_wo_outcome_column
Create Date: 2026-07-20

Idempotent guard via information_schema (mirrors quick_action_runs.py).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "machine_status_change_requests"
down_revision: Union[str, Sequence[str], None] = "p4_wo_outcome_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if _table_exists("machine_status_change_requests"):
        return
    op.create_table(
        "machine_status_change_requests",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=False),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="PENDING"
        ),
        sa.Column("source_intervention_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_machine_status_change_requests_machine_id",
        "machine_status_change_requests",
        ["machine_id"],
    )
    op.create_index(
        "ix_machine_status_change_requests_status",
        "machine_status_change_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_machine_status_change_requests_status",
        table_name="machine_status_change_requests",
    )
    op.drop_index(
        "ix_machine_status_change_requests_machine_id",
        table_name="machine_status_change_requests",
    )
    op.drop_table("machine_status_change_requests")
