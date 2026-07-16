import logging
from typing import Optional, List, Dict, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, case

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.alertes import Alert, AlertSeverity
from services.alertes import AlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    id: int
    alert_id: str
    machine_id: int
    alert_type: str
    severity: str
    message: str
    rul_days: Optional[float] = None
    failure_probability: Optional[float] = None
    is_active: bool
    is_linked_to_wo: bool
    work_order_id: Optional[int] = None
    priority: Optional[str] = None
    created_at: datetime
    dismissed_at: Optional[datetime] = None
    dismissed_by: Optional[int] = None

    class Config:
        from_attributes = True


class AlertStatsResponse(BaseModel):
    total_active: int
    by_severity: Dict[str, int]
    machines_affected: int


class AlertConfigResponse(BaseModel):
    id: int
    rul_threshold_days: float
    failure_probability_threshold: float
    enable_rul_alerts: bool
    enable_failure_alerts: bool
    enable_anomaly_alerts: bool
    notification_in_app: bool
    notification_email: bool
    frequency: str


class AlertConfigUpdate(BaseModel):
    rul_threshold_days: Optional[float] = None
    failure_probability_threshold: Optional[float] = None
    enable_rul_alerts: Optional[bool] = None
    enable_failure_alerts: Optional[bool] = None
    enable_anomaly_alerts: Optional[bool] = None
    notification_in_app: Optional[bool] = None
    notification_email: Optional[bool] = None
    frequency: Optional[str] = None


class DismissAlertRequest(BaseModel):
    user_id: int


class CreateWorkOrderRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None
    created_by: int
    priority: Optional[str] = None


async def get_alerts_for_user_role(
    db: AsyncSession,
    machine_id: Optional[int] = None,
    severity: Optional[AlertSeverity] = None,
) -> List[Alert]:
    """Filter alerts based on user role.

    ADMIN / CHEFTECH / CHETOP — see all active alerts (no zone column exists on Machines).
    TECHNICIEN — same for now (no technicien_id FK on Machines).
    """
    query = select(Alert).where(Alert.is_active)

    if machine_id:
        query = query.where(Alert.machine_id == machine_id)

    if severity:
        query = query.where(Alert.severity == severity)

    # All authenticated roles see all alerts.
    # Role-based scoping can be added here once Machines gains zone_travail_id / technicien_id.

    query = query.order_by(
        case(
            (Alert.severity == AlertSeverity.CRITICAL, 1),
            (Alert.severity == AlertSeverity.HIGH, 2),
            (Alert.severity == AlertSeverity.MEDIUM, 3),
            (Alert.severity == AlertSeverity.LOW, 4),
            else_=5,
        ),
        Alert.created_at.desc(),
    )

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("", response_model=List[AlertResponse], responses={400: {"description": "Bad Request"}})
async def get_alerts(
    *, machine_id: Annotated[Optional[int], Query(description="Filter by machine ID")] = None,
    severity: Annotated[Optional[str], Query(description="Filter by severity")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get list of active alerts, filtered by user role"""
    alert_severity = None
    if severity:
        try:
            alert_severity = AlertSeverity(severity.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    alerts = await get_alerts_for_user_role(
        db, machine_id, alert_severity
    )

    len(alerts)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_alerts = alerts[start:end]

    return paginated_alerts


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get alert statistics summary"""
    service = AlertService(db)
    stats = await service.get_alert_stats()
    return stats


@router.get("/config", response_model=AlertConfigResponse)
async def get_alert_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get alert configuration"""
    service = AlertService(db)
    config = await service.get_config()
    return config


@router.patch("/config", response_model=AlertConfigResponse)
async def update_alert_config(
    config_data: AlertConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Update alert configuration (admin only)"""
    service = AlertService(db)
    config = await service.update_config(config_data.model_dump(exclude_unset=True))
    return config


@router.post("/check")
async def trigger_alert_check(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Manually trigger alert checking and creation"""
    service = AlertService(db)
    result = await service.check_and_create_alerts()
    return {"status": "completed", "alerts_created": result}


@router.get("/machines/{machine_id}", response_model=List[AlertResponse])
async def get_machine_alerts(
    machine_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get alerts for a specific machine"""
    service = AlertService(db)
    alerts = await service.get_active_alerts(machine_id=machine_id)
    return alerts


@router.patch("/{alert_id}/dismiss", responses={404: {"description": "Alert not found"}})
async def dismiss_alert(
    alert_id: int,
    request: DismissAlertRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Dismiss an alert"""
    service = AlertService(db)
    alert = await service.dismiss_alert(alert_id, request.user_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "dismissed", "alert_id": alert_id}


@router.post("/{alert_id}/create-work-order", responses={403: {"description": "Only admin or cheftech can create work orders from alerts"}, 404: {"description": "Alert not found"}})
async def create_work_order_from_alert(
    alert_id: int,
    request: CreateWorkOrderRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Create a work order from an alert"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:
        raise HTTPException(
            status_code=403,
            detail="Only admin or cheftech can create work orders from alerts",
        )

    service = AlertService(db)

    wo_data = {
        "title": request.title,
        "description": request.description,
        "assigned_to": request.assigned_to,
        "due_date": request.due_date,
        "created_by": request.created_by,
        "priority": request.priority,
    }

    wo = await service.create_work_order_from_alert(alert_id, wo_data)

    if not wo:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "status": "created",
        "alert_id": alert_id,
        "work_order_id": wo.id,
        "work_order_title": wo.titre,
    }


@router.get("/my", response_model=List[AlertResponse])
async def get_my_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get alerts relevant to the current user based on their role and assignments"""
    alerts = await get_alerts_for_user_role(db)
    return alerts[:50]
