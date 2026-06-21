import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, delete, func, case, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.pieces import Piece
from models.piece_machine import piece_machine
from models.stock import Stock

logger = logging.getLogger(__name__)


class PieceService:
    """Service layer for Piece (spare parts) operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Piece]:
        try:
            obj = Piece(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created piece with id: {obj.id}")
            return obj
        except IntegrityError as ie:
            await self.db.rollback()
            msg = str(ie.orig) if hasattr(ie, "orig") else str(ie)
            ref = data.get("reference") or "?"
            if "pieces_reference_key" in msg or "duplicate key" in msg:
                logger.warning(f"Duplicate piece reference '{ref}' rejected")
                raise ValueError(
                    f"La référence '{ref}' est déjà utilisée. Choisissez-en une autre."
                )
            logger.error(f"IntegrityError creating piece: {msg}")
            raise ValueError("Violation de contrainte: vérifiez les valeurs saisies.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating piece: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Piece]:
        try:
            query = select(Piece).where(Piece.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching piece {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            query = select(Piece)
            count_query = select(lambda: Piece.id)

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Piece, field):
                        query = query.where(getattr(Piece, field) == value)
                        count_query = count_query.where(getattr(Piece, field) == value)

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith("-"):
                    field_name = sort[1:]
                    if hasattr(Piece, field_name):
                        query = query.order_by(getattr(Piece, field_name).desc())
                else:
                    if hasattr(Piece, sort):
                        query = query.order_by(getattr(Piece, sort))
            else:
                query = query.order_by(Piece.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching piece list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Piece]:
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated piece {obj_id}")
            return obj
        except IntegrityError as ie:
            await self.db.rollback()
            msg = str(ie.orig) if hasattr(ie, "orig") else str(ie)
            ref = update_data.get("reference") or "?"
            if "pieces_reference_key" in msg or "duplicate key" in msg:
                logger.warning(
                    f"Duplicate piece reference '{ref}' on update — rejected"
                )
                raise ValueError(
                    f"La référence '{ref}' est déjà utilisée par une autre pièce."
                )
            raise ValueError("Violation de contrainte lors de la mise à jour.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating piece {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted piece {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting piece {obj_id}: {str(e)}")
            raise

    async def get_pieces_by_machine(
        self,
        machine_id: int,
        include_consumables: bool = True,
        include_all_search: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return pieces grouped by relevance to a machine.

        Sections:
          - ``compatible``  : pieces explicitly linked to this machine
          - ``consumables`` : pieces with ``is_consumable=True`` (regardless of machine)
          - ``other``       : full-catalog matches when a search term is given
        Each entry includes piece info + current stock qty for the picker.
        """
        # Compatible pieces (via piece_machine table)
        compat_q = (
            select(
                Piece.id,
                Piece.reference,
                Piece.name,
                Piece.category,
                Piece.unit_price,
                Piece.min_stock,
                Piece.is_consumable,
                Piece.default_unit,
                func.coalesce(Stock.quantity, 0).label("stock_quantity"),
            )
            .join(piece_machine, piece_machine.c.piece_id == Piece.id)
            .outerjoin(Stock, Stock.piece_id == Piece.id)
            .where(piece_machine.c.machine_id == machine_id)
            .order_by(Piece.name)
        )
        compat_rows = (await self.db.execute(compat_q)).fetchall()
        compat = [self._row_to_picker_item(r) for r in compat_rows]
        compat_ids = {r.id for r in compat_rows}

        # Consumables (deduplicated from compatible)
        consumables: List[Dict[str, Any]] = []
        if include_consumables:
            cons_q = (
                select(
                    Piece.id,
                    Piece.reference,
                    Piece.name,
                    Piece.category,
                    Piece.unit_price,
                    Piece.min_stock,
                    Piece.is_consumable,
                    Piece.default_unit,
                    func.coalesce(Stock.quantity, 0).label("stock_quantity"),
                )
                .outerjoin(Stock, Stock.piece_id == Piece.id)
                .where(Piece.is_consumable == True)  # noqa: E712
                .order_by(Piece.name)
            )
            cons_rows = (await self.db.execute(cons_q)).fetchall()
            consumables = [
                self._row_to_picker_item(r) for r in cons_rows if r.id not in compat_ids
            ]

        # Optional full-catalog search
        other: List[Dict[str, Any]] = []
        if include_all_search and include_all_search.strip():
            term = f"%{include_all_search.strip()}%"
            other_q = (
                select(
                    Piece.id,
                    Piece.reference,
                    Piece.name,
                    Piece.category,
                    Piece.unit_price,
                    Piece.min_stock,
                    Piece.is_consumable,
                    Piece.default_unit,
                    func.coalesce(Stock.quantity, 0).label("stock_quantity"),
                )
                .outerjoin(Stock, Stock.piece_id == Piece.id)
                .where(or_(Piece.name.ilike(term), Piece.reference.ilike(term)))
                .where(~Piece.id.in_(compat_ids))
                .order_by(Piece.name)
                .limit(50)
            )
            other_rows = (await self.db.execute(other_q)).fetchall()
            other = [self._row_to_picker_item(r) for r in other_rows]

        # Enrich each item with available_quantity (stock - active reservations)
        all_items = compat + consumables + other
        piece_ids = [it["id"] for it in all_items]
        await self._attach_availability(all_items, piece_ids)

        return {"compatible": compat, "consumables": consumables, "other": other}

    async def _attach_availability(
        self, items: List[Dict[str, Any]], piece_ids: List[int]
    ) -> None:
        """Mutate items in place adding `reserved_quantity` + `available_quantity`.

        Single batch query: SELECT piece_id, SUM(quantity_reserved) FROM required_pieces
        WHERE piece_id IN (...) AND quantity_reserved > 0 GROUP BY piece_id.
        """
        if not piece_ids:
            return
        from models.required_pieces import RequiredPiece

        rows = await self.db.execute(
            select(
                RequiredPiece.piece_id,
                func.coalesce(func.sum(RequiredPiece.quantity_reserved), 0).label(
                    "reserved"
                ),
            )
            .where(RequiredPiece.piece_id.in_(piece_ids))
            .where(RequiredPiece.quantity_reserved > 0)
            .group_by(RequiredPiece.piece_id)
        )
        reserved_map = {r.piece_id: r.reserved for r in rows.fetchall()}
        for it in items:
            stock = it.get("stock_quantity", 0) or 0
            reserved = reserved_map.get(it["id"], 0) or 0
            try:
                from decimal import Decimal

                avail = Decimal(str(stock)) - Decimal(str(reserved))
                if avail < 0:
                    avail = Decimal("0")
                it["reserved_quantity"] = float(reserved)
                it["available_quantity"] = float(avail)
            except Exception:
                it["reserved_quantity"] = 0
                it["available_quantity"] = float(stock)

    @staticmethod
    def _row_to_picker_item(row) -> Dict[str, Any]:
        return {
            "id": row.id,
            "reference": row.reference,
            "name": row.name,
            "category": row.category,
            "unit_price": row.unit_price,
            "min_stock": row.min_stock,
            "is_consumable": row.is_consumable,
            "default_unit": row.default_unit,
            "stock_quantity": float(row.stock_quantity)
            if row.stock_quantity is not None
            else 0.0,
            # availability filled later by _attach_availability
            "reserved_quantity": 0.0,
            "available_quantity": float(row.stock_quantity)
            if row.stock_quantity is not None
            else 0.0,
        }

    async def suggest_matches(
        self,
        query_text: str,
        machine_id: Optional[int] = None,
        threshold_low: float = 0.40,
        threshold_high: float = 0.80,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Smart fuzzy match using pg_trgm across name, reference, category.

        Returns suggestions with tier classification:
          - ``high``   ≥ threshold_high (auto-suggestion candidate)
          - ``medium`` between thresholds
          - ``low``    above ``threshold_low`` but below medium — surfaced but not highlighted

        When ``machine_id`` provided, adds a 0.1 similarity bonus for pieces
        already linked to that machine (machine-compatibility boost).
        """
        if not query_text or not query_text.strip():
            return []
        q = query_text.strip()

        # Compute similarity per piece — combine name/reference/category fields
        # and apply machine boost via CASE.
        machine_boost_case = (
            case(
                (piece_machine.c.machine_id == machine_id, 0.1),
                else_=0.0,
            )
            if machine_id is not None
            else case((1 == 1, 0.0), else_=0.0)
        )

        base_sim = func.greatest(
            func.similarity(Piece.name, q),
            func.similarity(func.coalesce(Piece.reference, ""), q),
            func.similarity(func.coalesce(Piece.category, ""), q),
        )
        score_col = (base_sim + machine_boost_case).label("score")
        machine_match_col = (machine_boost_case > 0).label("machine_match")

        stmt = (
            select(
                Piece.id,
                Piece.reference,
                Piece.name,
                Piece.category,
                score_col,
                machine_match_col,
            )
            .outerjoin(
                piece_machine,
                and_(
                    piece_machine.c.piece_id == Piece.id,
                    piece_machine.c.machine_id
                    == (machine_id if machine_id is not None else -1),
                ),
            )
            .where(base_sim >= threshold_low)
            .order_by(score_col.desc())
            .limit(limit)
        )

        rows = (await self.db.execute(stmt)).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            score = min(1.0, float(r.score))
            tier = (
                "high"
                if score >= threshold_high
                else ("medium" if score >= 0.60 else "low")
            )
            out.append(
                {
                    "piece_id": r.id,
                    "name": r.name,
                    "reference": r.reference,
                    "category": r.category,
                    "similarity": round(score, 4),
                    "tier": tier,
                    "machine_match": bool(r.machine_match),
                }
            )
        return out

    async def link_machine(self, piece_id: int, machine_id: int) -> bool:
        try:
            stmt = piece_machine.insert().values(
                piece_id=piece_id, machine_id=machine_id
            )
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Linked piece {piece_id} to machine {machine_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error linking piece {piece_id} to machine {machine_id}: {str(e)}"
            )
            raise

    async def unlink_machine(self, piece_id: int, machine_id: int) -> bool:
        try:
            stmt = delete(piece_machine).where(
                piece_machine.c.piece_id == piece_id,
                piece_machine.c.machine_id == machine_id,
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error unlinking piece {piece_id} from machine {machine_id}: {str(e)}"
            )
            raise

    async def get_linked_machines(self, piece_id: int) -> List[int]:
        try:
            stmt = select(piece_machine.c.machine_id).where(
                piece_machine.c.piece_id == piece_id
            )
            result = await self.db.execute(stmt)
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(
                f"Error fetching linked machines for piece {piece_id}: {str(e)}"
            )
            raise


# ---------------------------------------------------------------------------
# Standalone inventory readiness helpers (used by ML router)
# ---------------------------------------------------------------------------


async def batch_get_parts_readiness(db: AsyncSession) -> Dict[int, str]:
    """
    Single-query batch lookup: returns {machine_id: "OK"|"WARNING"|"CRITICAL"} for
    every machine that has at least one linked piece with a stock entry.

    Machines with no linked pieces are NOT in the result — callers should default to "OK".

    Status logic (per machine):
      CRITICAL  — any linked piece has stock.quantity == 0
      WARNING   — any linked piece has stock.quantity <= piece.min_stock (and none at 0)
      OK        — all linked pieces have stock above min_stock threshold
    """
    try:
        # LEFT JOIN stock so pieces with no stock row count as quantity=0
        min_stock_col = func.coalesce(Piece.min_stock, 5)
        qty_col = func.coalesce(Stock.quantity, 0)

        stmt = (
            select(
                piece_machine.c.machine_id,
                func.sum(case((qty_col == 0, 1), else_=0)).label("zero_count"),
                func.sum(
                    case(((qty_col > 0) & (qty_col <= min_stock_col), 1), else_=0)
                ).label("low_count"),
                func.count(piece_machine.c.piece_id).label("total_pieces"),
            )
            .join(Piece, Piece.id == piece_machine.c.piece_id)
            .outerjoin(Stock, Stock.piece_id == piece_machine.c.piece_id)
            .group_by(piece_machine.c.machine_id)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        readiness: Dict[int, str] = {}
        for row in rows:
            machine_id, zero_count, low_count, total_pieces = row
            if zero_count > 0:
                readiness[machine_id] = "CRITICAL"
            elif low_count > 0:
                readiness[machine_id] = "WARNING"
            else:
                readiness[machine_id] = "OK"

        return readiness

    except Exception as e:
        logger.error(f"Error in batch_get_parts_readiness: {str(e)}", exc_info=True)
        return {}


async def get_machine_parts_readiness(
    machine_id: int, db: AsyncSession
) -> Dict[str, Any]:
    """
    Single-machine parts readiness — used by unified-health endpoint.
    Returns detailed breakdown including part names and quantities.
    """
    try:
        min_stock_col = func.coalesce(Piece.min_stock, 5)
        qty_col = func.coalesce(Stock.quantity, 0)

        stmt = (
            select(
                Piece.id,
                Piece.name,
                qty_col.label("quantity"),
                min_stock_col.label("min_stock"),
            )
            .join(piece_machine, piece_machine.c.piece_id == Piece.id)
            .outerjoin(Stock, Stock.piece_id == Piece.id)
            .where(piece_machine.c.machine_id == machine_id)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        if not rows:
            return {
                "status": "OK",
                "parts_checked": 0,
                "critical_missing": [],
                "low_stock": [],
                "all_available": True,
            }

        critical_missing = []
        low_stock = []

        for piece_id, name, qty, min_stock in rows:
            if qty == 0:
                critical_missing.append({"id": piece_id, "name": name, "qty": qty})
            elif qty <= min_stock:
                low_stock.append(
                    {"id": piece_id, "name": name, "qty": qty, "min_stock": min_stock}
                )

        if critical_missing:
            status = "CRITICAL"
        elif low_stock:
            status = "WARNING"
        else:
            status = "OK"

        return {
            "status": status,
            "parts_checked": len(rows),
            "critical_missing": critical_missing,
            "low_stock": low_stock,
            "all_available": len(critical_missing) == 0 and len(low_stock) == 0,
        }

    except Exception as e:
        logger.error(
            f"Error in get_machine_parts_readiness for machine {machine_id}: {str(e)}",
            exc_info=True,
        )
        return {"status": "UNKNOWN", "error": "inventory_unavailable"}
