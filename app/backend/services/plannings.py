import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.plannings import Plannings

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class PlanningsService:
    """Service layer for Plannings operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Plannings]:
        """Create a new plannings"""
        try:
            obj = Plannings(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created plannings with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating plannings: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Plannings]:
        """Get plannings by ID"""
        try:
            query = select(Plannings).where(Plannings.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching plannings {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of planningss"""
        try:
            query = select(Plannings)
            count_query = select(func.count(Plannings.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Plannings, field):
                        query = query.where(getattr(Plannings, field) == value)
                        count_query = count_query.where(getattr(Plannings, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Plannings, field_name):
                        query = query.order_by(getattr(Plannings, field_name).desc())
                else:
                    if hasattr(Plannings, sort):
                        query = query.order_by(getattr(Plannings, sort))
            else:
                query = query.order_by(Plannings.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching plannings list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Plannings]:
        """Update plannings"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Plannings {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated plannings {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating plannings {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete plannings"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Plannings {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted plannings {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting plannings {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Plannings]:
        """Get plannings by any field"""
        try:
            if not hasattr(Plannings, field_name):
                raise ValueError(f"Field {field_name} does not exist on Plannings")
            result = await self.db.execute(
                select(Plannings).where(getattr(Plannings, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching plannings by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Plannings]:
        """Get list of planningss filtered by field"""
        try:
            if not hasattr(Plannings, field_name):
                raise ValueError(f"Field {field_name} does not exist on Plannings")
            result = await self.db.execute(
                select(Plannings)
                .where(getattr(Plannings, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Plannings.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching planningss by {field_name}: {str(e)}")
            raise