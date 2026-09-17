"""add planning_machines machine_id index

Revision ID: add_plannings_idx
Revises: new_perf_indexes
Create Date: 2026-04-03 14:35:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "add_plannings_idx"
down_revision: Union[str, None] = "new_perf_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_planning_machines_machine_id", "planning_machines", ["machine_id"]
    )
    op.create_index(
        "idx_planning_machines_planning_id", "planning_machines", ["planning_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_planning_machines_planning_id", table_name="planning_machines")
    op.drop_index("idx_planning_machines_machine_id", table_name="planning_machines")
