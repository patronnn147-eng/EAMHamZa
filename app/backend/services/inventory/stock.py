"""StockService — atomic stock movements with auto_commit control.

`consume_stock` and `add_stock` accept `auto_commit=False` so callers can
chain multiple stock operations within a single parent transaction
(work-order completion, reservation fulfillment, etc.). Use `auto_commit=True`
(the default) for standalone REST calls.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.pieces import Piece
from models.stock import Stock
from models.mouvement_stock import MouvementStock

logger = logging.getLogger(__name__)

Numeric = Union[int, float, Decimal]


def _to_decimal(value: Numeric) -> Decimal:
    """Cast any numeric input to Decimal with 2-place quantization."""
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


class StockService:
    """Service layer for Stock operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stock_levels(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Get current stock levels for all pieces with pagination."""
        try:
            count_query = select(func.count(Stock.id)).join(
                Piece, Stock.piece_id == Piece.id
            )
            count_result = await self.db.execute(count_query)
            total = count_result.scalar() or 0

            query = (
                select(
                    Stock.id,
                    Stock.piece_id,
                    Stock.quantity,
                    Piece.name.label("piece_name"),
                    Piece.reference.label("piece_reference"),
                    Piece.min_stock,
                    Piece.default_unit,
                )
                .join(Piece, Stock.piece_id == Piece.id)
                .order_by(Piece.name)
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(query)
            rows = result.fetchall()
            items = [
                {
                    "id": row.id,
                    "piece_id": row.piece_id,
                    "quantity": row.quantity,
                    "piece_name": row.piece_name,
                    "piece_reference": row.piece_reference,
                    "min_stock": row.min_stock,
                }
                for row in rows
            ]
            return {"items": items, "total": total}
        except Exception as e:
            logger.exception(f"Error fetching stock levels: {str(e)}")
            raise

    async def add_stock(
        self,
        piece_id: int,
        quantity: Numeric,
        reference: Optional[str] = None,
        unit: Optional[str] = None,
        intervention_id: Optional[int] = None,
        auto_commit: bool = True,
    ) -> Dict[str, Any]:
        """Add stock for a piece. Creates stock entry if none exists.

        When `auto_commit=False` the caller is responsible for committing
        the surrounding transaction (used by reservation fulfillment).
        """
        qty = _to_decimal(quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")

        try:
            # Resolve unit from piece if not provided
            if unit is None:
                piece = await self.db.scalar(select(Piece).where(Piece.id == piece_id))
                if piece is None:
                    raise ValueError(f"Piece {piece_id} not found")
                unit = piece.default_unit or "pcs"

            stock = await self.db.scalar(
                select(Stock).where(Stock.piece_id == piece_id)
            )
            if stock:
                # Coerce existing INT column safely; ORM will handle Numeric
                stock.quantity = (Decimal(str(stock.quantity or 0)) + qty).quantize(
                    Decimal("0.01")
                )
            else:
                stock = Stock(piece_id=piece_id, quantity=qty)
                self.db.add(stock)

            movement = MouvementStock(
                piece_id=piece_id,
                quantity=qty,
                unit=unit,
                movement_type="in",
                reference=reference,
                intervention_id=intervention_id,
            )
            self.db.add(movement)

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(stock)

            logger.info(
                f"Added {qty} {unit} stock for piece {piece_id} (commit={auto_commit})"
            )
            return {
                "id": stock.id,
                "piece_id": stock.piece_id,
                "quantity": stock.quantity,
            }
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(f"Error adding stock for piece {piece_id}: {str(e)}")
            raise

    async def consume_stock(
        self,
        piece_id: int,
        quantity: Numeric,
        intervention_id: Optional[int] = None,
        reference: Optional[str] = None,
        unit: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Dict[str, Any]:
        """Consume stock for a piece (intervention, scrap, …).

        Raises ValueError if insufficient stock. When `auto_commit=False`
        the caller controls the transaction boundary.
        """
        qty = _to_decimal(quantity)
        if qty <= 0:
            raise ValueError("quantity must be > 0")

        try:
            if unit is None:
                piece = await self.db.scalar(select(Piece).where(Piece.id == piece_id))
                if piece is None:
                    raise ValueError(f"Piece {piece_id} not found")
                unit = piece.default_unit or "pcs"

            stock = await self.db.scalar(
                select(Stock).where(Stock.piece_id == piece_id)
            )
            if not stock:
                raise ValueError(f"No stock entry found for piece {piece_id}")
            current_qty = Decimal(str(stock.quantity or 0))
            if current_qty < qty:
                raise ValueError(
                    f"Insufficient stock for piece {piece_id}: have {current_qty}, need {qty}"
                )

            stock.quantity = (current_qty - qty).quantize(Decimal("0.01"))

            ref = reference or (
                f"intervention-{intervention_id}" if intervention_id else None
            )
            movement = MouvementStock(
                piece_id=piece_id,
                quantity=qty,
                unit=unit,
                movement_type="out",
                reference=ref,
                intervention_id=intervention_id,
            )
            self.db.add(movement)

            await self.db.flush()
            if auto_commit:
                await self.db.commit()
                await self.db.refresh(stock)

            logger.info(
                f"Consumed {qty} {unit} stock for piece {piece_id} (commit={auto_commit})"
            )
            return {
                "id": stock.id,
                "piece_id": stock.piece_id,
                "quantity": stock.quantity,
            }
        except Exception as e:
            if auto_commit:
                await self.db.rollback()
            logger.exception(f"Error consuming stock for piece {piece_id}: {str(e)}")
            raise

    async def get_alerts(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Get low-stock alerts with pagination.

        Alerts driven by AVAILABLE quantity = Stock.quantity − Σ active reservations.
        This prevents over-ordering when reservations have already covered the deficit.
        """
        try:
            # Active reservations subquery (RESERVED movements not yet released)
            # Note: RESERVED movements are net positive in count; RESERVATION_RELEASED decrements.
            # We compute via the required_pieces.quantity_reserved field for accuracy.
            reserved_sub = (
                select(
                    Piece.id.label("piece_id"),
                    func.coalesce(func.sum(_active_reservation_sum_col()), 0).label(
                        "reserved"
                    ),
                )
                .select_from(Piece)
                .outerjoin(
                    _active_reservation_source(),
                    _active_reservation_source().c.piece_id == Piece.id,
                )
                .group_by(Piece.id)
                .subquery()
            )

            count_query = (
                select(func.count(Stock.piece_id))
                .join(Piece, Stock.piece_id == Piece.id)
                .outerjoin(reserved_sub, reserved_sub.c.piece_id == Piece.id)
                .where(
                    (Stock.quantity - func.coalesce(reserved_sub.c.reserved, 0))
                    < Piece.min_stock
                )
            )
            total = (await self.db.execute(count_query)).scalar() or 0

            query = (
                select(
                    Stock.piece_id,
                    Piece.name.label("piece_name"),
                    Piece.reference.label("piece_reference"),
                    Stock.quantity.label("current_quantity"),
                    Piece.min_stock,
                    func.coalesce(reserved_sub.c.reserved, 0).label("reserved"),
                )
                .join(Piece, Stock.piece_id == Piece.id)
                .outerjoin(reserved_sub, reserved_sub.c.piece_id == Piece.id)
                .where(
                    (Stock.quantity - func.coalesce(reserved_sub.c.reserved, 0))
                    < Piece.min_stock
                )
                .order_by(Stock.quantity)
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(query)
            rows = result.fetchall()
            items = []
            for row in rows:
                available = Decimal(str(row.current_quantity or 0)) - Decimal(
                    str(row.reserved or 0)
                )
                items.append(
                    {
                        "piece_id": row.piece_id,
                        "piece_name": row.piece_name,
                        "piece_reference": row.piece_reference,
                        "current_quantity": available,  # report AVAILABLE not raw
                        "min_stock": row.min_stock,
                        "deficit": Decimal(row.min_stock) - available,
                    }
                )
            return {"items": items, "total": total}
        except Exception as e:
            logger.exception(f"Error fetching stock alerts: {str(e)}")
            raise

    async def get_movements(
        self,
        piece_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get stock movement history with pagination."""
        try:
            count_query = select(func.count(MouvementStock.id))
            if piece_id:
                count_query = count_query.where(MouvementStock.piece_id == piece_id)
            total = (await self.db.execute(count_query)).scalar() or 0

            query = (
                select(
                    MouvementStock.id,
                    MouvementStock.piece_id,
                    MouvementStock.pending_piece_id,
                    MouvementStock.quantity,
                    MouvementStock.unit,
                    MouvementStock.movement_type,
                    MouvementStock.reference,
                    MouvementStock.intervention_id,
                    MouvementStock.created_at,
                    Piece.name.label("piece_name"),
                )
                .outerjoin(Piece, MouvementStock.piece_id == Piece.id)
                .order_by(MouvementStock.id.desc())
                .offset(skip)
                .limit(limit)
            )
            if piece_id:
                query = query.where(MouvementStock.piece_id == piece_id)
            result = await self.db.execute(query)
            rows = result.fetchall()
            items = [
                {
                    "id": row.id,
                    "piece_id": row.piece_id,
                    "pending_piece_id": row.pending_piece_id,
                    "quantity": row.quantity,
                    "unit": row.unit,
                    "movement_type": row.movement_type,
                    "reference": row.reference,
                    "intervention_id": row.intervention_id,
                    "created_at": row.created_at,
                    "piece_name": row.piece_name,
                }
                for row in rows
            ]
            return {"items": items, "total": total}
        except Exception as e:
            logger.exception(f"Error fetching stock movements: {str(e)}")
            raise


# ── Helpers for active-reservation aggregation ───────────────────────────────
# Module-level helpers to keep get_alerts query readable. Importing RequiredPiece
# at module scope would create a circular import via services.inventory; lazy import.


def _active_reservation_source():
    from models.required_pieces import RequiredPiece  # noqa: WPS433 (intentional lazy)

    return RequiredPiece.__table__


def _active_reservation_sum_col():
    from models.required_pieces import RequiredPiece  # noqa: WPS433

    return RequiredPiece.quantity_reserved
