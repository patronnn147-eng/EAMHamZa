"""Add title column to chat_sessions for multi-conversation support

Revision ID: chat_sessions_multi
Revises: upgrade_embedding_dim_1024
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision = "chat_sessions_multi"
down_revision = "upgrade_embedding_dim_1024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("title", sa.String(length=200), nullable=True),
    )
    # Initial title for legacy single-session-per-user rows
    op.execute("UPDATE chat_sessions SET title = 'Conversation' WHERE title IS NULL")


def downgrade() -> None:
    op.drop_column("chat_sessions", "title")
