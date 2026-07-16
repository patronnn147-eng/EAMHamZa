"""Bridge migration: fix_enhance_work_orders

Revision ID: fix_enhance_work_orders
Revises: update_OrdresTravail_chetop
Create Date: 2026-02-11

This revision exists to match the current database alembic_version.
It is intentionally a no-op and only restores a valid migration chain.

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "fix_enhance_work_orders"
down_revision: Union[str, Sequence[str], None] = "update_OrdresTravail_chetop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bridge migration — intentional no-op, see module docstring."""


def downgrade() -> None:
    """Bridge migration — intentional no-op, see module docstring."""
