"""Add chat_sessions table — DB-backed conversation history

Revision ID: add_chat_sessions
Revises: add_ai_memories
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_chat_sessions"
down_revision = "add_planning_tache_statut"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "utilisateur_id",
            sa.Integer(),
            sa.ForeignKey("utilisateurs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "messages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("last_query", sa.Text(), nullable=True),
        sa.Column("message_count", sa.Integer(), server_default="0"),
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
        "ix_chat_sessions_user_updated",
        "chat_sessions",
        ["utilisateur_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_user_updated", table_name="chat_sessions")
    op.drop_table("chat_sessions")
