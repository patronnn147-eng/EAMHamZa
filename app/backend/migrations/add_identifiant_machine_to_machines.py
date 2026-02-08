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
                    ADD COLUMN IF NOT EXISTS identifiant_machine VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE machines
                    SET identifiant_machine = ''
                    WHERE identifiant_machine IS NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ALTER COLUMN identifiant_machine SET NOT NULL
                    """
                )
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())
