"""Add ai_memories table for dynamic LLM user memory

Revision ID: add_ai_memories
Revises: merge_all_heads_final
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_ai_memories"
down_revision = "merge_all_heads_final"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS because the table may already exist in production DBs
    # (created by SQLAlchemy models before migrations were set up).
    if not op.get_context().bind.dialect.has_table(
        op.get_context().bind, "ai_memories"
    ):
        op.create_table(
            "ai_memories",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "utilisateur_id",
                sa.Integer(),
                sa.ForeignKey("utilisateurs.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("memory_type", sa.String(50), nullable=False),
            sa.Column("memory_key", sa.String(255), nullable=False),
            sa.Column("memory_value", sa.Text(), nullable=False),
            sa.Column("success_count", sa.Integer(), server_default="0"),
            sa.Column("failure_count", sa.Integer(), server_default="0"),
            sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_ai_memories_user_type", "ai_memories", ["utilisateur_id", "memory_type"]
        )


def downgrade() -> None:
    op.drop_index("ix_ai_memories_user_type", table_name="ai_memories")
    op.drop_table("ai_memories")
