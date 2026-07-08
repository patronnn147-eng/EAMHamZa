import logging
import asyncio
from typing import List, Optional, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from core.database import get_db
from core.auth import get_current_user, ALGORITHM, SECRET_KEY
from core.notifications import broadcaster
import jwt
from jwt import PyJWTError as JWTError
from models.utilisateurs import Utilisateurs
from services.notifications import NotificationsService
from schemas.pagination import PaginatedResponse
import math

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


async def get_user_from_token(token: str, db: AsyncSession) -> Utilisateurs:
    """Helper to get user from token, used for SSE query params"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        from models.utilisateurs import Utilisateurs
        from sqlalchemy import select

        try:
            user_id_int = int(user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        result = await db.execute(
            select(Utilisateurs).where(Utilisateurs.id == user_id_int)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


@router.get("/stream", responses={401: {"description": "Invalid, missing, or unresolvable token"}})
async def notification_stream(
    request: Request, token: str, db: Annotated[AsyncSession, Depends(get_db)]
):
    """SSE endpoint for real-time notifications"""
    user = await get_user_from_token(token, db)
    user_id = user.id

    async def event_generator():
        queue = await broadcaster.subscribe(user_id)
        try:
            while True:
                # Check if client is still connected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for a new notification with a timeout for heartbeat
                    notification = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield {"event": "message", "data": notification}
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield {"event": "heartbeat", "data": "ping"}
        finally:
            broadcaster.unsubscribe(user_id, queue)

    return EventSourceResponse(event_generator())


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


class NotificationListResponse(PaginatedResponse[NotificationResponse]):
    """List response schema with unread count"""

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
@router.get("", response_model=NotificationListResponse, responses={500: {"description": "Internal Server Error"}})
async def get_my_notifications(
    *, page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    unread_only: bool = False,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current user's notifications"""
    skip = (page - 1) * size
    limit = size
    try:
        service = NotificationsService(db)

        # Build query filter
        query_dict = {"utilisateur_id": current_user.id}
        if unread_only:
            query_dict["lu"] = False

        # Get notifications
        result = await service.get_list(
            skip=skip, limit=limit, query_dict=query_dict, sort="-date_envoi"
        )

        # Count unread notifications
        unread_result = await service.get_list(
            skip=0, limit=1, query_dict={"utilisateur_id": current_user.id, "lu": False}
        )

        return NotificationListResponse(
            items=[
                NotificationResponse.model_validate(item) for item in result["items"]
            ],
            total=result["total"],
            page=page,
            size=size,
            total_pages=math.ceil(result["total"] / size) if size > 0 else 0,
            unread_count=unread_result["total"],
        )
    except Exception as e:
        logger.exception(f"Error fetching notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}",
        )


@router.get("/unread-count", responses={500: {"description": "Internal Server Error"}})
async def get_unread_count(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get count of unread notifications"""
    try:
        service = NotificationsService(db)
        result = await service.get_list(
            skip=0, limit=1, query_dict={"utilisateur_id": current_user.id, "lu": False}
        )
        return {"unread_count": result["total"]}
    except Exception as e:
        logger.exception(f"Error fetching unread count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unread count: {str(e)}",
        )


@router.post("/mark-as-read", responses={500: {"description": "Internal Server Error"}})
async def mark_notifications_as_read(
    data: MarkAsReadRequest,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
            "updated_count": updated_count,
        }
    except Exception as e:
        logger.exception(f"Error marking notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notifications as read: {str(e)}",
        )


@router.post("/mark-all-as-read", responses={500: {"description": "Internal Server Error"}})
async def mark_all_as_read(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mark all user's notifications as read"""
    try:
        service = NotificationsService(db)

        # Get all unread notifications
        result = await service.get_list(
            skip=0,
            limit=1000,
            query_dict={"utilisateur_id": current_user.id, "lu": False},
        )

        updated_count = 0
        for notification in result["items"]:
            await service.update(notification.id, {"lu": True})
            updated_count += 1

        return {
            "message": f"Marked all {updated_count} notifications as read",
            "updated_count": updated_count,
        }
    except Exception as e:
        logger.exception(f"Error marking all notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}",
        )


@router.post("/bulk", responses={400: {"description": "utilisateur_ids is required"}, 403: {"description": "Not authorized"}})
async def create_bulk_notifications(
    data: BulkNotificationCreateRequest,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create notifications for multiple users (ChefOp/ChefTech/Admin)."""
    if current_user.role not in {"CHETOP", "CHEFTECH", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    if not data.utilisateur_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="utilisateur_ids is required",
        )

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


@router.delete("/{notification_id}", responses={403: {"description": "You can only delete your own notifications"}, 404: {"description": "Notification not found"}, 500: {"description": "Internal Server Error"}})
async def delete_notification(
    notification_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a notification (only if it belongs to current user)"""
    try:
        service = NotificationsService(db)

        # Verify notification belongs to current user
        notification = await service.get_by_id(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )

        if notification.utilisateur_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own notifications",
            )

        success = await service.delete(notification_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )

        return {"message": "Notification deleted successfully", "id": notification_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting notification {notification_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}",
        )
