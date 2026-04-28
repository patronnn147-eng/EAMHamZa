"""Add planning_id to intervention model for Phase 2

Revision ID: phase2_intervention_planning
Revises: interventions_approval_workflow
Create Date: 2026-04-28

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


revision: str = "phase2_intervention_planning"
down_revision: Union[str, Sequence[str], None] = "interventions_approval_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add planning_id column to link interventions to plannings."""
    if not _column_exists("ordres_intervention", "planning_id"):
        op.add_column(
            "ordres_intervention",
            sa.Column("planning_id", sa.Integer(), nullable=True),
        )
        # Create index for faster queries
        op.create_index(
            "ix_ordres_intervention_planning_id",
            "ordres_intervention",
            ["planning_id"],
            unique=False,
        )
        # Add foreign key constraint (optional, will fail gracefully if plannings table doesn't exist)
        try:
            op.create_foreign_key(
                "fk_ordres_intervention_planning_id",
                "ordres_intervention",
                "plannings",
                ["planning_id"],
                ["id"],
            )
        except Exception:
            # Foreign key might fail if constraint name conflicts - continue anyway
            pass


def downgrade() -> None:
    """Remove planning_id column."""
    op.drop_index(
        "ix_ordres_intervention_planning_id",
        table_name="ordres_intervention",
    )
    op.drop_column("ordres_intervention", "planning_id")