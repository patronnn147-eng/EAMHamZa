import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.utilisateurs import Utilisateurs

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class UtilisateursService:
    """Service layer for Utilisateurs operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, data: Dict[str, Any], _id: Optional[str] = None
    ) -> Optional[Utilisateurs]:
        """Create a new utilisateurs"""
        try:
            obj = Utilisateurs(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created utilisateurs with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating utilisateurs: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, _id=id)
            return obj is not None
        except Exception as e:
            logger.exception(
                f"Error checking ownership for utilisateurs {obj_id}: {str(e)}"
            )
            return False

    async def get_by_id(
        self, obj_id: int, _id: Optional[str] = None
    ) -> Optional[Utilisateurs]:
        """Get utilisateurs by ID (user can only see their own records)"""
        try:
            query = select(Utilisateurs).where(Utilisateurs.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching utilisateurs {obj_id}: {str(e)}")
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
        _id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of utilisateurss (user can only see their own records)"""
        try:
            query, count_query = self._apply_filters(
                select(Utilisateurs),
                select(func.count(Utilisateurs.id)),
                Utilisateurs,
                query_dict,
            )
            total = (await self.db.execute(count_query)).scalar()
            query = self._apply_sort(query, sort, Utilisateurs)
            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()
            return {"items": items, "total": total, "skip": skip, "limit": limit}
        except Exception as e:
            logger.exception(f"Error fetching utilisateurs list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any], id: Optional[str] = None
    ) -> Optional[Utilisateurs]:
        """Update utilisateurs (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, _id=id)
            if not obj:
                logger.warning(f"Utilisateurs {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated utilisateurs {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating utilisateurs {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, id: Optional[str] = None) -> bool:
        """Delete utilisateurs (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, _id=id)
            if not obj:
                logger.warning(f"Utilisateurs {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted utilisateurs {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting utilisateurs {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Utilisateurs]:
        """Get utilisateurs by any field"""
        try:
            if not hasattr(Utilisateurs, field_name):
                raise ValueError(f"Field {field_name} does not exist on Utilisateurs")
            result = await self.db.execute(
                select(Utilisateurs).where(
                    getattr(Utilisateurs, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Error fetching utilisateurs by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Utilisateurs]:
        """Get list of utilisateurss filtered by field"""
        try:
            if not hasattr(Utilisateurs, field_name):
                raise ValueError(f"Field {field_name} does not exist on Utilisateurs")
            result = await self.db.execute(
                select(Utilisateurs)
                .where(getattr(Utilisateurs, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Utilisateurs.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.exception(f"Error fetching utilisateurss by {field_name}: {str(e)}")
            raise
