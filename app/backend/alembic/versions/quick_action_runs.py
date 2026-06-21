"""Create quick_action_runs idempotency table

Revision ID: quick_action_runs
Revises: doc_versioning_dedup
Create Date: 2026-06-13

Idempotent guard via information_schema (mirrors p7_parts_demand_column.py).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "quick_action_runs"
down_revision: Union[str, Sequence[str], None] = "doc_versioning_dedup"
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
    if _table_exists("quick_action_runs"):
        return
    op.create_table(
        "quick_action_runs",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_quick_action_runs_hash", "quick_action_runs", ["hash"]
    )
    op.create_index(
        "ix_quick_action_runs_machine_id", "quick_action_runs", ["machine_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_quick_action_runs_machine_id", table_name="quick_action_runs")
    op.drop_constraint("uq_quick_action_runs_hash", "quick_action_runs", type_="unique")
    op.drop_table("quick_action_runs")
