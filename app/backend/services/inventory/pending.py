"""PendingPieceService — uncatalogued piece review queue.

When a technician submits an uncatalogued piece, this service:
1. Inserts a ``pending_pieces`` row (status=PENDING_REVIEW)
2. Inserts a ``mouvement_stock`` row IMMEDIATELY with:
   - movement_type='PENDING_OUT'
   - piece_id=NULL
   - pending_piece_id=<new>
   This preserves the actual submission timestamp.

Admin review converts the placeholder in-place — the same mouvement_stock row
is updated (NOT a new row inserted), preserving created_at. This is the
"chronological honesty" requirement from the plan.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.mouvement_stock import MouvementStock
from models.pending_pieces import PendingPiece
from models.pieces import Piece
from models.stock import Stock
from models.utilisateurs import Utilisateurs

from .stock import _to_decimal

logger = logging.getLogger(__name__)


class PendingPieceService:
    """Lifecycle: submit → review (match/create/reject)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Submit (called from intervention request flow) ──────────────────────

    async def create_with_placeholder(
        self,
        name: str,
        quantity,
        unit: str = "pcs",
        category: Optional[str] = None,
        photo_object_key: Optional[str] = None,
        notes: Optional[str] = None,
        intervention_id: Optional[int] = None,
        submitted_by: Optional[int] = None,
        auto_commit: bool = True,
    ) -> PendingPiece:
        """Create a pending piece + its PENDING_OUT placeholder movement."""
        qty = _to_decimal(quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")
        if not name or not name.strip():
            raise ValueError("name is required")

        try:
            pp = PendingPiece(
                intervention_id=intervention_id,
                submitted_by=submitted_by,
                name=name.strip()[:200],
                category=(category or "").strip()[:50] or None,
                quantity=qty,
                unit=(unit or "pcs")[:20],
                photo_object_key=photo_object_key,
                notes=notes,
                status="PENDING_REVIEW",
            )
            self.db.add(pp)
            await self.db.flush()  # need pp.id for placeholder

            # Placeholder movement — piece_id NULL, pending_piece_id = pp.id
            placeholder = MouvementStock(
                piece_id=None,
                pending_piece_id=pp.id,
                quantity=qty,
                unit=unit,
                movement_type="PENDING_OUT",
                reference=f"OT-itv-{intervention_id}-pending"
                if intervention_id
                else "pending",
                intervention_id=intervention_id,
            )
            self.db.add(placeholder)

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(pp)

            logger.info(
                f"PendingPiece created id={pp.id} name='{pp.name}' qty={qty} {unit} "
                f"intervention_id={intervention_id}"
            )
            return pp
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.error(f"create_with_placeholder failed: {e}", exc_info=True)
            raise

    # ── List ────────────────────────────────────────────────────────────────

    async def list_pending(
        self,
        status: Optional[str] = "PENDING_REVIEW",
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        try:
            count_q = select(func.count(PendingPiece.id))
            base_q = (
                select(
                    PendingPiece,
                    Utilisateurs.nom.label("submitted_by_name"),
                    Piece.name.label("matched_piece_name"),
                )
                .outerjoin(Utilisateurs, Utilisateurs.id == PendingPiece.submitted_by)
                .outerjoin(Piece, Piece.id == PendingPiece.matched_piece_id)
                .order_by(PendingPiece.created_at.desc())
            )
            if status:
                count_q = count_q.where(PendingPiece.status == status)
                base_q = base_q.where(PendingPiece.status == status)

            total = (await self.db.execute(count_q)).scalar() or 0
            rows = (await self.db.execute(base_q.offset(skip).limit(limit))).fetchall()

            items = []
            for pp, submitter_name, matched_name in rows:
                items.append(
                    {
                        "id": pp.id,
                        "intervention_id": pp.intervention_id,
                        "submitted_by": pp.submitted_by,
                        "submitted_by_name": submitter_name,
                        "name": pp.name,
                        "category": pp.category,
                        "quantity": pp.quantity,
                        "unit": pp.unit,
                        "photo_object_key": pp.photo_object_key,
                        "notes": pp.notes,
                        "status": pp.status,
                        "matched_piece_id": pp.matched_piece_id,
                        "matched_piece_name": matched_name,
                        "reviewed_by": pp.reviewed_by,
                        "reviewed_at": pp.reviewed_at,
                        "rejection_reason": pp.rejection_reason,
                        "created_at": pp.created_at,
                    }
                )
            return {"items": items, "total": total}
        except Exception as e:
            logger.error(f"list_pending failed: {e}", exc_info=True)
            raise

    # ── Match: link to existing piece (in-place mvt conversion) ─────────────

    async def match_to_existing(
        self,
        pending_id: int,
        matched_piece_id: int,
        reviewed_by: Optional[int] = None,
        auto_commit: bool = True,
    ) -> PendingPiece:
        """Convert pending piece to a real consumption against an existing piece.

        Strategy:
        - Update pending_piece row → status=MATCHED, matched_piece_id, reviewed metadata
        - Update the **existing** PENDING_OUT mouvement_stock row in-place
          (keeps original created_at) → movement_type='out', piece_id=matched
        - Decrement Stock.quantity by the pending qty (real stock effect now)
        """
        try:
            pp = await self.db.scalar(
                select(PendingPiece).where(PendingPiece.id == pending_id)
            )
            if pp is None:
                raise ValueError(f"PendingPiece {pending_id} not found")
            if pp.status != "PENDING_REVIEW":
                raise ValueError(
                    f"PendingPiece {pending_id} is not pending review (status={pp.status})"
                )

            target_piece = await self.db.scalar(
                select(Piece).where(Piece.id == matched_piece_id)
            )
            if target_piece is None:
                raise ValueError(f"Target piece {matched_piece_id} not found")

            # Locate the placeholder mvt row
            placeholder = await self.db.scalar(
                select(MouvementStock).where(
                    MouvementStock.pending_piece_id == pending_id
                )
            )

            qty = Decimal(str(pp.quantity))

            # Mutate placeholder in-place — preserves created_at
            if placeholder is not None:
                placeholder.movement_type = "out"
                placeholder.piece_id = matched_piece_id
                # keep pending_piece_id for audit traceability
                placeholder.reference = (
                    placeholder.reference or ""
                ) + f"|matched-pending-{pending_id}"

            # Decrement stock now (real effect)
            stock = await self.db.scalar(
                select(Stock).where(Stock.piece_id == matched_piece_id)
            )
            if stock is None:
                stock = Stock(piece_id=matched_piece_id, quantity=Decimal("0"))
                self.db.add(stock)
                await self.db.flush()
            current = Decimal(str(stock.quantity or 0))
            stock.quantity = (current - qty).quantize(Decimal("0.01"))
            # NOTE: we intentionally allow negative quantity here. The piece was
            # already used in the field; a negative balance signals "owed back to
            # stock" until the next delivery reconciles it. Operations team can
            # see this in the alerts view.

            # Mark pending row resolved
            pp.status = "MATCHED"
            pp.matched_piece_id = matched_piece_id
            pp.reviewed_by = reviewed_by
            pp.reviewed_at = datetime.now(timezone.utc)

            # Auto-link resolved piece to intervention's machine
            await self._auto_link_pending_to_machine(
                piece_id=matched_piece_id, intervention_id=pp.intervention_id
            )

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(pp)

            # invalidate forecast cache
            self._invalidate_forecast()

            logger.info(
                f"PendingPiece {pending_id} MATCHED → piece {matched_piece_id}; "
                f"stock now {stock.quantity}"
            )
            return pp
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.error(
                f"match_to_existing failed for pending {pending_id}: {e}", exc_info=True
            )
            raise

    # ── Create new piece from pending submission ────────────────────────────

    async def create_new_piece(
        self,
        pending_id: int,
        new_piece_data: Dict[str, Any],
        reviewed_by: Optional[int] = None,
        auto_commit: bool = True,
    ) -> PendingPiece:
        """Create a brand-new catalog piece then match the pending to it."""
        try:
            pp = await self.db.scalar(
                select(PendingPiece).where(PendingPiece.id == pending_id)
            )
            if pp is None:
                raise ValueError(f"PendingPiece {pending_id} not found")
            if pp.status != "PENDING_REVIEW":
                raise ValueError(f"PendingPiece {pending_id} is not pending review")

            # Create piece
            ref = new_piece_data["reference"]
            existing = await self.db.scalar(select(Piece).where(Piece.reference == ref))
            if existing is not None:
                raise ValueError(
                    f"Reference '{ref}' already exists (piece id={existing.id}). Use match instead."
                )

            piece = Piece(
                reference=ref,
                name=new_piece_data.get("name") or pp.name,
                description=new_piece_data.get("description"),
                unit_price=new_piece_data.get("unit_price"),
                category=new_piece_data.get("category") or pp.category,
                min_stock=new_piece_data.get("min_stock", 5),
                is_consumable=new_piece_data.get("is_consumable", False),
                default_unit=new_piece_data.get("default_unit", pp.unit or "pcs"),
            )
            self.db.add(piece)
            await self.db.flush()  # piece.id

            # Reuse the match path (in-place mvt conversion, stock decrement)
            placeholder = await self.db.scalar(
                select(MouvementStock).where(
                    MouvementStock.pending_piece_id == pending_id
                )
            )
            qty = Decimal(str(pp.quantity))
            if placeholder is not None:
                placeholder.movement_type = "out"
                placeholder.piece_id = piece.id
                placeholder.reference = (
                    placeholder.reference or ""
                ) + f"|created-pending-{pending_id}"

            # New piece → no prior stock — start at zero and decrement (negative balance signals owed)
            self.db.add(
                Stock(
                    piece_id=piece.id,
                    quantity=(Decimal("0") - qty).quantize(Decimal("0.01")),
                )
            )

            pp.status = "CREATED"
            pp.matched_piece_id = piece.id
            pp.reviewed_by = reviewed_by
            pp.reviewed_at = datetime.now(timezone.utc)

            # Auto-link the newly-created piece to intervention's machine
            await self._auto_link_pending_to_machine(
                piece_id=piece.id, intervention_id=pp.intervention_id
            )

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(pp)

            self._invalidate_forecast()

            logger.info(
                f"PendingPiece {pending_id} CREATED new piece {piece.id} ({piece.reference})"
            )
            return pp
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.error(
                f"create_new_piece failed for pending {pending_id}: {e}", exc_info=True
            )
            raise

    # ── Reject ──────────────────────────────────────────────────────────────

    async def reject(
        self,
        pending_id: int,
        rejection_reason: str,
        reviewed_by: Optional[int] = None,
        auto_commit: bool = True,
    ) -> PendingPiece:
        """Reject — placeholder mvt updated to 'REJECTED', no stock effect."""
        try:
            pp = await self.db.scalar(
                select(PendingPiece).where(PendingPiece.id == pending_id)
            )
            if pp is None:
                raise ValueError(f"PendingPiece {pending_id} not found")
            if pp.status != "PENDING_REVIEW":
                raise ValueError(f"PendingPiece {pending_id} is not pending review")

            placeholder = await self.db.scalar(
                select(MouvementStock).where(
                    MouvementStock.pending_piece_id == pending_id
                )
            )
            if placeholder is not None:
                placeholder.movement_type = "REJECTED"
                placeholder.reference = (
                    placeholder.reference or ""
                ) + f"|rejected-{rejection_reason[:50]}"

            pp.status = "REJECTED"
            pp.rejection_reason = rejection_reason
            pp.reviewed_by = reviewed_by
            pp.reviewed_at = datetime.now(timezone.utc)

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(pp)

            logger.info(f"PendingPiece {pending_id} REJECTED: {rejection_reason}")
            return pp
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.error(f"reject failed for pending {pending_id}: {e}", exc_info=True)
            raise

    async def _auto_link_pending_to_machine(
        self, piece_id: int, intervention_id: int | None
    ) -> None:
        """When a pending piece is MATCHED/CREATED and tied to an intervention,
        auto-link the resolved piece to the intervention's machine.

        Same idempotent ON CONFLICT pattern as `InventoryReservationService`.
        Best-effort — failure does not roll back the resolution.
        """
        if not intervention_id:
            return
        try:
            from models.ordres_intervention import Ordres_intervention
            from models.piece_machine import piece_machine
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            machine_id = await self.db.scalar(
                select(Ordres_intervention.machine_id).where(
                    Ordres_intervention.id == intervention_id
                )
            )
            if not machine_id:
                return
            stmt = pg_insert(piece_machine).values(
                piece_id=piece_id, machine_id=machine_id
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["piece_id", "machine_id"]
            )
            await self.db.execute(stmt)
        except Exception as e:
            logger.debug(f"_auto_link_pending_to_machine soft-fail: {e}")

        # ── Hooks ───────────────────────────────────────────────────────────────

    @staticmethod
    def _invalidate_forecast() -> None:
        try:
            from modules.ml.services.demand_forecast import invalidate_forecast_cache

            invalidate_forecast_cache()
        except Exception:  # pragma: no cover — best effort
            pass
