import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.archives import Archives

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class ArchivesService:
    """Service layer for Archives operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Archives]:
        """Create a new archives"""
        try:
            obj = Archives(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created archives with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating archives: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Archives]:
        """Get archives by ID"""
        try:
            query = select(Archives).where(Archives.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching archives {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of archivess"""
        try:
            query = select(Archives)
            count_query = select(func.count(Archives.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Archives, field):
                        query = query.where(getattr(Archives, field) == value)
                        count_query = count_query.where(
                            getattr(Archives, field) == value
                        )

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith("-"):
                    field_name = sort[1:]
                    if hasattr(Archives, field_name):
                        query = query.order_by(getattr(Archives, field_name).desc())
                else:
                    if hasattr(Archives, sort):
                        query = query.order_by(getattr(Archives, sort))
            else:
                query = query.order_by(Archives.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.exception(f"Error fetching archives list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Archives]:
        """Update archives"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Archives {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated archives {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating archives {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete archives"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Archives {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted archives {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting archives {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Archives]:
        """Get archives by any field"""
        try:
            if not hasattr(Archives, field_name):
                raise ValueError(f"Field {field_name} does not exist on Archives")
            result = await self.db.execute(
                select(Archives).where(getattr(Archives, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching archives by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Archives]:
        """Get list of archivess filtered by field"""
        try:
            if not hasattr(Archives, field_name):
                raise ValueError(f"Field {field_name} does not exist on Archives")
            result = await self.db.execute(
                select(Archives)
                .where(getattr(Archives, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Archives.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(f"Error fetching archivess by {field_name}: {str(e)}")
            raise
