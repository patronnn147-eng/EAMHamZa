"""
Notifications Router - API endpoints for user notifications
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.notifications import Notifications
from services.notifications import NotificationsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


# ---------- Pydantic Schemas ----------
class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: int
    utilisateur_id: int
    type: str
    message: str
    date_envoi: datetime
    lu: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List response schema"""
    items: List[NotificationResponse]
    total: int
    unread_count: int


class MarkAsReadRequest(BaseModel):
    """Schema for marking notifications as read"""
    notification_ids: List[int]


class BulkNotificationCreateRequest(BaseModel):
    """Schema for creating notifications for multiple users"""
    utilisateur_ids: List[int]
    titre: str
    priorite: str = "MOYENNE"
    type: str
    message: str


# ---------- Routes ----------
@router.get("", response_model=NotificationListResponse)
async def get_my_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's notifications"""
    try:
        service = NotificationsService(db)
        
        # Build query filter
        query_dict = {"utilisateur_id": current_user.id}
        if unread_only:
            query_dict["lu"] = False
        
        # Get notifications
        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort="-date_envoi"
        )
        
        # Count unread notifications
        unread_result = await service.get_list(
            skip=0,
            limit=1,
            query_dict={"utilisateur_id": current_user.id, "lu": False}
        )
        
        return NotificationListResponse(
            items=[NotificationResponse.model_validate(item) for item in result["items"]],
            total=result["total"],
            unread_count=unread_result["total"]
        )
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}"
        )


@router.get("/unread-count")
async def get_unread_count(
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications"""
    try:
        service = NotificationsService(db)
        result = await service.get_list(
            skip=0,
            limit=1,
            query_dict={"utilisateur_id": current_user.id, "lu": False}
        )
        return {"unread_count": result["total"]}
    except Exception as e:
        logger.error(f"Error fetching unread count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unread count: {str(e)}"
        )


@router.post("/mark-as-read")
async def mark_notifications_as_read(
    data: MarkAsReadRequest,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notifications as read"""
    try:
        service = NotificationsService(db)
        updated_count = 0
        
        for notification_id in data.notification_ids:
            # Verify notification belongs to current user
            notification = await service.get_by_id(notification_id)
            if notification and notification.utilisateur_id == current_user.id:
                await service.update(notification_id, {"lu": True})
                updated_count += 1
        
        return {
            "message": f"Marked {updated_count} notifications as read",
            "updated_count": updated_count
        }
    except Exception as e:
        logger.error(f"Error marking notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notifications as read: {str(e)}"
        )


@router.post("/mark-all-as-read")
async def mark_all_as_read(
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all user's notifications as read"""
    try:
        service = NotificationsService(db)
        
        # Get all unread notifications
        result = await service.get_list(
            skip=0,
            limit=1000,
            query_dict={"utilisateur_id": current_user.id, "lu": False}
        )
        
        updated_count = 0
        for notification in result["items"]:
            await service.update(notification.id, {"lu": True})
            updated_count += 1
        
        return {
            "message": f"Marked all {updated_count} notifications as read",
            "updated_count": updated_count
        }
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.post("/bulk")
async def create_bulk_notifications(
    data: BulkNotificationCreateRequest,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create notifications for multiple users (ChefOp/ChefTech/Admin)."""
    if current_user.role not in {"CHETOP", "CHEFTECH", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if not data.utilisateur_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="utilisateur_ids is required")

    service = NotificationsService(db)
    now = datetime.now()
    created = 0

    for user_id in sorted(set(data.utilisateur_ids)):
        await service.create(
            {
                "utilisateur_id": user_id,
                "titre": data.titre,
                "priorite": data.priorite,
                "type": data.type,
                "message": data.message,
                "date_envoi": now,
                "lu": False,
                "created_at": now,
            }
        )
        created += 1

    return {"created": created}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification (only if it belongs to current user)"""
    try:
        service = NotificationsService(db)
        
        # Verify notification belongs to current user
        notification = await service.get_by_id(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        if notification.utilisateur_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own notifications"
            )
        
        success = await service.delete(notification_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return {"message": "Notification deleted successfully", "id": notification_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )