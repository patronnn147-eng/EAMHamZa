"""Stub migration: restore add_ml_alert_details revision

Revision ID: add_ml_alert_details
Revises: merge_and_fix_telemetry
Create Date: 2026-04-24

This revision exists to match the current database alembic_version entry.
The migration file was deleted/lost while the database already recorded this
revision as its current head.  It is intentionally a no-op — all DDL changes
it originally contained have already been applied to the database.
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "add_ml_alert_details"
down_revision: Union[str, Sequence[str], None] = "merge_and_fix_telemetry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: the database is already at this revision.
    # The original DDL (ml alert detail columns) was applied directly to the DB
    # before this file was lost.  Adding a safe guard check prevents re-applying.
    pass


def downgrade() -> None:
    # No-op: cannot reliably reverse changes whose definition no longer exists.
    pass
