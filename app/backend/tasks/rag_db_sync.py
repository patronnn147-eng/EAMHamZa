"""
Event-driven RAG sync tasks.

Two task types:
  - sync_row(table, row_id)  — re-ingest a single DB row into the KB
  - delete_row(table, row_id) — remove a row's docs (chunks + S3) from the KB

Triggered by SQLAlchemy after_commit hooks in `services/rag_change_hooks.py`.

Also keeps the full `sync_all` task available for manual/initial backfill
(e.g. `docker compose exec backend python scripts/sync_db_to_rag.py` is fine,
or call this task with `.delay()` for the same behavior).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Make /app importable inside ForkPoolWorker (same pattern as alert_checker)
_app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from core.celery_app import celery_app
from scripts.sync_db_to_rag import run_sync, sync_row, delete_row, TABLES

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.rag_sync_row",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def rag_sync_row(self, table: str, row_id: int):
    """Re-ingest a single DB row into the RAG KB. Fires after model commit."""
    logger.info(f"[rag_sync_row] {table}:{row_id}")
    result = asyncio.run(sync_row(table, row_id))
    if not result.get("ok"):
        logger.warning(f"[rag_sync_row] {table}:{row_id} → {result}")
    return result


@celery_app.task(
    name="tasks.rag_delete_row",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def rag_delete_row(self, table: str, row_id: int):
    """Delete a single row's docs from the RAG KB. Fires after model delete commit."""
    logger.info(f"[rag_delete_row] {table}:{row_id}")
    result = asyncio.run(delete_row(table, row_id))
    if not result.get("ok"):
        logger.warning(f"[rag_delete_row] {table}:{row_id} → {result}")
    return result


@celery_app.task(name="tasks.rag_sync_all", bind=True, max_retries=1)
def rag_sync_all(self, tables: list | None = None, delete_stale: bool = True):
    """
    Full backfill. Use for initial sync or after KB corruption.
    NOT scheduled — invoke manually via `.delay()` if needed.
    """
    logger.info(f"[rag_sync_all] tables={tables or 'ALL'} delete_stale={delete_stale}")
    result = asyncio.run(run_sync(tables=tables, delete_stale=delete_stale, dry_run=False))
    logger.info(f"[rag_sync_all] done — {result}")
    return result
