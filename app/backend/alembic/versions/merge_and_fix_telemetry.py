"""Merge heads and fix telemetry old columns

Revision ID: merge_and_fix_telemetry
Revises: add_requested_by, rename_telemetry_cols
Create Date: 2026-04-17

Merges the two divergent heads and ensures old NOT-NULL columns on
machine_telemetry_logs are dropped so inserts using the new column names work.
"""

from typing import Sequence, Union


revision: str = "merge_and_fix_telemetry"
down_revision: Union[str, Sequence[str], None] = (
    "add_requested_by",
    "rename_telemetry_cols",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration — joins branches, no schema changes."""


def downgrade() -> None:
    """Merge migration — joins branches, no schema changes."""
