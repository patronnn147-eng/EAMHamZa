import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, JSON
from core.database import Base
import enum

logger = logging.getLogger(__name__)


class AuditActionType(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VIEW = "VIEW"


class AuditEntityType(str, enum.Enum):
    MACHINE = "machine"
    WORK_ORDER = "work_order"
    INTERVENTION = "intervention"
    PLANNING = "planning"
    USER = "user"
    ALERT = "alert"
    INVENTORY = "inventory"
    REPORT = "report"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    action_type = Column(Enum(AuditActionType), nullable=False, index=True)
    entity_type = Column(Enum(AuditEntityType), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    entity_name = Column(String(255), nullable=True)

    user_id = Column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    user_name = Column(String(255), nullable=True)

    changes = Column(JSON, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )


class AuditService:
    """Service for audit logging operations"""

    def __init__(self, db):
        self.db = db

    async def log_audit(
        self,
        entity_type: str,
        entity_id: int,
        action_type: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        entity_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry"""
        try:
            entry = AuditLog(
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                user_id=user_id,
                user_name=user_name,
                changes=changes,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
                description=description,
                created_at=datetime.utcnow(),
            )
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            logger.info(
                f"Audit log created: {entry.id} - {action_type} {entity_type}:{entity_id}"
            )
            return entry
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating audit log: {str(e)}")
            raise

    async def log_create(
        self,
        entity_type: str,
        entity_id: int,
        new_values: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        entity_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log entity creation"""
        return await self.log_audit(
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=AuditActionType.CREATE,
            user_id=user_id,
            user_name=user_name,
            new_values=new_values,
            entity_name=entity_name,
            ip_address=ip_address,
            description=f"Created {entity_type} {entity_id}",
        )

    async def log_update(
        self,
        entity_type: str,
        entity_id: int,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        entity_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log entity update"""
        changes = {}
        for key in set(list(old_values.keys()) + list(new_values.keys())):
            if old_values.get(key) != new_values.get(key):
                changes[key] = {"old": old_values.get(key), "new": new_values.get(key)}

        return await self.log_audit(
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=AuditActionType.UPDATE,
            user_id=user_id,
            user_name=user_name,
            old_values=old_values,
            new_values=new_values,
            changes=changes,
            entity_name=entity_name,
            ip_address=ip_address,
            description=f"Updated {entity_type} {entity_id}",
        )

    async def log_delete(
        self,
        entity_type: str,
        entity_id: int,
        old_values: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        entity_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log entity deletion"""
        return await self.log_audit(
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=AuditActionType.DELETE,
            user_id=user_id,
            user_name=user_name,
            old_values=old_values,
            entity_name=entity_name,
            ip_address=ip_address,
            description=f"Deleted {entity_type} {entity_id}",
        )

    async def log_view(
        self,
        entity_type: str,
        entity_id: int,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log entity view"""
        return await self.log_audit(
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=AuditActionType.VIEW,
            user_id=user_id,
            user_name=user_name,
            ip_address=ip_address,
        )

    def _apply_cheftech_scope(self, query, count_query):
        """Restrict queries to CHEFTECH-visible rows: only actions performed BY TECHNICIEN users.
        ChefTech supervises technicians, so the audit panel must show only technician activity —
        not ChefTech's own actions (e.g. assign) which also touch work_order entities."""
        from sqlalchemy import select
        from models.utilisateurs import Utilisateurs, UserRole

        technician_ids_subq = select(Utilisateurs.id).where(
            Utilisateurs.role == UserRole.TECHNICIEN
        )
        scope_clause = AuditLog.user_id.in_(technician_ids_subq)
        return query.where(scope_clause), count_query.where(scope_clause)

    async def get_audit_log(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        user_search: Optional[str] = None,
        user_role: Optional[Any] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get paginated audit log entries"""
        from sqlalchemy import select, func
        from models.utilisateurs import UserRole

        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
            count_query = count_query.where(AuditLog.entity_type == entity_type)

        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
            count_query = count_query.where(AuditLog.entity_id == entity_id)

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)

        if action_type:
            query = query.where(AuditLog.action_type == action_type)
            count_query = count_query.where(AuditLog.action_type == action_type)

        if from_date:
            query = query.where(AuditLog.created_at >= from_date)
            count_query = count_query.where(AuditLog.created_at >= from_date)

        if to_date:
            query = query.where(AuditLog.created_at <= to_date)
            count_query = count_query.where(AuditLog.created_at <= to_date)

        if user_search:
            # SQLite-compatible case-insensitive substring match
            pattern = f"%{user_search.lower()}%"
            query = query.where(func.lower(AuditLog.user_name).like(pattern))
            count_query = count_query.where(
                func.lower(AuditLog.user_name).like(pattern)
            )

        if user_role == UserRole.CHEFTECH:
            query, count_query = self._apply_cheftech_scope(query, count_query)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def get_audit_stats(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get audit statistics"""
        from sqlalchemy import select, func

        base_filter = []
        if entity_type:
            base_filter.append(AuditLog.entity_type == entity_type)
        if entity_id:
            base_filter.append(AuditLog.entity_id == entity_id)

        by_action_query = (
            select(AuditLog.action_type, func.count(AuditLog.id)).where(*base_filter)
            if base_filter
            else select(AuditLog.action_type, func.count(AuditLog.id))
        )
        by_action_query = by_action_query.group_by(AuditLog.action_type)

        action_result = await self.db.execute(by_action_query)
        by_action = {row[0]: row[1] for row in action_result.all()}

        by_user_query = (
            select(AuditLog.user_name, func.count(AuditLog.id)).where(*base_filter)
            if base_filter
            else select(AuditLog.user_name, func.count(AuditLog.id))
        )
        by_user_query = by_user_query.group_by(AuditLog.user_name)

        user_result = await self.db.execute(by_user_query)
        by_user = {row[0]: row[1] for row in user_result.all() if row[0]}

        by_entity_query = select(
            AuditLog.entity_type, func.count(AuditLog.id)
        ).group_by(AuditLog.entity_type)

        entity_result = await self.db.execute(by_entity_query)
        by_entity = {row[0]: row[1] for row in entity_result.all()}

        return {
            "by_action": by_action,
            "by_user": by_user,
            "by_entity": by_entity,
            "total": sum(by_action.values()),
        }

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: int,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get complete history for an entity"""
        from sqlalchemy import select

        query = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()
