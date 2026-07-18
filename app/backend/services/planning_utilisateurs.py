import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.planning_utilisateurs import PlanningUtilisateurs

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class PlanningUtilisateursService:
    """Service layer for PlanningUtilisateurs operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[PlanningUtilisateurs]:
        """Create a new PlanningUtilisateurs"""
        try:
            obj = PlanningUtilisateurs(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created PlanningUtilisateurs with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating PlanningUtilisateurs: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[PlanningUtilisateurs]:
        """Get PlanningUtilisateurs by ID"""
        try:
            query = select(PlanningUtilisateurs).where(
                PlanningUtilisateurs.id == obj_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching PlanningUtilisateurs {obj_id}: {str(e)}")
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
        """Get paginated list of PlanningUtilisateurss"""
        try:
            query, count_query = self._apply_filters(
                select(PlanningUtilisateurs),
                select(func.count(PlanningUtilisateurs.id)),
                PlanningUtilisateurs,
                query_dict,
            )
            total = (await self.db.execute(count_query)).scalar()
            query = self._apply_sort(query, sort, PlanningUtilisateurs)
            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching PlanningUtilisateurs list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[PlanningUtilisateurs]:
        """Update PlanningUtilisateurs"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"PlanningUtilisateurs {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated PlanningUtilisateurs {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating PlanningUtilisateurs {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete PlanningUtilisateurs"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"PlanningUtilisateurs {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted PlanningUtilisateurs {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting PlanningUtilisateurs {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[PlanningUtilisateurs]:
        """Get PlanningUtilisateurs by any field"""
        try:
            if not hasattr(PlanningUtilisateurs, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on PlanningUtilisateurs"
                )
            result = await self.db.execute(
                select(PlanningUtilisateurs).where(
                    getattr(PlanningUtilisateurs, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching PlanningUtilisateurs by {field_name}: {str(e)}"
            )
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[PlanningUtilisateurs]:
        """Get list of PlanningUtilisateurss filtered by field"""
        try:
            if not hasattr(PlanningUtilisateurs, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on PlanningUtilisateurs"
                )
            result = await self.db.execute(
                select(PlanningUtilisateurs)
                .where(getattr(PlanningUtilisateurs, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(PlanningUtilisateurs.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(
                f"Error fetching PlanningUtilisateurss by {field_name}: {str(e)}"
            )
            raise
