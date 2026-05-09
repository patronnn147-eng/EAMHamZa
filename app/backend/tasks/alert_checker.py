from __future__ import annotations

import asyncio
import logging
import sys
import os

# ForkPoolWorkers may inherit a cwd-relative '' path that resolves differently
# from the main process. Ensure /app is on sys.path so modules.* imports work.
_app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from core.celery_app import celery_app
from core.database import db_manager
from models.alertes import Alert  # noqa: F401 — registers Alert mapper for string relationships
from models.machines import Machines  # noqa: F401 — registers Machines mapper

logger = logging.getLogger(__name__)


async def run_alert_check() -> dict:
    # Each asyncio.run() creates a new event loop. The db_manager singleton
    # caches its async engine + asyncio.Lock() bound to the *first* loop.
    # Fully close and reset before reinitialising so a fresh engine and lock
    # are created for the current loop, avoiding
    # "Future attached to a different loop" errors.
    await db_manager.close_db()
    # _init_lock was created inside the previous loop — replace it.
    db_manager._init_lock = asyncio.Lock()
    db_manager._table_creation_lock = asyncio.Lock()
    await db_manager.init_db()
    async with db_manager.async_session_maker() as session:
        from services.alertes import AlertService
        service = AlertService(session)
        return await service.check_and_create_alerts()


@celery_app.task(name="tasks.check_predictive_alerts")
def check_predictive_alerts():
    logger.info("Starting predictive alert check task...")
    try:
        result = asyncio.run(run_alert_check())
        logger.info(f"Alert check complete: {result}")
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Error in check_predictive_alerts: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
