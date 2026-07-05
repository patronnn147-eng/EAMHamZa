import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ordres import Ordres

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class OrdresService:
    """Service layer for Ordres operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Ordres]:
        """Create a new ordres"""
        try:
            obj = Ordres(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created ordres with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating ordres: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Ordres]:
        """Get ordres by ID"""
        try:
            query = select(Ordres).where(Ordres.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching ordres {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of ordress"""
        try:
            query = select(Ordres)
            count_query = select(func.count(Ordres.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Ordres, field):
                        query = query.where(getattr(Ordres, field) == value)
                        count_query = count_query.where(getattr(Ordres, field) == value)

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith("-"):
                    field_name = sort[1:]
                    if hasattr(Ordres, field_name):
                        query = query.order_by(getattr(Ordres, field_name).desc())
                else:
                    if hasattr(Ordres, sort):
                        query = query.order_by(getattr(Ordres, sort))
            else:
                query = query.order_by(Ordres.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.exception(f"Error fetching ordres list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Ordres]:
        """Update ordres"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Ordres {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated ordres {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating ordres {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete ordres"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Ordres {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted ordres {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting ordres {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Ordres]:
        """Get ordres by any field"""
        try:
            if not hasattr(Ordres, field_name):
                raise ValueError(f"Field {field_name} does not exist on Ordres")
            result = await self.db.execute(
                select(Ordres).where(getattr(Ordres, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching ordres by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Ordres]:
        """Get list of ordress filtered by field"""
        try:
            if not hasattr(Ordres, field_name):
                raise ValueError(f"Field {field_name} does not exist on Ordres")
            result = await self.db.execute(
                select(Ordres)
                .where(getattr(Ordres, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Ordres.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(f"Error fetching ordress by {field_name}: {str(e)}")
            raise
