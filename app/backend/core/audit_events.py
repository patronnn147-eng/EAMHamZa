import logging
from typing import Dict, Any, Optional
from sqlalchemy import event, inspect
from sqlalchemy.orm import Mapper
from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


AUDITABLE_MODELS = {
    "machines": "machine",
    "ordres_travail": "work_order",
    "ordres_intervention": "intervention",
    "plannings": "planning",
    "utilisateurs": "user",
    "alertes": "alert",
    "pieces": "inventory",
}


def get_entity_name(obj: Any, model_name: str) -> Optional[str]:
    """Get a human-readable name for an entity"""
    if hasattr(obj, "nom"):
        return obj.nom
    if hasattr(obj, "titre"):
        return obj.titre
    if hasattr(obj, "name"):
        return obj.name
    if hasattr(obj, "label"):
        return obj.label
    return f"{model_name} {obj.id}"


async def audit_after_flush(mapper: Mapper, connection, flush_event: Any):
    """Process pending audit entries after flush"""
    from services.audit import AuditService

    async with AsyncSessionLocal() as db:
        AuditService(db)

        for obj in flush_event.mapper.mapped_table.c:
            pass


def setup_audit_listeners():
    """Setup SQLAlchemy event listeners for automatic audit logging

    This function registers before_flush listeners on all mappers
    to automatically log CREATE, UPDATE, DELETE operations.
    """

    @event.listens_for(
        inspect(inspect) if hasattr(inspect, "mapped_table") else object, "after_flush"
    )
    def audit_after_flush_listener(session, flush_context):
        """Listen to after_flush to capture changes"""

        for obj in session.new:
            try:
                mapper = inspect(type(obj))
                table_name = mapper.mapped_table.name
                entity_type = AUDITABLE_MODELS.get(table_name)

                if entity_type:
                    {
                        col.key: getattr(obj, col.key)
                        for col in mapper.columns
                        if not col.key.startswith("_")
                    }

                    logger.info(f"CREATE: {entity_type}:{obj.id}")
            except Exception as e:
                logger.warning(f"Error auditing create: {e}")

        for obj in session.dirty:
            try:
                mapper = inspect(type(obj))
                table_name = mapper.mapped_table.name
                entity_type = AUDITABLE_MODELS.get(table_name)

                if entity_type and session.is_modified(obj):
                    {
                        col.key: inspect(obj).attrs[col.key].history.deleted[0]
                        if col.key in inspect(obj).attrs
                        and inspect(obj).attrs[col.key].history.deleted
                        else None
                        for col in mapper.columns
                        if not col.key.startswith("_")
                    }
                    {
                        col.key: getattr(obj, col.key)
                        for col in mapper.columns
                        if not col.key.startswith("_")
                    }

                    logger.info(f"UPDATE: {entity_type}:{obj.id}")
            except Exception as e:
                logger.warning(f"Error auditing update: {e}")

        for obj in session.deleted:
            try:
                mapper = inspect(type(obj))
                table_name = mapper.mapped_table.name
                entity_type = AUDITABLE_MODELS.get(table_name)

                if entity_type:
                    {
                        col.key: getattr(obj, col.key)
                        for col in mapper.columns
                        if not col.key.startswith("_")
                    }

                    logger.info(f"DELETE: {entity_type}:{obj.id}")
            except Exception as e:
                logger.warning(f"Error auditing delete: {e}")

    logger.info("Audit listeners registered successfully")


def manual_audit_log(
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
):
    """Helper for manual audit logging from route handlers

    Usage in routes:
        await manual_audit_log(
            entity_type="machine",
            entity_id=machine.id,
            action="UPDATE",
            user_id=user.id,
            user_name=user.nom,
            old_values=old_machine.__dict__,
            new_values=new_machine.__dict__
        )
    """
    logger.info(f"Manual audit: {action} {entity_type}:{entity_id} by {user_name}")
