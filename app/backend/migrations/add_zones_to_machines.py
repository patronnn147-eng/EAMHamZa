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
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS zone VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS sous_zone VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    DROP COLUMN IF EXISTS ordre
                    """
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())
