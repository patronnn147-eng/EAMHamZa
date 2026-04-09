import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ordres_intervention import Ordres_intervention

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Ordres_interventionService:
    """Service layer for Ordres_intervention operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Ordres_intervention]:
        """Create a new ordres_intervention"""
        try:
            obj = Ordres_intervention(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created ordres_intervention with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating ordres_intervention: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Ordres_intervention]:
        """Get ordres_intervention by ID"""
        try:
            query = select(Ordres_intervention).where(Ordres_intervention.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching ordres_intervention {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of ordres_interventions"""
        try:
            query = select(Ordres_intervention)
            count_query = select(func.count(Ordres_intervention.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Ordres_intervention, field):
                        query = query.where(getattr(Ordres_intervention, field) == value)
                        count_query = count_query.where(getattr(Ordres_intervention, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Ordres_intervention, field_name):
                        query = query.order_by(getattr(Ordres_intervention, field_name).desc())
                else:
                    if hasattr(Ordres_intervention, sort):
                        query = query.order_by(getattr(Ordres_intervention, sort))
            else:
                query = query.order_by(Ordres_intervention.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching ordres_intervention list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Ordres_intervention]:
        """Update ordres_intervention"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Ordres_intervention {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated ordres_intervention {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating ordres_intervention {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete ordres_intervention"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Ordres_intervention {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted ordres_intervention {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting ordres_intervention {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Ordres_intervention]:
        """Get ordres_intervention by any field"""
        try:
            if not hasattr(Ordres_intervention, field_name):
                raise ValueError(f"Field {field_name} does not exist on Ordres_intervention")
            result = await self.db.execute(
                select(Ordres_intervention).where(getattr(Ordres_intervention, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching ordres_intervention by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Ordres_intervention]:
        """Get list of ordres_interventions filtered by field"""
        try:
            if not hasattr(Ordres_intervention, field_name):
                raise ValueError(f"Field {field_name} does not exist on Ordres_intervention")
            result = await self.db.execute(
                select(Ordres_intervention)
                .where(getattr(Ordres_intervention, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Ordres_intervention.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching ordres_interventions by {field_name}: {str(e)}")
            raise