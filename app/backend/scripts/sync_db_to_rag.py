"""
One-shot DB → RAG sync.

Reads selected tables from Postgres, formats each row as a human-readable text
document, and POSTs to the RAG service `/ingest` endpoint.

Usage (inside backend container, or with appropriate env vars):
    python scripts/sync_db_to_rag.py                  # ingest all tables
    python scripts/sync_db_to_rag.py --tables machines,ordres_travail
    python scripts/sync_db_to_rag.py --dry-run        # print docs, no upload
    python scripts/sync_db_to_rag.py --delete-stale   # remove old auto-synced docs first

Idempotency:
    Each row is ingested as a separate doc with filename pattern
    `db:{table}:{id}` and doc_type="report". When --delete-stale is passed,
    documents matching this filename pattern are deleted before re-ingest.

Run inside container:
    docker compose exec backend python scripts/sync_db_to_rag.py
"""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import os
import sys
from datetime import datetime
from typing import Callable

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Backend service for S3 upload — script runs inside backend container
sys.path.insert(0, "/app")
from services.rag_storage import upload_bytes, build_object_key, delete_object  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("db2rag")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/asset_management",
)
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8003")
INGEST_BATCH = int(
    os.getenv("DB2RAG_BATCH", "2")
)  # parallel HTTP uploads — embed pipeline is heavy, keep low
HTTP_TIMEOUT = float(os.getenv("DB2RAG_TIMEOUT", "120"))

DOC_TYPE = "report"  # one of: manual | sop | report
FILENAME_PREFIX = "db:"  # marks auto-synced docs for --delete-stale


# ---------------------------------------------------------------------------
# Row → text formatters
# ---------------------------------------------------------------------------


def _fmt_dt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    return str(v)


def _fmt_machine(r) -> str:
    return (
        f"# Machine #{r.id} — {r.nom}\n\n"
        f"- Type: {r.type or '—'}\n"
        f"- Location: {r.emplacement or '—'} / Zone: {r.zone or '—'} / Sub-zone: {r.sous_zone or '—'}\n"
        f"- Order: {r.ordre or '—'}\n"
        f"- Status: {r.statut or '—'}\n"
        f"- Last maintenance: {_fmt_dt(r.date_derniere_maintenance)}\n"
        f"- Next maintenance: {_fmt_dt(r.date_prochaine_maintenance)}\n"
        f"- Created: {_fmt_dt(r.created_at)}\n"
    )


def _fmt_ordre_travail(r) -> str:
    return (
        f"# Work Order #{r.id} — {r.titre}\n\n"
        f"- Machine ID: {r.machine_id}\n"
        f"- Priority: {r.priorite}\n"
        f"- Status: {r.statut}\n"
        f"- Failure type: {r.failure_type or '—'}\n"
        f"- Due date: {_fmt_dt(r.date_echeance)}\n"
        f"- Started: {_fmt_dt(r.date_debut)}\n"
        f"- Finished: {_fmt_dt(r.date_fin)}\n"
        f"- Validated: {_fmt_dt(r.date_validation)}\n"
        f"\n## Description\n{r.description}\n"
        + (f"\n## Report\n{r.rapport}\n" if r.rapport else "")
        + (
            f"\n## Chief tech feedback\n{r.cheftech_feedback}\n"
            if r.cheftech_feedback
            else ""
        )
    )


def _fmt_alerte(r) -> str:
    return (
        f"# Alert #{r.id} — {r.alert_type} ({r.severity})\n\n"
        f"- Machine ID: {r.machine_id}\n"
        f"- Priority: {r.priority or '—'}\n"
        f"- Active: {r.is_active}\n"
        f"- Linked to WO: {r.work_order_id or '—'}\n"
        f"- RUL days: {r.rul_days if r.rul_days is not None else '—'}\n"
        f"- Failure probability: {r.failure_probability if r.failure_probability is not None else '—'}\n"
        f"- Created: {_fmt_dt(r.created_at)}\n"
        f"- Dismissed: {_fmt_dt(r.dismissed_at)}\n"
        f"\n## Message\n{r.message}\n"
    )


def _fmt_maintenance_planifiee(r) -> str:
    return (
        f"# Scheduled Maintenance #{r.id}\n\n"
        f"- Machine ID: {r.machine_id}\n"
        f"- Type: {getattr(r, 'type_maintenance', None) or '—'}\n"
        f"- Date: {_fmt_dt(getattr(r, 'date_planifiee', None))}\n"
        f"- Status: {getattr(r, 'statut', None) or '—'}\n"
        f"\n## Description\n{getattr(r, 'description', '') or ''}\n"
    )


