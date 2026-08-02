"""Upload the seed maintenance documents into RAG.

Drives the real ADMIN upload path (S3/MinIO write + chunk + embed) rather
than inserting rows, so the documents behave exactly like operator-uploaded
ones. Idempotent: the endpoint rejects an identical file by content hash,
which this treats as success.

Docs are read from /app/rag_seed inside the pod (copy them in first):
    kubectl cp docs/rag-seed <pod>:/app/rag_seed
    kubectl exec ... -- python upload_rag_seed.py
"""
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DOCS_DIR = Path("/app/rag_seed")

# filename -> (doc_type, description). doc_type must be manual|sop|report.
CATALOG = {
    "manuel-cms-pick-and-place.txt": (
        "manual", "Manuel de maintenance des machines de placement CMS (lignes 1-3)"),
    "manuel-four-de-refusion.txt": (
        "manual", "Manuel de maintenance des fours de refusion CMS"),
    "sop-consignation-securite.txt": (
        "sop", "Procedure de consignation et mise en securite avant intervention"),
    "sop-maintenance-utilites.txt": (
        "sop", "Maintenance du compresseur central et du groupe froid"),
    "sop-diagnostic-pdca.txt": (
        "sop", "Deroulement d'une intervention et redaction du rapport PDCA"),
}


async def main() -> None:
    from core.database import db_manager
    import models  # noqa: F401 — registers mappers
    from models.alertes import Alert  # noqa: F401 — not in models/__init__
    from models.utilisateurs import UserRole, Utilisateurs
    from modules.shared.routes.rag_docs import _ingest_one
    from sqlalchemy import select, text

    await db_manager.init_db()

    if not DOCS_DIR.is_dir():
        logger.error("Docs directory not found: %s", DOCS_DIR)
        return

    async with db_manager.async_session_maker() as db:
        admin = (await db.execute(
            select(Utilisateurs).where(Utilisateurs.role == UserRole.ADMIN).limit(1)
        )).scalar_one_or_none()
        if not admin:
            logger.error("No ADMIN user found — cannot attribute the uploads.")
            return

        uploaded = skipped = failed = 0
        for filename, (doc_type, description) in CATALOG.items():
            path = DOCS_DIR / filename
            if not path.exists():
                logger.warning("missing: %s", filename)
                failed += 1
                continue

            file_bytes = path.read_bytes()

            # Same dedup rule the endpoint enforces, checked up front so a
            # re-run reports cleanly instead of raising a 409.
            import hashlib
            digest = hashlib.sha256(file_bytes).hexdigest()
            already = (await db.execute(
                text("SELECT filename FROM documents WHERE content_hash = :h LIMIT 1"),
                {"h": digest},
            )).first()
            if already:
                logger.info("skip (already ingested): %s", filename)
                skipped += 1
                continue

            try:
                await _ingest_one(
                    file_bytes=file_bytes,
                    filename=filename,
                    doc_type=doc_type,
                    machine_id=None,
                    description=description,
                    uploaded_by=admin.id,
                    db=db,
                )
                logger.info("uploaded: %s (%s)", filename, doc_type)
                uploaded += 1
            except Exception as exc:
                logger.error("FAILED %s: %s", filename, exc)
                failed += 1

        docs = (await db.execute(text("SELECT count(*) FROM documents"))).scalar()
        chunks = (await db.execute(text("SELECT count(*) FROM doc_chunks"))).scalar()
        logger.info("uploaded=%s skipped=%s failed=%s | documents=%s chunks=%s",
                    uploaded, skipped, failed, docs, chunks)


if __name__ == "__main__":
    asyncio.run(main())
