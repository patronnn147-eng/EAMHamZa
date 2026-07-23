import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.maintenances_planifiees import MaintenancesPlanifiees
from services._crud_helpers import apply_filters as _apply_filters, apply_sort as _apply_sort

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class MaintenancesPlanifieesService:
    """Service layer for MaintenancesPlanifiees operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[MaintenancesPlanifiees]:
        """Create a new MaintenancesPlanifiees"""
        try:
            obj = MaintenancesPlanifiees(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created MaintenancesPlanifiees with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating MaintenancesPlanifiees: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[MaintenancesPlanifiees]:
        """Get MaintenancesPlanifiees by ID"""
        try:
            query = select(MaintenancesPlanifiees).where(
                MaintenancesPlanifiees.id == obj_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching MaintenancesPlanifiees {obj_id}: {str(e)}"
            )
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of MaintenancesPlanifieess"""
        try:
            query, count_query = _apply_filters(
                select(MaintenancesPlanifiees),
                select(func.count(MaintenancesPlanifiees.id)),
                MaintenancesPlanifiees,
                query_dict,
            )
            total = (await self.db.execute(count_query)).scalar()
            query = _apply_sort(query, sort, MaintenancesPlanifiees)
            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching MaintenancesPlanifiees list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[MaintenancesPlanifiees]:
        """Update MaintenancesPlanifiees"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"MaintenancesPlanifiees {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated MaintenancesPlanifiees {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Error updating MaintenancesPlanifiees {obj_id}: {str(e)}"
            )
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete MaintenancesPlanifiees"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(
                    f"MaintenancesPlanifiees {obj_id} not found for deletion"
                )
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted MaintenancesPlanifiees {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Error deleting MaintenancesPlanifiees {obj_id}: {str(e)}"
            )
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[MaintenancesPlanifiees]:
        """Get MaintenancesPlanifiees by any field"""
        try:
            if not hasattr(MaintenancesPlanifiees, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on MaintenancesPlanifiees"
                )
            result = await self.db.execute(
                select(MaintenancesPlanifiees).where(
                    getattr(MaintenancesPlanifiees, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching MaintenancesPlanifiees by {field_name}: {str(e)}"
            )
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[MaintenancesPlanifiees]:
        """Get list of MaintenancesPlanifieess filtered by field"""
        try:
            if not hasattr(MaintenancesPlanifiees, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on MaintenancesPlanifiees"
                )
            result = await self.db.execute(
                select(MaintenancesPlanifiees)
                .where(getattr(MaintenancesPlanifiees, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(MaintenancesPlanifiees.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(
                f"Error fetching MaintenancesPlanifieess by {field_name}: {str(e)}"
            )
            raise
