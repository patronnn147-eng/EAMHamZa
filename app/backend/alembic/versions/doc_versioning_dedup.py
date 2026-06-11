"""Add content_hash and version columns to documents for dedup support.

content_hash: sha256 hex digest of the raw file bytes. UNIQUE — DB-level dedup guard.
              NULL allowed for documents ingested before this migration.
version: integer counter, starts at 1, incremented on each PUT replace.

Revision ID: doc_versioning_dedup
Revises: hybrid_search_tsvector
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "doc_versioning_dedup"
down_revision: Union[str, Sequence[str], None] = "hybrid_search_tsvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table_name, "c": column_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _column_exists("documents", "content_hash"):
        op.add_column(
            "documents",
            sa.Column("content_hash", sa.String(64), nullable=True),
        )
        # UNIQUE index allows multiple NULLs (pre-migration rows)
        op.create_index(
            "uq_documents_content_hash",
            "documents",
            ["content_hash"],
            unique=True,
            postgresql_where=sa.text("content_hash IS NOT NULL"),
        )

    if not _column_exists("documents", "version"):
        op.add_column(
            "documents",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    op.drop_index("uq_documents_content_hash", table_name="documents")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "version")
