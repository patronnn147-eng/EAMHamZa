import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_memories import AIMemories
from schemas.ai_memory import AIMemoryCreate, AIMemoryUpdate

logger = logging.getLogger(__name__)


class AIMemoryService:
    """Service layer for AI Memory operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: AIMemoryCreate, utilisateur_id: int = None) -> Optional[AIMemories]:
        """Create a new AI memory entry"""
        try:
            # Use provided user_id or from schema
            user_id = utilisateur_id or data.utilisateur_id
            if not user_id:
                raise ValueError("utilisateur_id is required")
            
            obj = AIMemories(
                utilisateur_id=user_id,
                memory_type=data.memory_type,
                memory_key=data.memory_key,
                memory_value=data.memory_value,
                success_count=data.success_count,
                failure_count=data.failure_count,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created AI memory with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating AI memory: {str(e)}")
            raise

    async def get_by_id(self, obj_id: str) -> Optional[AIMemories]:
        """Get memory by ID"""
        try:
            query = select(AIMemories).where(AIMemories.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching AI memory {obj_id}: {str(e)}")
            raise

    async def get_by_user(
        self,
        utilisateur_id: int,
        memory_type: Optional[str] = None,
    ) -> List[AIMemories]:
        """Get all memories for a user, optionally filtered by type"""
        try:
            query = select(AIMemories).where(
                AIMemories.utilisateur_id == utilisateur_id
            )
            if memory_type:
                query = query.where(AIMemories.memory_type == memory_type)
            query = query.order_by(AIMemories.updated_at.desc())
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching AI memories: {str(e)}")
            raise

    async def get_by_key(
        self,
        utilisateur_id: int,
        memory_key: str,
    ) -> Optional[AIMemories]:
        """Get a specific memory by user and key"""
        try:
            query = select(AIMemories).where(
                AIMemories.utilisateur_id == utilisateur_id,
                AIMemories.memory_key == memory_key,
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching AI memory by key: {str(e)}")
            raise

    async def update(
        self,
        obj_id: str,
        data: AIMemoryUpdate,
    ) -> Optional[AIMemories]:
        """Update an existing memory"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                return None
            
            if data.memory_value is not None:
                obj.memory_value = data.memory_value
            if data.success_count is not None:
                obj.success_count = data.success_count
            if data.failure_count is not None:
                obj.failure_count = data.failure_count
            
            obj.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated AI memory: {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating AI memory: {str(e)}")
            raise

    async def increment_success(self, obj_id: str) -> Optional[AIMemories]:
        """Increment success count and update timestamp"""
        obj = await self.get_by_id(obj_id)
        if obj:
            obj.success_count += 1
            obj.last_used = datetime.now()
            obj.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def increment_failure(self, obj_id: str) -> Optional[AIMemories]:
        """Increment failure count and update timestamp"""
        obj = await self.get_by_id(obj_id)
        if obj:
            obj.failure_count += 1
            obj.last_used = datetime.now()
            obj.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def delete(self, obj_id: str) -> bool:
        """Delete a memory"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted AI memory: {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting AI memory: {str(e)}")
            raise

    async def get_all_types(self, utilisateur_id: int) -> Dict[str, Any]:
        """Get summary of all memory types for a user"""
        memories = await self.get_by_user(utilisateur_id)
        
        summary = {
            "preference": [],
            "strategy": [],
            "failure": [],
        }
        
        for mem in memories:
            if mem.memory_type in summary:
                summary[mem.memory_type].append({
                    "key": mem.memory_key,
                    "value": mem.memory_value,
                    "success_count": mem.success_count,
                    "failure_count": mem.failure_count,
                })
        
        return summary