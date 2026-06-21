import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.notifications import Notifications
from models.utilisateurs import Utilisateurs, UserRole

logger = logging.getLogger(__name__)


WORKFLOW_NOTIFICATIONS = {
    "WORK_ORDER_CREATED": {
        "roles": [UserRole.CHEFTECH, UserRole.CHETOP],
        "message": "Nouvel ordre de travail créé: {title}",
    },
    "WORK_ORDER_ASSIGNED": {
        "roles": [UserRole.TECHNICIEN],
        "message": "Ordre de travail assigné: {title}",
    },
    "WORK_ORDER_COMPLETED": {
        "roles": [UserRole.CHEFTECH, UserRole.CHETOP],
        "message": "Ordre de travail terminé: {title}",
    },
    "WORK_ORDER_UPDATED": {
        "roles": [UserRole.CHEFTECH, UserRole.CHETOP, UserRole.TECHNICIEN],
        "message": "Ordre de travail mis à jour: {title}",
    },
    "INTERVENTION_REQUESTED": {
        "roles": [UserRole.CHEFTECH],
        "message": "Demande d'intervention reçue: {machine}",
    },
    "INTERVENTION_APPROVED": {
        "roles": [UserRole.TECHNICIEN, UserRole.CHEFTECH],
        "message": "Intervention approuvée: {machine}",
    },
    "INTERVENTION_REJECTED": {
        "roles": [UserRole.CHETOP],
        "message": "Intervention rejetée: {machine}",
    },
    "INTERVENTION_COMPLETED": {
        "roles": [UserRole.CHEFTECH, UserRole.CHETOP],
        "message": "Intervention terminée: {machine}",
    },
    "ALERT_CREATED": {
        "roles": [UserRole.CHEFTECH, UserRole.CHETOP, UserRole.TECHNICIEN],
        "message": "Nouvelle alerte prédictive: {machine} - {alert_type}",
    },
    "ALERT_CRITICAL": {
        "roles": [UserRole.ADMIN, UserRole.CHEFTECH],
        "message": "ALERTE CRITIQUE: {machine} - {message}",
    },
    "REPORT_GENERATED": {
        "roles": [UserRole.ADMIN],
        "message": "Rapport généré: {report_type}",
    },
    "REPORT_SENT": {
        "roles": [UserRole.ADMIN],
        "message": "Rapport envoyé: {report_type} à {recipients} destinataires",
    },
    "USER_APPROVED": {
        "roles": [],  # Direct to user
        "message": "Votre compte a été approuvé. Vous pouvez maintenant vous connecter.",
    },
    "USER_REJECTED": {
        "roles": [],  # Direct to user
        "message": "Votre demande de compte a été rejetée.",
    },
    "MAINTENANCE_DUE": {
        "roles": [UserRole.CHEFTECH, UserRole.TECHNICIEN],
        "message": "Maintenance prévue: {machine} - {date}",
    },
}


