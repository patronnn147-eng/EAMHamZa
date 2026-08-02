"""Async SQLAlchemy session for RAG service."""
import os
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/asset_management",
)


def _split_ssl(url: str) -> tuple[str, dict]:
    """Move libpq's `sslmode` out of the URL into asyncpg's `ssl` connect arg.

    Managed Postgres (Azure) hands out URLs ending `?sslmode=require`, but that
    is libpq syntax: asyncpg raises `connect() got an unexpected keyword
    argument 'sslmode'`. SQLAlchemy's asyncpg dialect wants it as
    connect_args={"ssl": ...} instead. The backend carries the same fix in
    core/database.py and alembic/env.py.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    mode = (params.pop("sslmode", [None])[0] or "").lower()
    cleaned = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
    # disable/allow/prefer all mean "do not require TLS" for our purposes.
    if mode in ("require", "verify-ca", "verify-full"):
        return cleaned, {"ssl": "require"}
    return cleaned, {}


DATABASE_URL, _CONNECT_ARGS = _split_ssl(DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_CONNECT_ARGS,
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
