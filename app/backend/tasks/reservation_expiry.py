"""Celery task: release expired inventory reservations.

Runs on a daily schedule (configured in core.celery_app). Walks every
required_pieces row with `reservation_expires_at < now()` and releases the
reservation back to available stock. Emits one MouvementStock
`RESERVATION_RELEASED` row per affected reservation for audit traceability.

Idempotent — re-running yields zero work after the first sweep.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.release_expired_reservations", bind=True, max_retries=2, default_retry_delay=300)
def release_expired_reservations(self) -> Dict[str, Any]:
    """Synchronous Celery entry point — bridges to async service call."""
    try:
        loop = asyncio.new_event_loop()
        try:
            count = loop.run_until_complete(_run_async())
            return {"status": "ok", "released": count}
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"release_expired_reservations failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


async def _run_async() -> int:
    # Local imports — keeps the worker import time low and avoids
    # circular initialization with the FastAPI app.
    from core.database import db_manager
    from services.inventory import InventoryReservationService

    # db_manager exposes session factory; obtain a fresh one
    if not db_manager._initialized:  # type: ignore[attr-defined]
        await db_manager.initialize_tables()

    async with db_manager.async_session_maker() as session:
        svc = InventoryReservationService(session)
        count = await svc.release_expired(auto_commit=True)
        if count:
            logger.warning(f"release_expired_reservations released {count} expired reservation(s)")
        return count
