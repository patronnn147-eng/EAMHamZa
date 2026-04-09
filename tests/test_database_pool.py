# Auto-generated tests for connection pooling configuration

import os
import pytest
import asyncio
from app.backend.core.database import db_manager, DatabaseManager

@pytest.mark.asyncio
async def test_non_lambda_pool_configuration():
    """Ensure QueuePool settings are applied when not in Lambda environment."""
    # Ensure lambda env vars are unset
    os.environ.pop("AWS_LAMBDA_FUNCTION_NAME", None)
    os.environ.pop("IS_LAMBDA", None)

    # Force re-initialization
    await db_manager.init_db()
    engine = db_manager.engine
    # Verify that the engine uses QueuePool (default) and has correct kwargs
    assert hasattr(engine, "pool")
    # Check pool size and timeout attributes if available
    pool = engine.pool
    # Some pool implementations may not expose size directly; ensure attributes exist
    assert getattr(pool, "size", None) == 10
    assert getattr(pool, "_max_overflow", None) == 20
    assert getattr(pool, "_timeout", None) == 30
    # Recycle time is stored as "_recycle" on the pool
    assert getattr(pool, "_recycle", None) == 1800

@pytest.mark.asyncio
async def test_lambda_uses_nullpool():
    """When Lambda detection is enabled, engine uses NullPool."""
    os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-lambda"
    # Re-create DatabaseManager to avoid cached engine
    new_manager = DatabaseManager()
    await new_manager.init_db()
    engine = new_manager.engine
    # NullPool does not have a "pool" attribute; it returns a connection directly
    # Verify that the engine's pool class is NullPool
    from sqlalchemy.pool import NullPool as SQNullPool
    assert isinstance(engine.pool, SQNullPool)
    # Clean up env var
    os.environ.pop("AWS_LAMBDA_FUNCTION_NAME", None)
