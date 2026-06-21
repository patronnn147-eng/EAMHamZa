"""Add planning_machines table for multi-machine selection in planning

Revision ID: planning_machines_multi_select
Revises: phase1_work_orders_interventions
Create Date: 2026-02-10

"""

from alembic import op
import sqlalchemy as sa


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


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE indexname = :index_name
            """
        ),
        {"index_name": index_name},
    )
    return result.first() is not None


# revision identifiers, used by Alembic.
revision = "planning_machines_multi_select"
down_revision = "phase1_work_orders_interventions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _table_exists("planning_machines"):
        op.create_table(
            "planning_machines",
            sa.Column(
                "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
            ),
            sa.Column("planning_id", sa.Integer(), nullable=False),
            sa.Column("machine_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _index_exists("ix_planning_machines_planning_id"):
        op.create_index(
            "ix_planning_machines_planning_id",
            "planning_machines",
            ["planning_id"],
            unique=False,
        )
    if not _index_exists("ix_planning_machines_machine_id"):
        op.create_index(
            "ix_planning_machines_machine_id",
            "planning_machines",
            ["machine_id"],
            unique=False,
        )

    op.create_unique_constraint(
        "uq_planning_machines_planning_machine",
        "planning_machines",
        ["planning_id", "machine_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_planning_machines_planning_machine", "planning_machines", type_="unique"
    )
    op.drop_index("ix_planning_machines_machine_id", table_name="planning_machines")
    op.drop_index("ix_planning_machines_planning_id", table_name="planning_machines")
    op.drop_table("planning_machines")
