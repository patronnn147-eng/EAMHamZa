"""
Event-driven RAG sync — SQLAlchemy hooks.

Registers `after_insert` / `after_update` / `after_delete` listeners on the
models whose rows are indexed in the RAG knowledge base. Each event enqueues a
Celery task to re-ingest (or remove) the affected row.

Why this design:
  - Hooks fire after the actual DB write — no risk of indexing rows that
    later roll back.
  - Hooks capture changes during the session and dispatch in `after_commit`
    so we never enqueue work for a transaction that fails.
  - All heavy work (HTTP to rag-service, S3 upload, embedding) happens in the
    Celery worker — request latency is unaffected.

Disable via env: RAG_HOOKS_ENABLED=false
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Pending changes attached to a session before commit.
# Cleared after dispatch or rollback.
_PENDING_ATTR = "_rag_pending_changes"


def _hooks_enabled() -> bool:
    return os.getenv("RAG_HOOKS_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _enqueue_sync(table: str, row_id: int) -> None:
    """Send the sync task to Celery via the existing broker."""
    try:
        from tasks.rag_db_sync import rag_sync_row

        rag_sync_row.delay(table, row_id)
    except Exception as e:
        logger.warning(f"[rag_hooks] failed to enqueue sync_row({table},{row_id}): {e}")


def _enqueue_delete(table: str, row_id: int) -> None:
    try:
        from tasks.rag_db_sync import rag_delete_row

        rag_delete_row.delay(table, row_id)
    except Exception as e:
        logger.warning(
            f"[rag_hooks] failed to enqueue delete_row({table},{row_id}): {e}"
        )


def _make_listener(table: str, op: str):
    """Build a mapper-level listener that records the change on the session."""

    def listener(mapper, connection, target):
        if not _hooks_enabled():
            return
        sess = Session.object_session(target)
        if sess is None:
            return
        pending = getattr(sess, _PENDING_ATTR, None)
        if pending is None:
            pending = []
            setattr(sess, _PENDING_ATTR, pending)
        row_id = getattr(target, "id", None)
        if row_id is None:
            return
        pending.append((table, op, row_id))

    return listener


def _on_after_commit(session: Session) -> None:
    pending = getattr(session, _PENDING_ATTR, None)
    if not pending:
        return
    # Dedup: same (table, id) only needs one sync; delete wins over update
    seen: dict[tuple[str, int], str] = {}
    for table, op, row_id in pending:
        key = (table, row_id)
        if op == "delete":
            seen[key] = "delete"
        else:
            seen.setdefault(key, "upsert")
    for (table, row_id), op in seen.items():
        if op == "delete":
            _enqueue_delete(table, row_id)
        else:
            _enqueue_sync(table, row_id)
    setattr(session, _PENDING_ATTR, [])


def _on_after_rollback(session: Session) -> None:
    setattr(session, _PENDING_ATTR, [])


def register_rag_hooks() -> None:
    """
    Call once at app startup. Registers per-model listeners + session-level
    commit/rollback dispatchers. Idempotent — guarded by a module flag.
    """
    if getattr(register_rag_hooks, "_registered", False):
        return

    if not _hooks_enabled():
        logger.info("[rag_hooks] disabled via RAG_HOOKS_ENABLED")
        register_rag_hooks._registered = True
        return

    # Import models lazily so SQLAlchemy mappers are configured first.
    from models.machines import Machines
    from models.ordres_travail import OrdresTravail
    from models.alertes import Alert
    from models.pieces import Piece

    try:
        from models.maintenances_planifiees import (
            MaintenancesPlanifiees as maintenances_planifiees,
        )
    except Exception:
        maintenances_planifiees = None  # type: ignore

    targets: list[tuple[Any, str]] = [
        (Machines, "machines"),
        (OrdresTravail, "OrdresTravail"),
        (Alert, "alertes"),
        (Piece, "pieces"),
    ]
    if maintenances_planifiees is not None:
        targets.append((maintenances_planifiees, "MaintenancesPlanifiees"))

    for model, table in targets:
        event.listen(model, "after_insert", _make_listener(table, "upsert"))
        event.listen(model, "after_update", _make_listener(table, "upsert"))
        event.listen(model, "after_delete", _make_listener(table, "delete"))

    # Session-level dispatch — only fires Celery tasks after the TX commits.
    event.listen(Session, "after_commit", _on_after_commit)
    event.listen(Session, "after_rollback", _on_after_rollback)

    logger.info(f"[rag_hooks] registered listeners for: {[t for _, t in targets]}")
    register_rag_hooks._registered = True
