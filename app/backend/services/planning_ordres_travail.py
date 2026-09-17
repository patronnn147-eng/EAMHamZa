import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.planning_ordres_travail import Planning_ordres_travail

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Planning_ordres_travailService:
    """Service layer for Planning_ordres_travail operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Planning_ordres_travail]:
        """Create a new planning_ordres_travail"""
        try:
            obj = Planning_ordres_travail(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created planning_ordres_travail with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating planning_ordres_travail: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Planning_ordres_travail]:
        """Get planning_ordres_travail by ID"""
        try:
            query = select(Planning_ordres_travail).where(
                Planning_ordres_travail.id == obj_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching planning_ordres_travail {obj_id}: {str(e)}"
            )
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of planning_ordres_travails"""
        try:
            query = select(Planning_ordres_travail)
            count_query = select(func.count(Planning_ordres_travail.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Planning_ordres_travail, field):
                        query = query.where(
                            getattr(Planning_ordres_travail, field) == value
                        )
                        count_query = count_query.where(
                            getattr(Planning_ordres_travail, field) == value
                        )

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith("-"):
                    field_name = sort[1:]
                    if hasattr(Planning_ordres_travail, field_name):
                        query = query.order_by(
                            getattr(Planning_ordres_travail, field_name).desc()
                        )
                else:
                    if hasattr(Planning_ordres_travail, sort):
                        query = query.order_by(getattr(Planning_ordres_travail, sort))
            else:
                query = query.order_by(Planning_ordres_travail.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.exception(f"Error fetching planning_ordres_travail list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Planning_ordres_travail]:
        """Update planning_ordres_travail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Planning_ordres_travail {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated planning_ordres_travail {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Error updating planning_ordres_travail {obj_id}: {str(e)}"
            )
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete planning_ordres_travail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(
                    f"Planning_ordres_travail {obj_id} not found for deletion"
                )
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted planning_ordres_travail {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Error deleting planning_ordres_travail {obj_id}: {str(e)}"
            )
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Planning_ordres_travail]:
        """Get planning_ordres_travail by any field"""
        try:
            if not hasattr(Planning_ordres_travail, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on Planning_ordres_travail"
                )
            result = await self.db.execute(
                select(Planning_ordres_travail).where(
                    getattr(Planning_ordres_travail, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                f"Error fetching planning_ordres_travail by {field_name}: {str(e)}"
            )
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Planning_ordres_travail]:
        """Get list of planning_ordres_travails filtered by field"""
        try:
            if not hasattr(Planning_ordres_travail, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on Planning_ordres_travail"
                )
            result = await self.db.execute(
                select(Planning_ordres_travail)
                .where(getattr(Planning_ordres_travail, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Planning_ordres_travail.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(
                f"Error fetching planning_ordres_travails by {field_name}: {str(e)}"
            )
            raise
