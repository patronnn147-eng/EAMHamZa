"""InventoryReservationService — atomic reservation + fulfillment.

This is the **only** service that should mutate stock for the inventory ↔
work-order workflow. Approval/cancellation/completion handlers call methods
here; they never touch Stock or MouvementStock tables directly.

Key invariants:
- ``available_stock = stock.quantity − Σ required_pieces.quantity_reserved
  (where required_piece.intervention.statut is active)``
- Reservations expire automatically after ``DEFAULT_RESERVATION_TTL_DAYS``
  unless explicitly released or fulfilled.
- All multi-row operations support ``auto_commit=False`` so callers can wrap
  them in a parent transaction (e.g. work-order completion).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.consumed_pieces import ConsumedPiece
from models.mouvement_stock import MouvementStock
from models.pieces import Piece
from models.required_pieces import RequiredPiece
from models.stock import Stock
from schemas.stock import DeficitItem

from .stock import StockService, _to_decimal

logger = logging.getLogger(__name__)

DEFAULT_RESERVATION_TTL_DAYS = 7
DECIMAL_ZERO = Decimal("0")


class InsufficientStockError(Exception):
    """Raised when a reservation cannot be created due to deficit."""

    def __init__(self, missing: List[DeficitItem]):
        self.missing = missing
        super().__init__(f"Stock insuffisant — {len(missing)} pièce(s) en déficit")


class InventoryReservationService:
    """Owns the lifecycle of inventory reservations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stock_svc = StockService(db)

    # ── Read: availability ──────────────────────────────────────────────────

    async def get_available(self, piece_id: int) -> Decimal:
        """Compute available stock for a piece (raw qty − active reservations).

        Negative result clamped to zero.
        """
        stock_qty = await self.db.scalar(
            select(func.coalesce(Stock.quantity, 0)).where(Stock.piece_id == piece_id)
        )
        if stock_qty is None:
            return DECIMAL_ZERO

        reserved = await self.db.scalar(
            select(func.coalesce(func.sum(RequiredPiece.quantity_reserved), 0)).where(
                RequiredPiece.piece_id == piece_id
            )
        )
        result = Decimal(str(stock_qty)) - Decimal(str(reserved or 0))
        return result if result > DECIMAL_ZERO else DECIMAL_ZERO

    async def get_availability_map(
        self, piece_ids: Iterable[int]
    ) -> Dict[int, Dict[str, Decimal]]:
        """Batch availability lookup — single query.

        Returns {piece_id: {stock, reserved, available}}.
        Pieces missing a stock row report 0 stock.
        """
        piece_ids = list({pid for pid in piece_ids if pid is not None})
        if not piece_ids:
            return {}

        # Stock per piece
        stock_rows = await self.db.execute(
            select(Stock.piece_id, Stock.quantity).where(Stock.piece_id.in_(piece_ids))
        )
        stock_map = {
            row.piece_id: Decimal(str(row.quantity or 0)) for row in stock_rows
        }

        # Reserved per piece
        reserved_rows = await self.db.execute(
            select(
                RequiredPiece.piece_id,
                func.coalesce(func.sum(RequiredPiece.quantity_reserved), 0).label(
                    "reserved"
                ),
            )
            .where(RequiredPiece.piece_id.in_(piece_ids))
            .group_by(RequiredPiece.piece_id)
        )
        reserved_map = {
            row.piece_id: Decimal(str(row.reserved or 0)) for row in reserved_rows
        }

        result: Dict[int, Dict[str, Decimal]] = {}
        for pid in piece_ids:
            stock = stock_map.get(pid, DECIMAL_ZERO)
            reserved = reserved_map.get(pid, DECIMAL_ZERO)
            available = max(DECIMAL_ZERO, stock - reserved)
            result[pid] = {"stock": stock, "reserved": reserved, "available": available}
        return result

    # ── Create / fail: try_reserve ──────────────────────────────────────────

    async def _compute_deficits(
        self, wanted: Dict[int, Decimal], avail_map: Dict
    ) -> List[DeficitItem]:
        """Return DeficitItem list for any piece whose available stock < need."""
        deficits: List[DeficitItem] = []
        for piece_id, need in wanted.items():
            avail = avail_map.get(piece_id, {}).get("available", DECIMAL_ZERO)
            if avail < need:
                piece_name = await self.db.scalar(
                    select(Piece.name).where(Piece.id == piece_id)
                )
                deficits.append(
                    DeficitItem(
                        piece_id=piece_id,
                        piece_name=piece_name or f"piece-{piece_id}",
                        requested=need,
                        available=avail,
                        deficit=need - avail,
                    )
                )
        return deficits

    def _mark_rows_reserved(self, rows, expires_at, intervention_id: int) -> None:
        """Mutate each RequiredPiece row and append audit MouvementStock."""
        for r in rows:
            r.quantity_reserved = Decimal(str(r.quantity_planned))
            r.reservation_expires_at = expires_at
            r.approved = True
            self.db.add(
                MouvementStock(
                    piece_id=r.piece_id,
                    quantity=r.quantity_reserved,
                    unit=r.unit,
                    movement_type="RESERVED",
                    reference=f"OT-itv-{intervention_id}",
                    intervention_id=intervention_id,
                )
            )

    async def try_reserve(
        self,
        intervention_id: int,
        required_piece_ids: Optional[Sequence[int]] = None,
        ttl_days: int = DEFAULT_RESERVATION_TTL_DAYS,
        auto_commit: bool = True,
    ) -> List[RequiredPiece]:
        """Reserve stock for an intervention's required pieces.

        - If ``required_piece_ids`` is None, reserves ALL pending required
          pieces for the intervention (i.e. ``approved IS NULL``).
        - Raises ``InsufficientStockError`` if any item lacks available stock.
          On error, the transaction is rolled back (if auto_commit) so no
          partial reservation persists.

        Concurrency: aggregate availability is recomputed under the current
        SQL transaction. For strict isolation use ``REPEATABLE READ`` at the
        session level — defaults are fine for low contention.
        """
        if intervention_id <= 0:
            raise ValueError("intervention_id must be positive")

        try:
            q = select(RequiredPiece).where(
                RequiredPiece.intervention_id == intervention_id,
                RequiredPiece.quantity_reserved == 0,
            )
            if required_piece_ids:
                q = q.where(RequiredPiece.id.in_(required_piece_ids))
            rows = (await self.db.execute(q)).scalars().all()
            if not rows:
                logger.info(
                    f"try_reserve: no required pieces to reserve for itv {intervention_id}"
                )
                return []

            wanted: Dict[int, Decimal] = {}
            for r in rows:
                wanted[r.piece_id] = wanted.get(r.piece_id, DECIMAL_ZERO) + Decimal(str(r.quantity_planned))

            avail_map = await self.get_availability_map(wanted.keys())
            deficits = await self._compute_deficits(wanted, avail_map)
            if deficits:
                if auto_commit:
                    await self.db.rollback()
                raise InsufficientStockError(missing=deficits)

            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
            self._mark_rows_reserved(rows, expires_at, intervention_id)

            await self.db.flush()
            if auto_commit:
                await self.db.commit()

            logger.info(
                f"try_reserve OK — itv {intervention_id}: reserved {len(rows)} required pieces"
            )
            return rows
        except InsufficientStockError:
            raise
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(
                f"try_reserve failed for itv {intervention_id}: {e}", exc_info=True
            )
            raise

    # ── Release: full intervention ──────────────────────────────────────────

    async def release_all(
        self,
        intervention_id: int,
        reason: str = "cancelled",
        auto_commit: bool = True,
    ) -> int:
        """Release every active reservation for an intervention.

        Returns the number of released rows. Idempotent: safe to call on a
        completed intervention (no rows will match).
        """
        try:
            rows = (
                (
                    await self.db.execute(
                        select(RequiredPiece).where(
                            RequiredPiece.intervention_id == intervention_id,
                            RequiredPiece.quantity_reserved > 0,
                        )
                    )
                )
                .scalars()
                .all()
            )

            for r in rows:
                reserved_qty = Decimal(str(r.quantity_reserved))
                # audit
                self.db.add(
                    MouvementStock(
                        piece_id=r.piece_id,
                        quantity=reserved_qty,
                        unit=r.unit,
                        movement_type="RESERVATION_RELEASED",
                        reference=f"OT-itv-{intervention_id}-{reason}",
                        intervention_id=intervention_id,
                    )
                )
                r.quantity_reserved = DECIMAL_ZERO
                r.reservation_expires_at = None

            await self.db.flush()
            if auto_commit:
                await self.db.commit()

            logger.info(
                f"release_all itv {intervention_id} — released {len(rows)} reservations ({reason})"
            )
            return len(rows)
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(
                f"release_all failed for itv {intervention_id}: {e}", exc_info=True
            )
            raise

    # ── Release: expired only (Celery beat task) ────────────────────────────

    async def release_expired(self, auto_commit: bool = True) -> int:
        """Release every reservation whose `reservation_expires_at` is past.

        Returns the count of released rows. Logs interventions affected.
        """
        try:
            now = datetime.now(timezone.utc)
            rows = (
                (
                    await self.db.execute(
                        select(RequiredPiece).where(
                            RequiredPiece.quantity_reserved > 0,
                            RequiredPiece.reservation_expires_at != None,  # noqa: E711
                            RequiredPiece.reservation_expires_at < now,
                        )
                    )
                )
                .scalars()
                .all()
            )

            count = 0
            affected_interventions = set()
            for r in rows:
                reserved_qty = Decimal(str(r.quantity_reserved))
                self.db.add(
                    MouvementStock(
                        piece_id=r.piece_id,
                        quantity=reserved_qty,
                        unit=r.unit,
                        movement_type="RESERVATION_RELEASED",
                        reference=f"OT-itv-{r.intervention_id}-expired",
                        intervention_id=r.intervention_id,
                    )
                )
                r.quantity_reserved = DECIMAL_ZERO
                r.reservation_expires_at = None
                count += 1
                affected_interventions.add(r.intervention_id)

            await self.db.flush()
            if auto_commit:
                await self.db.commit()

            if count:
                logger.warning(
                    f"release_expired — {count} reservations expired across "
                    f"{len(affected_interventions)} intervention(s): {sorted(affected_interventions)}"
                )
            return count
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(f"release_expired failed: {e}", exc_info=True)
            raise

    # ── Fulfill: completion-time consumption ────────────────────────────────

    async def fulfill_reservation(
        self,
        required_piece_id: int,
        quantity_used: Decimal,
        quantity_returned: Decimal,
        quantity_wasted: Decimal,
        disposition: str,
        notes: Optional[str] = None,
        auto_commit: bool = False,  # default False — usually called from a parent TX
    ) -> ConsumedPiece:
        """Convert a reservation into actual consumption.

        Writes:
        - one `consumed_pieces` row
        - one `mouvement_stock` 'out' row for (used + wasted) — actual stock decrement
        - one `mouvement_stock` 'in' row for `returned` (if > 0)
        - one `mouvement_stock` 'RESERVATION_RELEASED' row clearing the reservation
        All within the same SQLAlchemy session — caller must commit (or set
        ``auto_commit=True``).
        """
        used = _to_decimal(quantity_used)
        returned = _to_decimal(quantity_returned)
        wasted = _to_decimal(quantity_wasted)

        # Load reservation row
        rp = await self.db.scalar(
            select(RequiredPiece).where(RequiredPiece.id == required_piece_id)
        )
        if rp is None:
            raise ValueError(f"required_piece {required_piece_id} not found")

        planned = Decimal(str(rp.quantity_planned))
        if (used + returned + wasted) > planned:
            raise ValueError(
                f"Sum of consumed quantities ({used + returned + wasted}) "
                f"exceeds planned ({planned}) for required_piece {required_piece_id}"
            )

        try:
            # 1. Stock decrement for net out (used + wasted)
            net_out = used + wasted
            if net_out > DECIMAL_ZERO:
                await self.stock_svc.consume_stock(
                    piece_id=rp.piece_id,
                    quantity=net_out,
                    intervention_id=rp.intervention_id,
                    reference=f"OT-itv-{rp.intervention_id}",
                    unit=rp.unit,
                    auto_commit=False,
                )

            # 2. Stock increment for returned
            if returned > DECIMAL_ZERO:
                await self.stock_svc.add_stock(
                    piece_id=rp.piece_id,
                    quantity=returned,
                    reference=f"OT-itv-{rp.intervention_id}-return",
                    unit=rp.unit,
                    intervention_id=rp.intervention_id,
                    auto_commit=False,
                )

            # 3. Release the reservation (audit row + zero out reserved qty)
            if rp.quantity_reserved > 0:
                self.db.add(
                    MouvementStock(
                        piece_id=rp.piece_id,
                        quantity=Decimal(str(rp.quantity_reserved)),
                        unit=rp.unit,
                        movement_type="RESERVATION_RELEASED",
                        reference=f"OT-itv-{rp.intervention_id}-fulfilled",
                        intervention_id=rp.intervention_id,
                    )
                )
            rp.quantity_reserved = DECIMAL_ZERO
            rp.reservation_expires_at = None

            # 4. Insert consumed_pieces row (trigger validates sum)
            cp = ConsumedPiece(
                intervention_id=rp.intervention_id,
                required_piece_id=rp.id,
                piece_id=rp.piece_id,
                quantity_used=used,
                quantity_returned=returned,
                quantity_wasted=wasted,
                unit=rp.unit,
                disposition=disposition,
                notes=notes,
            )
            self.db.add(cp)

            # Auto-link piece to machine if not already linked (Option 1 hybrid)
            await self._auto_link_piece_to_machine(
                piece_id=rp.piece_id, intervention_id=rp.intervention_id
            )

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(cp)

            logger.info(
                f"fulfill_reservation rp={required_piece_id} used={used} "
                f"returned={returned} wasted={wasted} disposition={disposition}"
            )
            return cp
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(
                f"fulfill_reservation failed for rp {required_piece_id}: {e}",
                exc_info=True,
            )
            raise

    # ── Auto-linking — Option 1 of hybrid piece-machine workflow ──────────
    async def _auto_link_piece_to_machine(
        self, piece_id: int, intervention_id: int
    ) -> None:
        """Insert a piece_machine row when a piece is consumed on a machine.

        Idempotent (`ON CONFLICT DO NOTHING`). Catches the scenario where a
        technician used a piece on a machine that wasn't previously declared
        compatible — the link is grown organically from real consumption.
        """
        try:
            from models.OrdresIntervention import OrdresIntervention
            from models.piece_machine import piece_machine
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            machine_id = await self.db.scalar(
                select(OrdresIntervention.machine_id).where(
                    OrdresIntervention.id == intervention_id
                )
            )
            if not machine_id:
                return  # intervention has no machine — skip

            stmt = pg_insert(piece_machine).values(
                piece_id=piece_id, machine_id=machine_id
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["piece_id", "machine_id"]
            )
            await self.db.execute(stmt)
        except Exception as e:
            # Non-fatal — auto-link is a best-effort enrichment
            logger.debug(f"_auto_link_piece_to_machine soft-fail: {e}")

    # ── Deficit alert (hook for demand forecast / procurement) ──────────────

    def create_deficit_alert(self, missing: List[DeficitItem]) -> None:
        """Invalidate the demand-forecast cache so the next read picks up
        the new deficit. Hook here for future enrichment (Celery email task,
        notification, procurement webhook, etc.).
        """
        try:
            from modules.ml.services.demand_forecast import invalidate_forecast_cache

            invalidate_forecast_cache()
            logger.info(
                f"create_deficit_alert — invalidated forecast cache; "
                f"{len(missing)} piece(s) below available threshold"
            )
        except Exception as e:
            # Non-fatal — best-effort hook
            logger.warning(f"Failed to invalidate forecast cache: {e}")
