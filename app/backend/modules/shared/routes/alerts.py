import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.alertes import Alert, AlertConfig, AlertType, AlertSeverity
from services.alertes import AlertService
from schemas.pagination import PaginatedResponse
import math

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


@router.get("", response_model=List[AlertResponse])
async def get_alerts(
    machine_id: Optional[int] = Query(None, description="Filter by machine ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get list of active alerts, optionally filtered by machine or severity"""
    service = AlertService(db)
    
    alert_severity = None
    if severity:
        try:
            alert_severity = AlertSeverity(severity.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    alerts = await service.get_active_alerts(machine_id=machine_id, severity=alert_severity)
    
    # Paginate
    total = len(alerts)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    start = (page - 1) * page_size
    end = start + page_size
    paginated_alerts = alerts[start:end]
    
    return paginated_alerts


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get alert statistics summary"""
    service = AlertService(db)
    stats = await service.get_alert_stats()
    return stats


@router.get("/config", response_model=AlertConfigResponse)
async def get_alert_config(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get alert configuration"""
    service = AlertService(db)
    config = await service.get_config()
    return config


@router.patch("/config", response_model=AlertConfigResponse)
async def update_alert_config(
    config_data: AlertConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Update alert configuration (admin only)"""
    # TODO: Add role check for admin
    service = AlertService(db)
    config = await service.update_config(config_data.model_dump(exclude_unset=True))
    return config


@router.post("/check")
async def trigger_alert_check(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Manually trigger alert checking and creation"""
    # TODO: Add role check for admin
    service = AlertService(db)
    result = await service.check_and_create_alerts()
    return {"status": "completed", "alerts_created": result}


@router.get("/machines/{machine_id}", response_model=List[AlertResponse])
async def get_machine_alerts(
    machine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get alerts for a specific machine"""
    service = AlertService(db)
    alerts = await service.get_active_alerts(machine_id=machine_id)
    return alerts


@router.patch("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    request: DismissAlertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Dismiss an alert"""
    service = AlertService(db)
    alert = await service.dismiss_alert(alert_id, request.user_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "dismissed", "alert_id": alert_id}