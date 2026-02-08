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
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS nom VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS emplacement VARCHAR(255)
                    """
                )
            )
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
                    ADD COLUMN IF NOT EXISTS statut VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS type VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS date_derniere_maintenance TIMESTAMP WITH TIME ZONE
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS date_prochaine_maintenance TIMESTAMP WITH TIME ZONE
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS image_url VARCHAR(1024)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE machines
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    UPDATE machines
                    SET identifiant_machine = COALESCE(identifiant_machine, '')
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE machines
                    SET nom = COALESCE(nom, '')
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE machines
                    SET emplacement = COALESCE(emplacement, '')
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE machines
                    SET statut = COALESCE(statut, '')
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE machines
                    SET type = COALESCE(type, '')
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
            await conn.execute(text("""ALTER TABLE machines ALTER COLUMN nom SET NOT NULL"""))
            await conn.execute(text("""ALTER TABLE machines ALTER COLUMN emplacement SET NOT NULL"""))
            await conn.execute(text("""ALTER TABLE machines ALTER COLUMN statut SET NOT NULL"""))
            await conn.execute(text("""ALTER TABLE machines ALTER COLUMN type SET NOT NULL"""))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())
