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

from core.celery_app import celery_app  # noqa: E402
from core.database import db_manager  # noqa: E402
from models.alertes import Alert  # noqa: E402,F401
from models.machines import Machines  # noqa: E402,F401

logger = logging.getLogger(__name__)


async def run_alert_check() -> dict:
    # Each asyncio.run() creates a new event loop. The db_manager singleton's
    # engine, pool (incl. its internal sync primitives), and pooled asyncpg
    # connections are all bound to whichever loop created them. They MUST be
    # disposed inside that same loop -- disposing from a later call, running
    # in a new loop, tries to close connections/primitives whose loop is
    # already closed, causing "Future attached to a different loop" /
    # "Event loop is closed". So: fresh locks + init at the START, and
    # dispose at the END, all within this one loop, before asyncio.run()
    # closes it.
    db_manager._init_lock = asyncio.Lock()
    db_manager._table_creation_lock = asyncio.Lock()
    await db_manager.init_db()
    try:
        async with db_manager.async_session_maker() as session:
            from services.alertes import AlertService

            service = AlertService(session)
            return await service.check_and_create_alerts()
    finally:
        await db_manager.close_db()


@celery_app.task(name="tasks.check_predictive_alerts")
def check_predictive_alerts():
    logger.info("Starting predictive alert check task...")
    try:
        result = asyncio.run(run_alert_check())
        logger.info(f"Alert check complete: {result}")
        return {"status": "success", **result}
    except Exception as e:
        logger.exception(f"Error in check_predictive_alerts: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
