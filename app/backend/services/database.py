import logging
import time
from datetime import datetime

from core.database import db_manager
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Cache database health check (5 seconds)
_db_health_cache = {"healthy": False, "timestamp": None, "ttl_seconds": 5}


async def check_database_health() -> bool:
    """Check if database is healthy (cached for 5 seconds)"""
    now = datetime.utcnow()

    # Return cached result if fresh
    if (
        _db_health_cache["timestamp"] is not None
        and (now - _db_health_cache["timestamp"]).total_seconds()
        < _db_health_cache["ttl_seconds"]
    ):
        return _db_health_cache["healthy"]

    start_time = time.time()
    logger.debug("[DB_OP] Starting database health check")
    try:
        if not db_manager.async_session_maker:
            _db_health_cache["healthy"] = False
            _db_health_cache["timestamp"] = now
            return False

        async with db_manager.async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            healthy = True
            _db_health_cache["healthy"] = healthy
            _db_health_cache["timestamp"] = now
            logger.debug(
                f"[DB_OP] Database health check completed in {time.time() - start_time:.4f}s - healthy: True"
            )
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        logger.debug(
            f"[DB_OP] Database health check failed in {time.time() - start_time:.4f}s - healthy: False"
        )
        _db_health_cache["healthy"] = False
        _db_health_cache["timestamp"] = now
        return False


async def initialize_database():
    """Initialize database and create tables"""
    start_time = time.time()
    logger.debug("[DB_OP] Starting database initialization")
    try:
        logger.info("🔧 Starting database initialization...")
        await db_manager.init_db()
        logger.info(
            "🔧 Database connection initialized, now creating tables if tables not exist..."
        )
        await db_manager.create_tables()
        logger.info("🔧 Table creation completed")
        logger.info("Database initialized successfully")
        logger.debug(
            f"[DB_OP] Database initialization completed in {time.time() - start_time:.4f}s"
        )
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database():
    """Close database connections"""
    start_time = time.time()
    logger.debug("[DB_OP] Starting database close")
    try:
        await db_manager.close_db()
        logger.info("Database connections closed")
        logger.debug(
            f"[DB_OP] Database close completed in {time.time() - start_time:.4f}s"
        )
    except Exception as e:
        logger.error(f"Error closing database: {e}")
        logger.debug(
            f"[DB_OP] Database close failed in {time.time() - start_time:.4f}s"
        )
