"""Repair mojibake piece names written into the catalogue.

The P7 top-up was run against a backend image that still carried the corrupted
pkl, so 80 catalogue rows were inserted with names like "Condensateur de
dã©marrage". Same corruption, same inverse transform as
app/ml-microservice/scripts/repair_p7_catalog_encoding.py — reproduced here
because the backend image doesn't ship the ml-microservice tree.

Idempotent: rows that are already clean are left untouched.

    kubectl exec -n eam-staging deployment/backend -- python repair_piece_names.py
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def repair_text(s: str) -> str:
    """Undo (utf-8 bytes -> latin-1 decode -> lower). See the ml-microservice
    script for the full explanation of why a plain latin-1 round-trip fails."""
    if not isinstance(s, str) or all(ord(c) < 0x80 for c in s):
        return s

    out, i, n = [], 0, len(s)
    while i < n:
        code = ord(s[i])
        if code < 0x80 or code > 0xFF:
            out.append(s[i])
            i += 1
            continue

        j, cont = i + 1, []
        while j < n and 0x80 <= ord(s[j]) <= 0xBF and len(cont) < 3:
            cont.append(ord(s[j]))
            j += 1
        if not cont:
            out.append(s[i])
            i += 1
            continue

        decoded = None
        for lead in (code, code - 0x20):
            if lead < 0xC0 or lead > 0xF4:
                continue
            width = 1 if lead < 0xE0 else (2 if lead < 0xF0 else 3)
            if len(cont) < width:
                continue
            try:
                decoded = bytes([lead] + cont[:width]).decode("utf-8")
                i = i + 1 + width
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            out.append(s[i])
            i += 1
        else:
            out.append(decoded)
    return "".join(out)


async def main() -> None:
    from core.database import db_manager
    import models  # noqa: F401
    from models.alertes import Alert  # noqa: F401
    from models.pieces import Piece
    from sqlalchemy import select

    await db_manager.init_db()
    async with db_manager.async_session_maker() as db:
        pieces = (await db.execute(select(Piece))).scalars().all()
        fixed = 0
        for piece in pieces:
            new_name = repair_text(piece.name or "")
            if new_name != piece.name:
                logger.info("  %r -> %r", piece.name, new_name)
                piece.name = new_name
                fixed += 1
        if fixed:
            await db.commit()
        logger.info("Repaired %s of %s piece names.", fixed, len(pieces))


if __name__ == "__main__":
    asyncio.run(main())