def _fmt_piece(r) -> str:
    return (
        f"# Part #{r.id} — {getattr(r, 'nom', getattr(r, 'designation', '—'))}\n\n"
        f"- Reference: {getattr(r, 'reference', '—')}\n"
        f"- Description: {getattr(r, 'description', '—')}\n"
        f"- Stock qty: {getattr(r, 'quantite_stock', '—')}\n"
        f"- Unit price: {getattr(r, 'prix_unitaire', '—')}\n"
    )


# ---------------------------------------------------------------------------
# Table registry — (sql, formatter, machine_id_attr_or_None)
# ---------------------------------------------------------------------------

TABLES: dict[str, tuple[str, Callable, str | None]] = {
    "machines": (
        "SELECT id, nom, type, emplacement, zone, sous_zone, ordre, statut, "
        "date_derniere_maintenance, date_prochaine_maintenance, created_at "
        "FROM machines ORDER BY id",
        _fmt_machine,
        "id",  # the row IS the machine
    ),
    "ordres_travail": (
        "SELECT id, titre, description, priorite, machine_id, statut, "
        "failure_type, date_echeance, date_debut, date_fin, date_validation, "
        "rapport, cheftech_feedback FROM ordres_travail "
        "WHERE statut IN ('COMPLETED','VALIDATED','CLOSED') "
        "ORDER BY id DESC LIMIT 5000",
        _fmt_ordre_travail,
        "machine_id",
    ),
    "alertes": (
        "SELECT id, machine_id, alert_type, severity, message, rul_days, "
        "failure_probability, is_active, work_order_id, priority, "
        "created_at, dismissed_at FROM alertes "
        "ORDER BY id DESC LIMIT 5000",
        _fmt_alerte,
        "machine_id",
    ),
    "maintenances_planifiees": (
        "SELECT * FROM maintenances_planifiees ORDER BY id DESC LIMIT 2000",
        _fmt_maintenance_planifiee,
        "machine_id",
    ),
    "pieces": (
        "SELECT * FROM pieces ORDER BY id LIMIT 2000",
        _fmt_piece,
        None,  # not machine-bound
    ),
}

# Single-row fetch SQL per table — used by event-driven sync.
# Note: ordres_travail filter (only completed/validated/closed) still applies —
# in-progress edits are not synced until status reaches a terminal state.
ROW_FETCH: dict[str, str] = {
    "machines": (
        "SELECT id, nom, type, emplacement, zone, sous_zone, ordre, statut, "
        "date_derniere_maintenance, date_prochaine_maintenance, created_at "
        "FROM machines WHERE id = :id"
    ),
    "ordres_travail": (
        "SELECT id, titre, description, priorite, machine_id, statut, "
        "failure_type, date_echeance, date_debut, date_fin, date_validation, "
        "rapport, cheftech_feedback FROM ordres_travail "
        "WHERE id = :id AND statut IN ('COMPLETED','VALIDATED','CLOSED')"
    ),
    "alertes": (
        "SELECT id, machine_id, alert_type, severity, message, rul_days, "
        "failure_probability, is_active, work_order_id, priority, "
        "created_at, dismissed_at FROM alertes WHERE id = :id"
    ),
    "maintenances_planifiees": "SELECT * FROM maintenances_planifiees WHERE id = :id",
    "pieces": "SELECT * FROM pieces WHERE id = :id",
}


# ---------------------------------------------------------------------------
# Sync core
# ---------------------------------------------------------------------------


async def fetch_rows(db: AsyncSession, sql: str):
    result = await db.execute(text(sql))
    return result.fetchall()


async def delete_stale_docs(
    client: httpx.AsyncClient,
    db: AsyncSession,
    table: str,
) -> int:
    """Delete previously-synced docs (chunks + S3 objects) for a table."""
    resp = await client.get(f"{RAG_SERVICE_URL}/documents")
    resp.raise_for_status()
    docs = resp.json()
    prefix = f"{FILENAME_PREFIX}{table}:"
    targets = [d for d in docs if d["filename"].startswith(prefix)]

    # Fetch s3_object_key for each target from DB (rag-service doesn't return it)
    if targets:
        ids = [d["id"] for d in targets]
        result = await db.execute(
            text(
                "SELECT id::text AS id, s3_object_key FROM documents WHERE id::text = ANY(:ids)"
            ),
            {"ids": ids},
        )
        key_map = {r.id: r.s3_object_key for r in result.fetchall()}
    else:
        key_map = {}

    deleted = 0
    loop = asyncio.get_event_loop()
    for d in targets:
        try:
            r = await client.delete(f"{RAG_SERVICE_URL}/documents/{d['id']}")
            if r.status_code in (200, 204):
                deleted += 1
                # Best-effort S3 cleanup
                s3_key = key_map.get(d["id"])
                if s3_key:
                    try:
                        await loop.run_in_executor(None, delete_object, s3_key)
                    except Exception as e:
                        log.warning(f"S3 delete failed for {s3_key}: {e}")
        except Exception as e:
            log.warning(f"delete failed for {d['id']}: {e}")
    log.info(f"[{table}] deleted {deleted} stale docs (chunks + S3)")
    return deleted


