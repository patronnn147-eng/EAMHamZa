import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.pieces import Piece
from models.stock import Stock
from models.mouvement_stock import MouvementStock
from models.piece_machine import piece_machine

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
            count_query = select(func.count(Piece.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Piece, field):
                        query = query.where(getattr(Piece, field) == value)
                        count_query = count_query.where(getattr(Piece, field) == value)

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
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

    async def link_machine(self, piece_id: int, machine_id: int) -> bool:
        try:
            stmt = piece_machine.insert().values(piece_id=piece_id, machine_id=machine_id)
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Linked piece {piece_id} to machine {machine_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error linking piece {piece_id} to machine {machine_id}: {str(e)}")
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
            logger.error(f"Error unlinking piece {piece_id} from machine {machine_id}: {str(e)}")
            raise

    async def get_linked_machines(self, piece_id: int) -> List[int]:
        try:
            stmt = select(piece_machine.c.machine_id).where(piece_machine.c.piece_id == piece_id)
            result = await self.db.execute(stmt)
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching linked machines for piece {piece_id}: {str(e)}")
            raise


class StockService:
    """Service layer for Stock operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stock_levels(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Get current stock levels for all pieces with pagination."""
        try:
            count_query = select(func.count(Stock.id)).join(Piece, Stock.piece_id == Piece.id)
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
                )
                .join(Piece, Stock.piece_id == Piece.id)
                .order_by(Piece.name)
                .offset(skip).limit(limit)
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
            logger.error(f"Error fetching stock levels: {str(e)}")
            raise

    async def add_stock(self, piece_id: int, quantity: int, reference: Optional[str] = None) -> Dict[str, Any]:
        """Add stock for a piece. Creates stock entry if none exists."""
        try:
            # Get or create stock entry
            query = select(Stock).where(Stock.piece_id == piece_id)
            result = await self.db.execute(query)
            stock = result.scalar_one_or_none()

            if stock:
                stock.quantity += quantity
            else:
                stock = Stock(piece_id=piece_id, quantity=quantity)
                self.db.add(stock)

            # Record movement
            movement = MouvementStock(
                piece_id=piece_id,
                quantity=quantity,
                movement_type="in",
                reference=reference,
            )
            self.db.add(movement)

            await self.db.commit()
            await self.db.refresh(stock)
            logger.info(f"Added {quantity} stock for piece {piece_id}")
            return {"id": stock.id, "piece_id": stock.piece_id, "quantity": stock.quantity}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding stock for piece {piece_id}: {str(e)}")
            raise

    async def consume_stock(
        self, piece_id: int, quantity: int, intervention_id: Optional[int] = None, reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consume stock for a piece (e.g., used in an intervention)."""
        try:
            query = select(Stock).where(Stock.piece_id == piece_id)
            result = await self.db.execute(query)
            stock = result.scalar_one_or_none()

            if not stock:
                raise ValueError(f"No stock entry found for piece {piece_id}")
            if stock.quantity < quantity:
                raise ValueError(
                    f"Insufficient stock for piece {piece_id}: have {stock.quantity}, need {quantity}"
                )

            stock.quantity -= quantity

            ref = reference or (f"intervention-{intervention_id}" if intervention_id else None)
            movement = MouvementStock(
                piece_id=piece_id,
                quantity=quantity,
                movement_type="out",
                reference=ref,
            )
            self.db.add(movement)

            await self.db.commit()
            await self.db.refresh(stock)
            logger.info(f"Consumed {quantity} stock for piece {piece_id}")
            return {"id": stock.id, "piece_id": stock.piece_id, "quantity": stock.quantity}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error consuming stock for piece {piece_id}: {str(e)}")
            raise

    async def get_alerts(self, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Get low-stock alerts with pagination."""
        try:
            count_query = (
                select(func.count(Stock.piece_id))
                .join(Piece, Stock.piece_id == Piece.id)
                .where(Stock.quantity < Piece.min_stock)
            )
            count_result = await self.db.execute(count_query)
            total = count_result.scalar() or 0

            query = (
                select(
                    Stock.piece_id,
                    Piece.name.label("piece_name"),
                    Piece.reference.label("piece_reference"),
                    Stock.quantity.label("current_quantity"),
                    Piece.min_stock,
                )
                .join(Piece, Stock.piece_id == Piece.id)
                .where(Stock.quantity < Piece.min_stock)
                .order_by(Stock.quantity)
                .offset(skip).limit(limit)
            )
            result = await self.db.execute(query)
            rows = result.fetchall()
            items = [
                {
                    "piece_id": row.piece_id,
                    "piece_name": row.piece_name,
                    "piece_reference": row.piece_reference,
                    "current_quantity": row.current_quantity,
                    "min_stock": row.min_stock,
                    "deficit": row.min_stock - row.current_quantity,
                }
                for row in rows
            ]
            return {"items": items, "total": total}
        except Exception as e:
            logger.error(f"Error fetching stock alerts: {str(e)}")
            raise

    async def get_movements(self, piece_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Get stock movement history with pagination."""
        try:
            count_query = select(func.count(MouvementStock.id)).join(Piece, MouvementStock.piece_id == Piece.id)
            if piece_id:
                count_query = count_query.where(MouvementStock.piece_id == piece_id)
            count_result = await self.db.execute(count_query)
            total = count_result.scalar() or 0

            query = (
                select(
                    MouvementStock.id,
                    MouvementStock.piece_id,
                    MouvementStock.quantity,
                    MouvementStock.movement_type,
                    MouvementStock.reference,
                    MouvementStock.created_at,
                    Piece.name.label("piece_name"),
                )
                .join(Piece, MouvementStock.piece_id == Piece.id)
                .order_by(MouvementStock.id.desc())
                .offset(skip).limit(limit)
            )
            if piece_id:
                query = query.where(MouvementStock.piece_id == piece_id)
            result = await self.db.execute(query)
            rows = result.fetchall()
            items = [
                {
                    "id": row.id,
                    "piece_id": row.piece_id,
                    "quantity": row.quantity,
                    "movement_type": row.movement_type,
                    "reference": row.reference,
                    "created_at": row.created_at,
                    "piece_name": row.piece_name,
                }
                for row in rows
            ]
            return {"items": items, "total": total}
        except Exception as e:
            logger.error(f"Error fetching stock movements: {str(e)}")
            raise
