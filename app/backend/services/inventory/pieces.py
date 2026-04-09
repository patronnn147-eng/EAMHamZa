import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.pieces import Piece
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
            count_query = select(lambda: Piece.id)

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
