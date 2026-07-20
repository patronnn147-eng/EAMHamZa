"""One-off: invoke the same retraining pipeline the /api/v1/ml/retrain endpoint calls."""
import asyncio
import json
import logging

from core.database import db_manager
from modules.ml.services.ml_retraining import RetrainingService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main():
    await db_manager.init_db()
    async with db_manager.async_session_maker() as db:
        result = await RetrainingService.run_retraining_pipeline(db)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
