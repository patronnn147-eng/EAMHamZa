import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.planning_OrdresTravail import PlanningOrdresTravail

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class PlanningOrdresTravailService:
    """Service layer for PlanningOrdresTravail operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[PlanningOrdresTravail]:
        """Create a new planning_OrdresTravail"""
        try:
            obj = PlanningOrdresTravail(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created planning_OrdresTravail with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating planning_OrdresTravail: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[PlanningOrdresTravail]:
        """Get planning_OrdresTravail by ID"""
        try:
            query = select(PlanningOrdresTravail).where(
                PlanningOrdresTravail.id == obj_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching planning_OrdresTravail {obj_id}: {str(e)}"
            )
            raise

    @staticmethod
    def _apply_filters(query, count_query, model, query_dict):
        """Apply equality filters from query_dict to both queries."""
        if not query_dict:
            return query, count_query
        for field, value in query_dict.items():
            if hasattr(model, field):
                condition = getattr(model, field) == value
                query = query.where(condition)
                count_query = count_query.where(condition)
        return query, count_query

    @staticmethod
    def _apply_sort(query, sort, model):
        """Apply ordering to query; defaults to id.desc()."""
        if not sort:
            return query.order_by(model.id.desc())
        if sort.startswith("-"):
            field_name = sort[1:]
            if hasattr(model, field_name):
                return query.order_by(getattr(model, field_name).desc())
        elif hasattr(model, sort):
            return query.order_by(getattr(model, sort))
        return query.order_by(model.id.desc())

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of planning_OrdresTravails"""
        try:
            query, count_query = self._apply_filters(
                select(PlanningOrdresTravail),
                select(func.count(PlanningOrdresTravail.id)),
                PlanningOrdresTravail,
                query_dict,
            )
            total = (await self.db.execute(count_query)).scalar()
            query = self._apply_sort(query, sort, PlanningOrdresTravail)
            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching planning_OrdresTravail list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[PlanningOrdresTravail]:
        """Update planning_OrdresTravail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"PlanningOrdresTravail {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated planning_OrdresTravail {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Error updating planning_OrdresTravail {obj_id}: {str(e)}"
            )
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete planning_OrdresTravail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(
                    f"PlanningOrdresTravail {obj_id} not found for deletion"
                )
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted planning_OrdresTravail {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Error deleting planning_OrdresTravail {obj_id}: {str(e)}"
            )
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[PlanningOrdresTravail]:
        """Get planning_OrdresTravail by any field"""
        try:
            if not hasattr(PlanningOrdresTravail, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on PlanningOrdresTravail"
                )
            result = await self.db.execute(
                select(PlanningOrdresTravail).where(
                    getattr(PlanningOrdresTravail, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching planning_OrdresTravail by {field_name}: {str(e)}"
            )
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[PlanningOrdresTravail]:
        """Get list of planning_OrdresTravails filtered by field"""
        try:
            if not hasattr(PlanningOrdresTravail, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on PlanningOrdresTravail"
                )
            result = await self.db.execute(
                select(PlanningOrdresTravail)
                .where(getattr(PlanningOrdresTravail, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(PlanningOrdresTravail.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(
                f"Error fetching planning_OrdresTravails by {field_name}: {str(e)}"
            )
            raise
