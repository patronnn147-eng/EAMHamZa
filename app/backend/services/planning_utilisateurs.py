import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.planning_utilisateurs import Planning_utilisateurs

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Planning_utilisateursService:
    """Service layer for Planning_utilisateurs operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Planning_utilisateurs]:
        """Create a new planning_utilisateurs"""
        try:
            obj = Planning_utilisateurs(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created planning_utilisateurs with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating planning_utilisateurs: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Planning_utilisateurs]:
        """Get planning_utilisateurs by ID"""
        try:
            query = select(Planning_utilisateurs).where(
                Planning_utilisateurs.id == obj_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching planning_utilisateurs {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of planning_utilisateurss"""
        try:
            query = select(Planning_utilisateurs)
            count_query = select(func.count(Planning_utilisateurs.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Planning_utilisateurs, field):
                        query = query.where(
                            getattr(Planning_utilisateurs, field) == value
                        )
                        count_query = count_query.where(
                            getattr(Planning_utilisateurs, field) == value
                        )

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith("-"):
                    field_name = sort[1:]
                    if hasattr(Planning_utilisateurs, field_name):
                        query = query.order_by(
                            getattr(Planning_utilisateurs, field_name).desc()
                        )
                else:
                    if hasattr(Planning_utilisateurs, sort):
                        query = query.order_by(getattr(Planning_utilisateurs, sort))
            else:
                query = query.order_by(Planning_utilisateurs.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching planning_utilisateurs list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Planning_utilisateurs]:
        """Update planning_utilisateurs"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Planning_utilisateurs {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated planning_utilisateurs {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating planning_utilisateurs {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete planning_utilisateurs"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Planning_utilisateurs {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted planning_utilisateurs {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting planning_utilisateurs {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Planning_utilisateurs]:
        """Get planning_utilisateurs by any field"""
        try:
            if not hasattr(Planning_utilisateurs, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on Planning_utilisateurs"
                )
            result = await self.db.execute(
                select(Planning_utilisateurs).where(
                    getattr(Planning_utilisateurs, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                f"Error fetching planning_utilisateurs by {field_name}: {str(e)}"
            )
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Planning_utilisateurs]:
        """Get list of planning_utilisateurss filtered by field"""
        try:
            if not hasattr(Planning_utilisateurs, field_name):
                raise ValueError(
                    f"Field {field_name} does not exist on Planning_utilisateurs"
                )
            result = await self.db.execute(
                select(Planning_utilisateurs)
                .where(getattr(Planning_utilisateurs, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Planning_utilisateurs.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(
                f"Error fetching planning_utilisateurss by {field_name}: {str(e)}"
            )
            raise
