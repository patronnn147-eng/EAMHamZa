"""merge_phase2_and_base

Revision ID: 3d8edf736d26
Revises: add_ai_memories, phase2_intervention_planning
Create Date: 2026-04-28 20:44:25.998361

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "3d8edf736d26"
down_revision: Union[str, Sequence[str], None] = (
    "add_ai_memories",
    "phase2_intervention_planning",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
