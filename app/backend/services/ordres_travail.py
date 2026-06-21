import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ordres_travail import Ordres_travail

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Ordres_travailService:
    """Service layer for Ordres_travail operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Ordres_travail]:
        """Create a new ordres_travail"""
        try:
            # Handle None values for required fields
            processed_data = data.copy()
            if processed_data.get("titre") is None:
                processed_data["titre"] = (
                    f"Ordre de travail - {processed_data.get('priorite', 'MOYENNE')}"
                )
            if processed_data.get("description") is None:
                processed_data["description"] = "Description non spécifiée"

            obj = Ordres_travail(**processed_data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created ordres_travail with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating ordres_travail: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Ordres_travail]:
        """Get ordres_travail by ID"""
        try:
            query = select(Ordres_travail).where(Ordres_travail.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching ordres_travail {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of ordres_travails"""
        try:
            query = select(Ordres_travail)
            count_query = select(func.count(Ordres_travail.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Ordres_travail, field):
                        column = getattr(Ordres_travail, field)
                        # Convert value to appropriate type based on column type
                        column_type = str(column.type)
                        if "integer" in column_type.lower() and isinstance(value, str):
                            try:
                                value = int(value)
                            except ValueError:
                                continue
                        query = query.where(column == value)
                        count_query = count_query.where(column == value)

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                order_clauses = []
                for field in sort.split(","):
                    field = field.strip()
                    if field.startswith("-"):
                        field_name = field[1:]
                        if hasattr(Ordres_travail, field_name):
                            try:
                                order_clauses.append(
                                    getattr(Ordres_travail, field_name).desc()
                                )
                            except Exception:
                                pass
                    else:
                        if hasattr(Ordres_travail, field):
                            try:
                                order_clauses.append(getattr(Ordres_travail, field))
                            except Exception:
                                pass
                if order_clauses:
                    query = query.order_by(*order_clauses)
                else:
                    query = query.order_by(Ordres_travail.id.desc())
            else:
                query = query.order_by(Ordres_travail.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching ordres_travail list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Ordres_travail]:
        """Update ordres_travail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Ordres_travail {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated ordres_travail {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating ordres_travail {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete ordres_travail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Ordres_travail {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted ordres_travail {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting ordres_travail {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Ordres_travail]:
        """Get ordres_travail by any field"""
        try:
            if not hasattr(Ordres_travail, field_name):
                raise ValueError(f"Field {field_name} does not exist on Ordres_travail")
            result = await self.db.execute(
                select(Ordres_travail).where(
                    getattr(Ordres_travail, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching ordres_travail by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Ordres_travail]:
        """Get list of ordres_travails filtered by field"""
        try:
            if not hasattr(Ordres_travail, field_name):
                raise ValueError(f"Field {field_name} does not exist on Ordres_travail")
            result = await self.db.execute(
                select(Ordres_travail)
                .where(getattr(Ordres_travail, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Ordres_travail.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching ordres_travails by {field_name}: {str(e)}")
            raise
