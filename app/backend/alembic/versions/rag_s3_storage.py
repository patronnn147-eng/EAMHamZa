"""Add s3_object_key column to documents table for RAG file storage in MinIO/S3

Revision ID: rag_s3_storage
Revises: p7_parts_demand_col
Create Date: 2026-05-30

Moves the RAG document blob from in-memory-only to S3-backed.
The `documents` table keeps metadata + new `s3_object_key` pointer.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rag_s3_storage"
down_revision: Union[str, Sequence[str], None] = "p7_parts_demand_col"
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
    if not _column_exists("documents", "s3_object_key"):
        op.add_column(
            "documents",
            sa.Column("s3_object_key", sa.String(512), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("documents", "s3_object_key")
