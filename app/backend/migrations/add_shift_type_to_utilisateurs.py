#!/usr/bin/env python3

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def run_migrations() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    ALTER TABLE utilisateurs
                    ADD COLUMN IF NOT EXISTS shift_type VARCHAR(50) NOT NULL DEFAULT 'MORNING'
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    UPDATE utilisateurs
                    SET shift_type = 'MORNING'
                    WHERE shift_type IS NULL
                    """
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())
