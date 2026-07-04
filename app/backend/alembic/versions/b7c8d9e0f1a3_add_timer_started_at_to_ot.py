"""add_timer_started_at_to_ot

Revision ID: b7c8d9e0f1a3
Revises: a1b2c3d4e5f6
Create Date: 2026-03-27 12:45:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a3"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    # nosemgrep: sqlalchemy-raw-sql-interpolation,python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text -- table_name/column_name are hardcoded migration-author literals, never user input
    result = bind.execute(sa.text(f"SELECT 1 FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = '{column_name}'"))  # fmt: skip
    return result.first() is not None


def upgrade() -> None:
    # --- Ordres_travail ---
    if not _column_exists("ordres_travail", "timer_started_at"):
        op.add_column(
            "ordres_travail",
            sa.Column("timer_started_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    # --- Ordres_travail ---
    op.drop_column("ordres_travail", "timer_started_at")