async def ingest_one(
    client: httpx.AsyncClient,
    db: AsyncSession,
    text_body: str,
    filename: str,
    machine_id: int | None,
) -> bool:
    """
    1. Send text → rag-service /ingest → returns doc_id
    2. Upload same bytes → MinIO `rag-docs` bucket under {doc_id}/{filename}
    3. Patch documents.s3_object_key so the row links to S3
    """
    file_bytes = text_body.encode("utf-8")
    files = {"file": (filename + ".txt", io.BytesIO(file_bytes), "text/plain")}
    data = {"doc_type": DOC_TYPE}
    if machine_id is not None:
        data["machine_id"] = str(machine_id)

    # 1. Ingest (creates documents row + chunks + embeddings)
    try:
        r = await client.post(f"{RAG_SERVICE_URL}/ingest", files=files, data=data)
        if r.status_code != 201:
            log.warning(f"{filename}: HTTP {r.status_code} — {r.text[:200]}")
            return False
        doc_id = r.json()["doc_id"]
    except Exception as e:
        log.warning(f"{filename}: ingest failed — {e}")
        return False

    # 2. Upload bytes to MinIO under deterministic key
    object_key = build_object_key(doc_id, filename + ".txt")
    try:
        # upload_bytes is sync (minio client) — run in thread to avoid blocking event loop
        await asyncio.get_event_loop().run_in_executor(
            None, upload_bytes, file_bytes, object_key, "text/plain"
        )
        log.info(f"[S3 OK] {object_key} ({len(file_bytes)}B)")
    except Exception as e:
        # Loud error — do NOT silently mark success. KB row exists without S3 backup = broken.
        log.exception(f"[S3 FAIL] {filename} ({doc_id}): {e}")
        return False

    # 3. Link S3 key to documents row
    try:
        await db.execute(
            text("UPDATE documents SET s3_object_key = :k WHERE id = :id"),
            {"k": object_key, "id": doc_id},
        )
        await db.commit()
    except Exception as e:
        log.warning(f"{filename}: failed to patch s3_object_key — {e}")
    return True


async def sync_table(
    client: httpx.AsyncClient,
    db: AsyncSession,
    table: str,
    sql: str,
    formatter: Callable,
    machine_id_attr: str | None,
    dry_run: bool,
) -> tuple[int, int]:
    log.info(f"[{table}] fetching rows…")
    rows = await fetch_rows(db, sql)
    log.info(f"[{table}] {len(rows)} rows")

    ok, fail = 0, 0
    sem = asyncio.Semaphore(INGEST_BATCH)

    async def _process(r):
        nonlocal ok, fail
        async with sem:
            try:
                body = formatter(r)
            except Exception as e:
                log.warning(f"[{table}] row {getattr(r, 'id', '?')} format error: {e}")
                fail += 1
                return
            filename = f"{FILENAME_PREFIX}{table}:{r.id}"
            mid = getattr(r, machine_id_attr, None) if machine_id_attr else None
            if dry_run:
                print(f"--- {filename} (machine_id={mid}) ---\n{body}\n")
                ok += 1
                return
            success = await ingest_one(client, db, body, filename, mid)
            if success:
                ok += 1
            else:
                fail += 1

    await asyncio.gather(*(_process(r) for r in rows))
    log.info(f"[{table}] done: ok={ok} fail={fail}")
    return ok, fail