# ------------------ Service Layer ------------------
class NotificationsService:
    """Service layer for Notifications operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Notifications]:
        """Create a new notification"""
        try:
            obj = Notifications(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created notification with id: {obj.id}")

            # Broadcast to real-time clients
            try:
                from core.notifications import broadcaster

                notification_data = {
                    "id": obj.id,
                    "utilisateur_id": obj.utilisateur_id,
                    "type": obj.type,
                    "message": obj.message,
                    "date_envoi": obj.date_envoi.isoformat()
                    if obj.date_envoi
                    else None,
                    "lu": obj.lu,
                    "created_at": obj.created_at.isoformat()
                    if obj.created_at
                    else None,
                }
                await broadcaster.broadcast(obj.utilisateur_id, notification_data)
            except Exception as e:
                logger.error(f"Error broadcasting notification: {e}")

            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating notification: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Notifications]:
        """Get notification by ID"""
        try:
            query = select(Notifications).where(Notifications.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching notification {obj_id}: {str(e)}")
            raise

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 20,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of notifications"""
        try:
            query = select(Notifications)
            count_query = select(func.count(Notifications.id))

            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Notifications, field):
                        query = query.where(getattr(Notifications, field) == value)
                        count_query = count_query.where(
                            getattr(Notifications, field) == value
                        )

            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith("-"):
                    field_name = sort[1:]
                    if hasattr(Notifications, field_name):
                        query = query.order_by(
                            getattr(Notifications, field_name).desc()
                        )
                else:
                    if hasattr(Notifications, sort):
                        query = query.order_by(getattr(Notifications, sort))
            else:
                query = query.order_by(Notifications.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching notification list: {str(e)}")
            raise

    async def update(
        self, obj_id: int, update_data: Dict[str, Any]
    ) -> Optional[Notifications]:
        """Update notification"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Notification {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated notification {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating notification {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete notification"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Notification {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted notification {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting notification {obj_id}: {str(e)}")
            raise

    async def get_by_field(
        self, field_name: str, field_value: Any
    ) -> Optional[Notifications]:
        """Get notification by any field"""
        try:
            if not hasattr(Notifications, field_name):
                raise ValueError(f"Field {field_name} does not exist on Notifications")
            result = await self.db.execute(
                select(Notifications).where(
                    getattr(Notifications, field_name) == field_value
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching notification by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Notifications]:
        """Get list of notifications filtered by field"""
        try:
            if not hasattr(Notifications, field_name):
                raise ValueError(f"Field {field_name} does not exist on Notifications")
            result = await self.db.execute(
                select(Notifications)
                .where(getattr(Notifications, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Notifications.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching notifications by {field_name}: {str(e)}")
            raise

    async def send_to_role(
        self, role: UserRole, notification_data: Dict[str, Any]
    ) -> List[Notifications]:
        """Send notification to all users with a specific role"""
        try:
            result = await self.db.execute(
                select(Utilisateurs).where(Utilisateurs.role == role)
            )
            users = result.scalars().all()

            notifications = []
            for user in users:
                notif_data = notification_data.copy()
                notif_data["utilisateur_id"] = user.id
                notif = await self.create(notif_data)
                if notif:
                    notifications.append(notif)

            logger.info(
                f"Sent notification to {len(notifications)} users with role {role}"
            )
            return notifications
        except Exception as e:
            logger.error(f"Error sending notification to role {role}: {str(e)}")
            raise

    async def send_workflow_notification(
        self, action: str, data: Dict[str, Any], specific_user_id: Optional[int] = None
    ) -> List[Notifications]:
        """Send notification based on workflow action"""
        try:
            if action not in WORKFLOW_NOTIFICATIONS:
                logger.warning(f"Unknown workflow action: {action}")
                return []

            config = WORKFLOW_NOTIFICATIONS[action]
            message_template = config["message"]

            message = message_template.format(**data)

            notification_data = {"type": action, "message": message, "lu": False}

            # If specific user is provided (like USER_APPROVED)
            if specific_user_id:
                notification_data["utilisateur_id"] = specific_user_id
                return [await self.create(notification_data)]

            # Otherwise, send to all users of the configured roles
            target_roles = config.get("roles", [])
            notifications = []

            for role in target_roles:
                role_notifs = await self.send_to_role(role, notification_data)
                notifications.extend(role_notifs)

            return notifications
        except Exception as e:
            logger.error(f"Error sending workflow notification for {action}: {str(e)}")
            raise

    async def send_alert_notification(
        self,
        machine_name: str,
        alert_type: str,
        severity: str,
        message: str,
        machine_zone: Optional[str] = None,
    ) -> List[Notifications]:
        """Send notification for predictive maintenance alerts"""
        data = {
            "machine": machine_name,
            "alert_type": alert_type,
            "message": message,
            "severity": severity,
        }

        if severity in ["CRITICAL", "HIGH"]:
            action = "ALERT_CRITICAL"
        else:
            action = "ALERT_CREATED"

        return await self.send_workflow_notification(action, data)

    async def get_user_notifications(
        self, user_id: int, unread_only: bool = False, limit: int = 50
    ) -> List[Notifications]:
        """Get notifications for a specific user"""
        try:
            query = select(Notifications).where(Notifications.utilisateur_id == user_id)

            if unread_only:
                query = query.where(not Notifications.lu)

            query = query.order_by(Notifications.id.desc()).limit(limit)

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching user notifications: {str(e)}")
            raise

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        try:
            result = await self.db.execute(
                select(func.count(Notifications.id)).where(
                    Notifications.utilisateur_id == user_id, not Notifications.lu
                )
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error fetching unread count: {str(e)}")
            raise

    async def mark_as_read(
        self, notification_id: int, user_id: int
    ) -> Optional[Notifications]:
        """Mark a notification as read (only if owned by user)"""
        try:
            result = await self.db.execute(
                select(Notifications).where(
                    Notifications.id == notification_id,
                    Notifications.utilisateur_id == user_id,
                )
            )
            notification = result.scalar_one_or_none()

            if notification:
                notification.lu = True
                await self.db.commit()
                await self.db.refresh(notification)

            return notification
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking notification as read: {str(e)}")
            raise

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        try:
            result = await self.db.execute(
                select(Notifications).where(
                    Notifications.utilisateur_id == user_id, not Notifications.lu
                )
            )
            notifications = result.scalars().all()

            count = 0
            for notif in notifications:
                notif.lu = True
                count += 1

            if count > 0:
                await self.db.commit()

            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking all as read: {str(e)}")
            raise
