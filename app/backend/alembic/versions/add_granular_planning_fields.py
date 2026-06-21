"""Add sous_zone and ordre to plannings

Revision ID: add_granular_planning_fields
Revises: interventions_approval_workflow
Create Date: 2026-02-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_granular_planning_fields"
down_revision: Union[str, Sequence[str], None] = "interventions_approval_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adding columns directly without existence check to avoid bind.execute issues in async env
    op.add_column(
        "plannings", sa.Column("sous_zone", sa.String(length=100), nullable=True)
    )
    op.add_column("plannings", sa.Column("ordre", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("plannings", "ordre")
    op.drop_column("plannings", "sous_zone")
