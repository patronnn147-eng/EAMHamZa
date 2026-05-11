"""Enable pgvector and create RAG tables

Revision ID: add_pgvector_rag
Revises: add_chat_sessions
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_pgvector_rag"
down_revision = "add_chat_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MUST be first — vector type must exist before any vector column
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),  # manual|sop|report
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "machine_id",
            sa.Integer(),
            sa.ForeignKey("machines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by",
            sa.Integer(),
            sa.ForeignKey("utilisateurs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_documents_machine_id", "documents", ["machine_id"])

    # Create doc_chunks with TEXT embedding column first, then alter to vector(384)
    # Avoids SQLAlchemy not knowing the vector type at create_table time
    op.create_table(
        "doc_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "doc_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),  # temp text, altered below
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_doc_chunks_doc_id", "doc_chunks", ["doc_id"])

    # Alter embedding column to vector(384)
    op.execute(
        "ALTER TABLE doc_chunks ALTER COLUMN embedding TYPE vector(384) "
        "USING embedding::vector(384)"
    )

    # ivfflat ANN index — cosine ops, lists=100 good for <1M vectors
    op.execute("""
        CREATE INDEX ix_doc_chunks_embedding
        ON doc_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_doc_chunks_embedding")
    op.drop_index("ix_doc_chunks_doc_id", table_name="doc_chunks")
    op.drop_table("doc_chunks")
    op.drop_index("ix_documents_machine_id", table_name="documents")
    op.drop_table("documents")
    # Do NOT drop vector extension — may be used by other things
