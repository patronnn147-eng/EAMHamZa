"""Add intervention approval workflow fields

Revision ID: interventions_approval_workflow
Revises: planning_machines_multi_select
Create Date: 2026-02-13

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


revision: str = "interventions_approval_workflow"
down_revision: Union[str, Sequence[str], None] = "planning_machines_multi_select"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not _column_exists("ordres_intervention", "problem_description"):
        op.add_column(
            "ordres_intervention",
            sa.Column("problem_description", sa.Text(), nullable=True),
        )

    if not _column_exists("ordres_intervention", "priority"):
        op.add_column(
            "ordres_intervention",
            sa.Column("priority", sa.String(length=20), nullable=True),
        )

    if not _column_exists("ordres_intervention", "estimated_duration_minutes"):
        op.add_column(
            "ordres_intervention",
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        )

    if not _column_exists("ordres_intervention", "required_materials"):
        op.add_column(
            "ordres_intervention",
            sa.Column("required_materials", sa.Text(), nullable=True),
        )

    if not _column_exists("ordres_intervention", "machine_id"):
        op.add_column(
            "ordres_intervention", sa.Column("machine_id", sa.Integer(), nullable=True)
        )

    if not _column_exists("ordres_intervention", "requested_at"):
        op.add_column(
            "ordres_intervention",
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists("ordres_intervention", "approved_by"):
        op.add_column(
            "ordres_intervention", sa.Column("approved_by", sa.Integer(), nullable=True)
        )

    if not _column_exists("ordres_intervention", "approved_at"):
        op.add_column(
            "ordres_intervention",
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists("ordres_intervention", "rejection_reason"):
        op.add_column(
            "ordres_intervention",
            sa.Column("rejection_reason", sa.Text(), nullable=True),
        )

    idx_name = op.f("ix_ordres_intervention_statut")
    if not _index_exists(idx_name):
        op.create_index(idx_name, "ordres_intervention", ["statut"], unique=False)


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ordres_intervention_statut"), table_name="ordres_intervention"
    )

    op.drop_column("ordres_intervention", "rejection_reason")
    op.drop_column("ordres_intervention", "approved_at")
    op.drop_column("ordres_intervention", "approved_by")
    op.drop_column("ordres_intervention", "requested_at")
    op.drop_column("ordres_intervention", "machine_id")
    op.drop_column("ordres_intervention", "required_materials")
    op.drop_column("ordres_intervention", "estimated_duration_minutes")
    op.drop_column("ordres_intervention", "priority")
    op.drop_column("ordres_intervention", "problem_description")
