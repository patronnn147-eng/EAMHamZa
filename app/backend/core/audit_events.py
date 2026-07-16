import logging
from typing import Dict, Any, Optional
from sqlalchemy import event, inspect

logger = logging.getLogger(__name__)


AUDITABLE_MODELS = {
    "machines": "machine",
    "OrdresTravail": "work_order",
    "OrdresIntervention": "intervention",
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


def _audit_after_flush_listener(session, flush_context):
    """SQLAlchemy after_flush listener — logs CREATE/UPDATE/DELETE for auditable models."""
    for obj in session.new:
        try:
            mapper = inspect(type(obj))
            entity_type = AUDITABLE_MODELS.get(mapper.mapped_table.name)
            if entity_type:
                logger.info(f"CREATE: {entity_type}:{obj.id}")
        except Exception as e:
            logger.warning(f"Error auditing create: {e}")

    for obj in session.dirty:
        try:
            mapper = inspect(type(obj))
            entity_type = AUDITABLE_MODELS.get(mapper.mapped_table.name)
            if entity_type and session.is_modified(obj):
                logger.info(f"UPDATE: {entity_type}:{obj.id}")
        except Exception as e:
            logger.warning(f"Error auditing update: {e}")

    for obj in session.deleted:
        try:
            mapper = inspect(type(obj))
            entity_type = AUDITABLE_MODELS.get(mapper.mapped_table.name)
            if entity_type:
                logger.info(f"DELETE: {entity_type}:{obj.id}")
        except Exception as e:
            logger.warning(f"Error auditing delete: {e}")


def setup_audit_listeners():
    """Register the after_flush audit listener on the SQLAlchemy target.

    This function registers an after_flush listener to automatically log
    CREATE, UPDATE, DELETE operations for auditable models.
    """
    target = inspect(inspect) if hasattr(inspect, "mapped_table") else object
    event.listen(target, "after_flush", _audit_after_flush_listener)
    logger.info("Audit listeners registered successfully")


def manual_audit_log(
    entity_type: str,
    entity_id: int,
    action: str,
    _user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    _changes: Optional[Dict[str, Any]] = None,
    _old_values: Optional[Dict[str, Any]] = None,
    _new_values: Optional[Dict[str, Any]] = None,
):
    """Helper for manual audit logging from route handlers

    Usage in routes:
        await manual_audit_log(
            entity_type="machine",
            entity_id=machine.id,
            action="UPDATE",
            _user_id=user.id,
            user_name=user.nom,
            _old_values=old_machine.__dict__,
            _new_values=new_machine.__dict__
        )
    """
    logger.info(f"Manual audit: {action} {entity_type}:{entity_id} by {user_name}")
