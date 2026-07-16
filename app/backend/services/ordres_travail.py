import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.OrdresTravail import OrdresTravail

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class OrdresTravailService:
    """Service layer for OrdresTravail operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[OrdresTravail]:
        """Create a new OrdresTravail"""
        try:
            # Handle None values for required fields
            processed_data = data.copy()
            if processed_data.get("titre") is None:
                processed_data["titre"] = (
                    f"Ordre de travail - {processed_data.get('priorite', 'MOYENNE')}"
                )
            if processed_data.get("description") is None:
                processed_data["description"] = "Description non spécifiée"

            obj = OrdresTravail(**processed_data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created OrdresTravail with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating OrdresTravail: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[OrdresTravail]:
        """Get OrdresTravail by ID"""
        try:
            query = select(OrdresTravail).where(OrdresTravail.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching OrdresTravail {obj_id}: {str(e)}")
            raise

    @staticmethod
    def _apply_filters(query, count_query, query_dict: Optional[Dict[str, Any]]):
        """Apply equality filters from query_dict to both select and count queries."""
        if not query_dict:
            return query, count_query
        for field, value in query_dict.items():
            if not hasattr(OrdresTravail, field):
                continue
            column = getattr(OrdresTravail, field)
            if "integer" in str(column.type).lower() and isinstance(value, str):
                try:
                    value = int(value)
                except ValueError:
                    continue
            query = query.where(column == value)
            count_query = count_query.where(column == value)
        return query, count_query

    @staticmethod
    def _apply_sort(query, sort: Optional[str]):
        """Apply ORDER BY clauses from a comma-separated sort string (prefix '-' for desc)."""
        if not sort:
            return query.order_by(OrdresTravail.id.desc())
        order_clauses = []
        for field in sort.split(","):
            field = field.strip()
            if field.startswith("-"):
                field_name = field[1:]
                if hasattr(OrdresTravail, field_name):
                    try:
                        order_clauses.append(getattr(OrdresTravail, field_name).desc())
                    except Exception:
                        pass
            elif hasattr(OrdresTravail, field):
                try:
                    order_clauses.append(getattr(OrdresTravail, field))
                except Exception:
                    pass
        return query.order_by(*order_clauses) if order_clauses else query.order_by(OrdresTravail.id.desc())

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of OrdresTravails"""
        try:
            query, count_query = self._apply_filters(
                select(OrdresTravail), select(func.count(OrdresTravail.id)), query_dict
            )
            total = (await self.db.execute(count_query)).scalar()
            query = self._apply_sort(query, sort)
            items = (await self.db.execute(query.offset(skip).limit(limit))).scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching OrdresTravail list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[OrdresTravail]:
        """Update OrdresTravail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"OrdresTravail {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated OrdresTravail {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating OrdresTravail {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete OrdresTravail"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"OrdresTravail {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted OrdresTravail {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting OrdresTravail {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[OrdresTravail]:
        """Get OrdresTravail by any field"""
        try:
            if not hasattr(OrdresTravail, field_name):
                raise ValueError(f"Field {field_name} does not exist on OrdresTravail")
            result = await self.db.execute(
                select(OrdresTravail).where(
                    getattr(OrdresTravail, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching OrdresTravail by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[OrdresTravail]:
        """Get list of OrdresTravails filtered by field"""
        try:
            if not hasattr(OrdresTravail, field_name):
                raise ValueError(f"Field {field_name} does not exist on OrdresTravail")
            result = await self.db.execute(
                select(OrdresTravail)
                .where(getattr(OrdresTravail, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(OrdresTravail.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(
                f"Error fetching OrdresTravails by {field_name}: {str(e)}"
            )
            raise
