"""Add the parts P7 can recommend to the live catalogue, with stock levels.

Additive and idempotent: existing pieces are left alone, only missing ones are
inserted, so this can run against a seeded database without disturbing the
work-order history. Matches seed_demo_staging.py's piece seeding.

    kubectl exec -n eam-staging deployment/backend -- python topup_p7_parts.py
"""
import asyncio
import logging
import random
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    from core.database import db_manager
    import models  # noqa: F401 — registers mappers
    from models.alertes import Alert  # noqa: F401 — not in models/__init__
    from models.pieces import Piece
    from models.stock import Stock
    from seed_demo_staging import _p7_catalog_specs
    from sqlalchemy import select

    rng = random.Random(20260802)
    await db_manager.init_db()

    async with db_manager.async_session_maker() as db:
        existing = {
            (n or "").strip().lower()
            for (n,) in (await db.execute(select(Piece.name))).all()
        }
        specs = [s for s in _p7_catalog_specs()
                 if s["name"].strip().lower() not in existing]

        if not specs:
            logger.info("Nothing to add — every P7 part is already catalogued.")
            return

        added = []
        for spec in specs:
            piece = Piece(**spec)
            db.add(piece)
            added.append(piece)
        await db.flush()

        # Same shape as the main seed: most parts comfortably stocked, a
        # deliberate minority short so the shortage surfaces stay demonstrable.
        short_idx = set(rng.sample(range(len(added)), k=max(1, len(added) // 5)))
        for i, piece in enumerate(added):
            floor = piece.min_stock or 5
            if i in short_idx:
                qty = Decimal(rng.randint(0, max(1, floor - 1)))
            else:
                qty = Decimal(rng.randint(floor + 5, floor * 4 + 10))
            db.add(Stock(piece_id=piece.id, quantity=qty))

        await db.commit()
        total = (await db.execute(select(Piece))).scalars().all()
        logger.info("Added %s parts (%s deliberately below min_stock). Catalogue now %s.",
                    len(added), len(short_idx), len(total))


if __name__ == "__main__":
    asyncio.run(main())
