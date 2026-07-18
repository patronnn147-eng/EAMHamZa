"""ArchiveService — soft-archive lifecycle for date-based modules.

Modules covered:
- PlanningTaches      (due column: date_fin)
- OrdresTravail       (due column: date_echeance)
- OrdresIntervention  (due column: date_intervention)
- plannings            (due column: date_fin)

Lifecycle:
1. **Archive**: hourly sweep moves rows past due OR in terminal status to
   archive (sets archived_at + archive_reason).
2. **Reactivate**: admin action sets archived_at=NULL.
3. **Purge**: weekly sweep deletes rows where archived_at < now - retention_days.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence

from sqlalchemy import String, and_, cast, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail
from models.planning_taches import PlanningTaches
from models.plannings import Plannings

logger = logging.getLogger(__name__)


# Per-module archive rules — keep ALL config in one table for review
@dataclass(frozen=True)
class ArchiveRule:
    module: str
    model: type
    due_column: str  # column whose value > NOW means "past due"
    terminal_statuses: Sequence[
        str
    ]  # status values that trigger archive regardless of date
    status_column: str = "statut"


ARCHIVE_RULES: List[ArchiveRule] = [
    ArchiveRule(
        module="PlanningTaches",
        model=PlanningTaches,
        due_column="date_fin",
        terminal_statuses=("COMPLETED",),
    ),
    ArchiveRule(
        module="OrdresTravail",
        model=OrdresTravail,
        due_column="date_echeance",
        terminal_statuses=("COMPLETED", "VALIDATED", "CLOSED", "REJECTED", "ANNULÉ"),
    ),
    ArchiveRule(
        module="OrdresIntervention",
        model=OrdresIntervention,
        due_column="date_intervention",
        terminal_statuses=("TERMINÉ", "TERMINE", "DECLINED"),
    ),
    ArchiveRule(
        module="plannings",
        model=Plannings,
        due_column="date_fin",
        terminal_statuses=(),  # no terminal status on plannings
        status_column="planning_statut",  # actual column name on Plannings
    ),
]

ARCHIVE_REASON_PAST_DUE = "PAST_DUE_DATE"
ARCHIVE_REASON_COMPLETED = "COMPLETED"
ARCHIVE_REASON_MANUAL = "MANUAL"

DEFAULT_PURGE_DAYS = 30


class ArchiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Sweep: archive past-due or completed items ─────────────────────

    async def archive_past_due(self, auto_commit: bool = True) -> Dict[str, int]:
        """Archive past-due AND/OR terminal-status rows across all modules.

        Returns {module: rows_archived}.
        Idempotent: rows already archived (archived_at IS NOT NULL) are skipped.
        """
        now = datetime.now(timezone.utc)
        results: Dict[str, int] = {}
        total = 0

        try:
            for rule in ARCHIVE_RULES:
                due_col = getattr(rule.model, rule.due_column)
                status_col = getattr(rule.model, rule.status_column, None)
                archived_col = getattr(rule.model, "archived_at")
                module_count = 0

                # Pass 1: archive rows in terminal status (reason=COMPLETED)
                if status_col is not None and rule.terminal_statuses:
                    stmt_completed = (
                        update(rule.model)
                        .where(
                            and_(
                                archived_col.is_(None),
                                cast(status_col, String).in_(rule.terminal_statuses),
                            )
                        )
                        .values(
                            archived_at=now, archive_reason=ARCHIVE_REASON_COMPLETED
                        )
                        .execution_options(synchronize_session=False)
                    )
                    r1 = await self.db.execute(stmt_completed)
                    module_count += r1.rowcount or 0

                # Pass 2: archive remaining past-due rows (reason=PAST_DUE_DATE)
                stmt_past = (
                    update(rule.model)
                    .where(
                        and_(
                            archived_col.is_(None),
                            due_col.is_not(None),
                            due_col < now,
                        )
                    )
                    .values(archived_at=now, archive_reason=ARCHIVE_REASON_PAST_DUE)
                    .execution_options(synchronize_session=False)
                )
                r2 = await self.db.execute(stmt_past)
                module_count += r2.rowcount or 0

                results[rule.module] = module_count
                total += module_count

            if auto_commit:
                await self.db.commit()

            if total:
                logger.warning(
                    f"ArchiveService.archive_past_due — archived {total} row(s): {results}"
                )
            return results
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(f"archive_past_due failed: {e}", exc_info=True)
            raise

    # ─── Reactivate: admin-only ─────────────────────────────────────────

    async def reactivate(
        self, module: str, item_id: int, auto_commit: bool = True
    ) -> bool:
        rule = next((r for r in ARCHIVE_RULES if r.module == module), None)
        if rule is None:
            raise ValueError(f"Unknown module: {module}")

        try:
            stmt = (
                update(rule.model)
                .where(getattr(rule.model, "id") == item_id)
                .where(getattr(rule.model, "archived_at").is_not(None))
                .values(archived_at=None, archive_reason=None)
                .execution_options(synchronize_session=False)
            )
            result = await self.db.execute(stmt)
            n = result.rowcount or 0
            if auto_commit:
                await self.db.commit()
            logger.info(f"Reactivated {module}/{item_id}: {n} row(s)")
            return n > 0
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(
                f"reactivate failed for {module}/{item_id}: {e}", exc_info=True
            )
            raise

    # ─── Purge: hard delete rows older than retention ───────────────────

    async def purge_old(
        self, retention_days: int = DEFAULT_PURGE_DAYS, auto_commit: bool = True
    ) -> Dict[str, int]:
        """Delete archived rows where archived_at < now - retention_days.

        WARNING: irreversible. Run only via scheduled task. Returns counts per module.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        results: Dict[str, int] = {}
        total = 0

        try:
            for rule in ARCHIVE_RULES:
                archived_col = getattr(rule.model, "archived_at")
                stmt = (
                    delete(rule.model)
                    .where(and_(archived_col.is_not(None), archived_col < cutoff))
                    .execution_options(synchronize_session=False)
                )
                result = await self.db.execute(stmt)
                n = result.rowcount or 0
                results[rule.module] = n
                total += n

            if auto_commit:
                await self.db.commit()

            if total:
                logger.warning(
                    f"ArchiveService.purge_old — purged {total} row(s) (>{retention_days}d): {results}"
                )
            return results
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(f"purge_old failed: {e}", exc_info=True)
            raise

    # ─── Listing for the Archive UI ─────────────────────────────────────

    async def list_archived(
        self,
        module: str,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        user_filter_column: Optional[str] = None,
        user_id_filter: Optional[int] = None,
    ) -> Dict[str, object]:
        """List archived rows of a module. Returns {items, total}.

        `user_filter_column` + `user_id_filter` scope per role
        (e.g. TECHNICIEN sees only items where technician_id = self).
        """
        rule = next((r for r in ARCHIVE_RULES if r.module == module), None)
        if rule is None:
            raise ValueError(f"Unknown module: {module}")

        archived_col = getattr(rule.model, "archived_at")
        conditions = [archived_col.is_not(None)]

        if date_from:
            conditions.append(archived_col >= date_from)
        if date_to:
            conditions.append(archived_col <= date_to)

        if (
            user_filter_column
            and user_id_filter
            and hasattr(rule.model, user_filter_column)
        ):
            col = getattr(rule.model, user_filter_column)
            conditions.append(col == user_id_filter)

        # Search by any text field — generic name/identifier columns
        if search:
            search_pattern = f"%{search.strip()}%"
            text_candidates: List[str] = []
            for col_name in (
                "titre",
                "identifiant_planning",
                "problem_description",
                "description",
                "rapport",
            ):
                if hasattr(rule.model, col_name):
                    text_candidates.append(col_name)
            if text_candidates:
                ors = [
                    getattr(rule.model, c).ilike(search_pattern)
                    for c in text_candidates
                ]
                conditions.append(or_(*ors))

        count_stmt = (
            select(func.count()).select_from(rule.model).where(and_(*conditions))
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        rows_stmt = (
            select(rule.model)
            .where(and_(*conditions))
            .order_by(archived_col.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = (await self.db.execute(rows_stmt)).scalars().all()

        return {"items": rows, "total": total}
