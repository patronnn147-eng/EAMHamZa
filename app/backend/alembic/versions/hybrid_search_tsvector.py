"""Phase 13.1 hybrid search — add two GENERATED tsvector columns + GIN indexes on doc_chunks.

French + english stemming. Backfill is automatic via GENERATED ALWAYS — Postgres
evaluates the expression for every existing row at column-add time. No changes to
the ingestor required.

Locks: ACCESS EXCLUSIVE during ADD COLUMN rewrite (~few seconds at current scale,
~5000 chunks). CREATE INDEX (non-CONCURRENT) holds a SHARE lock — also short at
this scale. CREATE INDEX CONCURRENTLY is NOT used because Alembic wraps upgrades
in a transaction and CIC is not transactional. Accepted tradeoff at this scale.

Safety: SET lock_timeout = '30s' guards against indefinite blocking; if the lock
can't be acquired in 30s we fail loud rather than stalling other sessions.

Revision ID: hybrid_search_tsvector
Revises: chat_sessions_multi
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa

revision = "hybrid_search_tsvector"
down_revision = "chat_sessions_multi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fail loud if we can't get the ACCESS EXCLUSIVE lock in 30s rather than
    # blocking writers indefinitely (per RESEARCH §3.E mitigation).
    op.execute(sa.text("SET lock_timeout = '30s'"))

    # Each ADD COLUMN GENERATED rewrites the table once and backfills every row
    # automatically. Two separate statements so failures are easier to localize.
    op.execute(sa.text(
        "ALTER TABLE doc_chunks "
        "ADD COLUMN content_tsv_fr tsvector "
        "GENERATED ALWAYS AS (to_tsvector('french', content)) STORED"
    ))
    op.execute(sa.text(
        "ALTER TABLE doc_chunks "
        "ADD COLUMN content_tsv_en tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    ))

    # GIN indexes for fast @@ tsquery matching. Non-CONCURRENT on purpose
    # (Alembic transaction wrapping). At ~5000 rows this is ~1s blocking.
    op.execute(sa.text(
        "CREATE INDEX doc_chunks_tsv_fr_idx "
        "ON doc_chunks USING GIN (content_tsv_fr)"
    ))
    op.execute(sa.text(
        "CREATE INDEX doc_chunks_tsv_en_idx "
        "ON doc_chunks USING GIN (content_tsv_en)"
    ))

    # Reset lock_timeout for the rest of the session.
    op.execute(sa.text("SET lock_timeout = '0'"))


def downgrade() -> None:
    # Reverse order: drop indexes first, then columns.
    op.execute(sa.text("DROP INDEX IF EXISTS doc_chunks_tsv_en_idx"))
    op.execute(sa.text("DROP INDEX IF EXISTS doc_chunks_tsv_fr_idx"))
    op.execute(sa.text("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS content_tsv_en"))
    op.execute(sa.text("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS content_tsv_fr"))
