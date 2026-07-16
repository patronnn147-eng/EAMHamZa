"""Async SQLAlchemy session for RAG service."""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/asset_management",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,        # default 5 — ingest holds a connection through slow embed+insert
    max_overflow=20,     # default 10 — burst during bulk DB→RAG sync
    pool_timeout=60,     # default 30 — give slow embedding pipeline more headroom
    pool_recycle=1800,   # recycle stale conns every 30 min
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
