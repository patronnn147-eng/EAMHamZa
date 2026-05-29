"""Universal soft-archive columns across date-based modules

Revision ID: universal_archive_columns
Revises: inventory_stock_decimal
Create Date: 2026-05-18

Adds `archived_at` + `archive_reason` columns to:
- planning_taches
- ordres_travail
- ordres_intervention
- plannings

Soft-archive design — archived rows stay in their original table with a
non-null `archived_at`. Active queries filter `WHERE archived_at IS NULL`.
Partial index on `archived_at IS NULL` keeps active scans fast.
"""
from alembic import op
import sqlalchemy as sa


revision = "universal_archive_columns"
down_revision = "inventory_stock_decimal"
branch_labels = None
depends_on = None


TABLES = ["planning_taches", "ordres_travail", "ordres_intervention", "plannings"]


def upgrade() -> None:
    for tbl in TABLES:
        op.add_column(tbl, sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(tbl, sa.Column("archive_reason", sa.String(50), nullable=True))
        # Partial index: only rows where archived_at is NULL — fast for active queries
        op.create_index(
            f"idx_{tbl}_active",
            tbl,
            ["id"],
            postgresql_where=sa.text("archived_at IS NULL"),
        )
        # Lookup index for archive page queries (date-ordered)
        op.create_index(
            f"idx_{tbl}_archived",
            tbl,
            [sa.text("archived_at DESC")],
            postgresql_where=sa.text("archived_at IS NOT NULL"),
        )

    # CHECK constraints — valid archive reasons
    for tbl in TABLES:
        op.create_check_constraint(
            f"ck_{tbl}_archive_reason_valid",
            tbl,
            "archive_reason IS NULL OR archive_reason IN ('PAST_DUE_DATE', 'COMPLETED', 'MANUAL')",
        )


def downgrade() -> None:
    for tbl in TABLES:
        op.drop_constraint(f"ck_{tbl}_archive_reason_valid", tbl, type_="check")
        op.drop_index(f"idx_{tbl}_archived", table_name=tbl)
        op.drop_index(f"idx_{tbl}_active", table_name=tbl)
        op.drop_column(tbl, "archive_reason")
        op.drop_column(tbl, "archived_at")
