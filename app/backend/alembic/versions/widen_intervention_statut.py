"""widen OrdresIntervention.statut so CONVERTED_TO_WORKORDER fits

The workflow value written by
modules/shared/routes/intervention_workflow.py::create_work_order_from_intervention
is "CONVERTED_TO_WORKORDER" — 22 characters — but the column was VARCHAR(20).
Every call to that endpoint therefore failed with
asyncpg StringDataRightTruncationError, making "create work order from
intervention" unusable and leaving the intervention/work-order chain broken.

Widened to VARCHAR(32), which also leaves room for the rest of the vocabulary
(EN_ATTENTE / EN_COURS / TERMINÉ / BLOQUÉ / PENDING_APPROVAL / APPROVED /
DECLINED / PENDING / CONVERTED_TO_WORKORDER / VALIDATED).

Revision ID: widen_intervention_statut
Revises: utilisateur_zones
Create Date: 2026-08-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "widen_intervention_statut"
down_revision: Union[str, Sequence[str], None] = "utilisateur_zones"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _current_length() -> int | None:
    """Return the column's current character maximum length, or None if absent."""
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            "SELECT character_maximum_length FROM information_schema.columns "
            "WHERE table_name = 'OrdresIntervention' AND column_name = 'statut'"
        )
    ).first()
    return row[0] if row else None


def upgrade() -> None:
    current = _current_length()
    if current is None or current >= 32:
        return
    op.alter_column(
        "OrdresIntervention",
        "statut",
        existing_type=sa.String(length=current),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    current = _current_length()
    if current is None or current <= 20:
        return
    # Truncate any value that would not survive the narrower column, so the
    # downgrade cannot fail on existing rows.
    op.execute(
        'UPDATE "OrdresIntervention" SET statut = LEFT(statut, 20) '
        "WHERE LENGTH(statut) > 20"
    )
    op.alter_column(
        "OrdresIntervention",
        "statut",
        existing_type=sa.String(length=current),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
