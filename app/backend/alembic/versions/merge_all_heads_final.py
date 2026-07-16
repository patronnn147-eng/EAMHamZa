"""Merge all dangling heads into a single clean tip

Revision ID: merge_all_heads_final
Revises: fix_enhance_work_orders, add_granular_planning_fields, add_ml_alert_details
Create Date: 2026-04-24

This merge migration unifies the three divergent heads that existed in the
migration chain into a single, canonical head:

  - fix_enhance_work_orders       (no-op stub, branch off update_OrdresTravail_chetop)
  - add_granular_planning_fields  (adds sous_zone / ordre to plannings)
  - add_ml_alert_details          (no-op stub, restored from lost file)

After this migration the chain has exactly one head: merge_all_heads_final.
Running `alembic upgrade head` is safe from any of the three parent revisions.
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "merge_all_heads_final"
down_revision: Union[str, Sequence[str], None] = (
    "fix_enhance_work_orders",
    "add_granular_planning_fields",
    "add_ml_alert_details",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pure merge — no schema changes needed.
    # All DDL from the three parent branches has already been applied to the
    # database.  This revision simply records that every branch has been
    # reconciled so that future migrations have a single, unambiguous parent.
    pass


def downgrade() -> None:
    # Downgrading a merge revision is intentionally a no-op.
    # To roll back individual branch changes, downgrade to the specific
    # parent revision directly (e.g. `alembic downgrade add_ml_alert_details`).
    pass
