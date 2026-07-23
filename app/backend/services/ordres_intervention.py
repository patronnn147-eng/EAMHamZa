import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ordres_intervention import OrdresIntervention
from services._crud_helpers import apply_filters as _apply_filters, apply_sort as _apply_sort

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class OrdresInterventionService:
    """Service layer for OrdresIntervention operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[OrdresIntervention]:
        """Create a new OrdresIntervention"""
        try:
            obj = OrdresIntervention(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created OrdresIntervention with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating OrdresIntervention: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[OrdresIntervention]:
        """Get OrdresIntervention by ID"""
        try:
            query = select(OrdresIntervention).where(OrdresIntervention.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching OrdresIntervention {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of OrdresInterventions"""
        try:
            query, count_query = _apply_filters(
                select(OrdresIntervention),
                select(func.count(OrdresIntervention.id)),
                OrdresIntervention,
                query_dict,
            )
            total = (await self.db.execute(count_query)).scalar()
            query = _apply_sort(query, sort, OrdresIntervention)
            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching OrdresIntervention list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[OrdresIntervention]:
        """Update OrdresIntervention"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"OrdresIntervention {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated OrdresIntervention {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating OrdresIntervention {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete OrdresIntervention"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"OrdresIntervention {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted OrdresIntervention {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting OrdresIntervention {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[OrdresIntervention]:
        """Get OrdresIntervention by any field"""
        try:
            if not hasattr(OrdresIntervention, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on OrdresIntervention"
                )
            result = await self.db.execute(
                select(OrdresIntervention).where(
                    getattr(OrdresIntervention, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching OrdresIntervention by {field_name}: {str(e)}"
            )
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[OrdresIntervention]:
        """Get list of OrdresInterventions filtered by field"""
        try:
            if not hasattr(OrdresIntervention, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on OrdresIntervention"
                )
            result = await self.db.execute(
                select(OrdresIntervention)
                .where(getattr(OrdresIntervention, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(OrdresIntervention.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(
                f"Error fetching OrdresInterventions by {field_name}: {str(e)}"
            )
            raise
