"""Upgrade doc_chunks embedding column from vector(384) to vector(1024) for BAAI/bge-m3

Revision ID: upgrade_embedding_dim_1024
Revises: rag_s3_storage
Create Date: 2026-06-01

NOTE: Existing doc_chunks rows are deleted before altering the column type.
      Old 384-dim vectors are incompatible with 1024-dim — re-ingest all documents after
      running this migration.
"""

from alembic import op

revision = "upgrade_embedding_dim_1024"
down_revision = "rag_s3_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop all existing chunks — 384-dim vectors cannot be cast to 1024-dim.
    # Documents table rows are kept; only chunk embeddings are wiped.
    op.execute("DELETE FROM doc_chunks")

    # Alter column type
    op.execute(
        "ALTER TABLE doc_chunks "
        "ALTER COLUMN embedding TYPE vector(1024) "
        "USING embedding::text::vector(1024)"
    )

    # Rebuild the cosine similarity index for new dimension
    op.execute("DROP INDEX IF EXISTS doc_chunks_embedding_idx")
    op.execute(
        "CREATE INDEX doc_chunks_embedding_idx "
        "ON doc_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM doc_chunks")
    op.execute(
        "ALTER TABLE doc_chunks "
        "ALTER COLUMN embedding TYPE vector(384) "
        "USING embedding::text::vector(384)"
    )
    op.execute("DROP INDEX IF EXISTS doc_chunks_embedding_idx")
    op.execute(
        "CREATE INDEX doc_chunks_embedding_idx "
        "ON doc_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
