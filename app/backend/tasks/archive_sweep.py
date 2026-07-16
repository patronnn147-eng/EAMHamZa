"""Celery tasks for the universal archive lifecycle.

- `tasks.archive_past_due` — hourly: sweep past-due / terminal-status rows
  across PlanningTaches, OrdresTravail, OrdresIntervention, plannings.
- `tasks.purge_archive_old` — weekly: hard-delete rows whose `archived_at`
  is older than the retention window (default 30 days).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.archive_past_due", bind=True, max_retries=2, default_retry_delay=300
)
def archive_past_due(self) -> Dict[str, Any]:
    try:
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(_archive_run())
            return {"status": "ok", "archived": results}
        finally:
            loop.close()
    except Exception as exc:
        logger.exception(f"archive_past_due failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name="tasks.purge_archive_old", bind=True, max_retries=1, default_retry_delay=600
)
def purge_archive_old(self) -> Dict[str, Any]:
    days = int(os.getenv("ARCHIVE_RETENTION_DAYS", "30"))
    try:
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(_purge_run(days))
            return {"status": "ok", "purged": results, "retention_days": days}
        finally:
            loop.close()
    except Exception as exc:
        logger.exception(f"purge_archive_old failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# ─── Async helpers ──────────────────────────────────────────────────────


async def _archive_run() -> Dict[str, int]:
    from core.database import db_manager
    from services.archive import ArchiveService

    if not db_manager._initialized:  # type: ignore[attr-defined]
        await db_manager.initialize_tables()
    async with db_manager.async_session_maker() as session:
        svc = ArchiveService(session)
        return await svc.archive_past_due(auto_commit=True)


async def _purge_run(days: int) -> Dict[str, int]:
    from core.database import db_manager
    from services.archive import ArchiveService

    if not db_manager._initialized:  # type: ignore[attr-defined]
        await db_manager.initialize_tables()
    async with db_manager.async_session_maker() as session:
        svc = ArchiveService(session)
        return await svc.purge_old(retention_days=days, auto_commit=True)