async def _delete_existing(
    client: httpx.AsyncClient, db: AsyncSession, table: str, row_id: int
) -> None:
    """Delete any previously-synced doc(s) for this exact row + their S3 objects."""
    filename = f"{FILENAME_PREFIX}{table}:{row_id}"
    # Look up doc(s) by filename prefix (with .txt suffix from previous sync)
    result = await db.execute(
        text(
            "SELECT id::text AS id, s3_object_key FROM documents WHERE filename LIKE :pat"
        ),
        {"pat": filename + "%"},
    )
    rows = result.fetchall()
    loop = asyncio.get_event_loop()
    for row in rows:
        try:
            await client.delete(f"{RAG_SERVICE_URL}/documents/{row.id}")
            if row.s3_object_key:
                try:
                    await loop.run_in_executor(None, delete_object, row.s3_object_key)
                except Exception as e:
                    log.warning(f"S3 delete failed for {row.s3_object_key}: {e}")
        except Exception as e:
            log.warning(f"delete failed for doc {row.id}: {e}")


async def sync_row(table: str, row_id: int) -> dict:
    """
    Re-ingest ONE row: delete prior version → fetch fresh row → format → ingest.

    Called by event-driven Celery task after a model commit.
    """
    if table not in TABLES:
        return {"ok": False, "error": f"unknown table {table}"}

    sql = ROW_FETCH[table]
    _, formatter, mid_attr = TABLES[table]
    engine = create_async_engine(DATABASE_URL, future=True)
    SessionMaker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            async with SessionMaker() as db:
                await _delete_existing(client, db, table, row_id)
                result = await db.execute(text(sql), {"id": row_id})
                row = result.fetchone()
                if row is None:
                    return {"ok": True, "skipped": "row not found or filtered"}
                try:
                    body = formatter(row)
                except Exception as e:
                    return {"ok": False, "error": f"format: {e}"}
                filename = f"{FILENAME_PREFIX}{table}:{row.id}"
                mid = getattr(row, mid_attr, None) if mid_attr else None
                ok = await ingest_one(client, db, body, filename, mid)
                return {"ok": ok, "table": table, "row_id": row_id, "machine_id": mid}
    finally:
        await engine.dispose()


async def delete_row(table: str, row_id: int) -> dict:
    """Remove the synced doc(s) for ONE row (chunks + S3) — no re-ingest."""
    if table not in TABLES:
        return {"ok": False, "error": f"unknown table {table}"}
    engine = create_async_engine(DATABASE_URL, future=True)
    SessionMaker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            async with SessionMaker() as db:
                await _delete_existing(client, db, table, row_id)
                return {"ok": True, "table": table, "row_id": row_id}
    finally:
        await engine.dispose()


async def run_sync(
    tables: list[str] | None = None,
    delete_stale: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Programmatic entry point — called by CLI and by Celery task.

    Returns dict: {ok: int, fail: int, tables: [...], skipped_unknown: [...]}
    """
    targets = tables or list(TABLES.keys())
    unknown = [t for t in targets if t not in TABLES]
    if unknown:
        log.error(f"Unknown tables: {unknown}")
        targets = [t for t in targets if t in TABLES]

    engine = create_async_engine(DATABASE_URL, future=True)
    SessionMaker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_ok, total_fail = 0, 0
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            if not dry_run:
                try:
                    h = await client.get(f"{RAG_SERVICE_URL}/health")
                    h.raise_for_status()
                except Exception as e:
                    log.exception(f"RAG service unreachable at {RAG_SERVICE_URL}: {e}")
                    return {
                        "ok": 0,
                        "fail": 0,
                        "tables": targets,
                        "skipped_unknown": unknown,
                        "error": "rag-service unreachable",
                    }

            async with SessionMaker() as db:
                if delete_stale and not dry_run:
                    for table in targets:
                        await delete_stale_docs(client, db, table)

                for table in targets:
                    sql, fmt, mid_attr = TABLES[table]
                    ok, fail = await sync_table(
                        client, db, table, sql, fmt, mid_attr, dry_run
                    )
                    total_ok += ok
                    total_fail += fail
    finally:
        await engine.dispose()

    log.info(f"SUMMARY: ok={total_ok} fail={total_fail}")
    return {
        "ok": total_ok,
        "fail": total_fail,
        "tables": targets,
        "skipped_unknown": unknown,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables",
        default=",".join(TABLES.keys()),
        help=f"Comma list. Choices: {','.join(TABLES.keys())}",
    )
    parser.add_argument("--dry-run", action="store_true", help="print docs, no upload")
    parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="delete previously-synced docs before re-ingest",
    )
    args = parser.parse_args()

    targets = [t.strip() for t in args.tables.split(",") if t.strip()]
    result = await run_sync(
        tables=targets,
        delete_stale=args.delete_stale,
        dry_run=args.dry_run,
    )
    return 0 if result["fail"] == 0 and not result.get("error") else 3


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
