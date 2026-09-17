import logging
from typing import Optional, List, Dict, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from services.rapports import RapportsService

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class ScheduledReportCreate(BaseModel):
    report_type: str
    title: str
    frequency: str  # daily, weekly, monthly
    day_of_week: Optional[int] = None  # 0-6 for weekly
    time: str = "08:00"  # HH:MM format
    recipients: List[Dict[str, str]]  # [{"email": "...", "nom": "..."}]
    is_active: bool = True


class ScheduledReportUpdate(BaseModel):
    title: Optional[str] = None
    frequency: Optional[str] = None
    day_of_week: Optional[int] = None
    time: Optional[str] = None
    recipients: Optional[List[Dict[str, str]]] = None
    is_active: Optional[bool] = None


class ReportResponse(BaseModel):
    id: int
    identifiant_rapport: str
    titre: str
    date_generation: datetime
    report_type: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@admin_router.get("/scheduled")
async def get_scheduled_reports(
    *, page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get list of scheduled reports"""
    service = RapportsService(db)
    result = await service.get_scheduled_reports(active_only=False)

    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = result[start:end]

    return {
        "items": [r for r in paginated],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@admin_router.post("/scheduled")
async def create_scheduled_report(
    report: ScheduledReportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Create a new scheduled report"""
    service = RapportsService(db)

    schedule_config = {
        "frequency": report.frequency,
        "day_of_week": report.day_of_week,
        "time": report.time,
        "recipients": report.recipients,
    }

    created = await service.create_scheduled_report(
        report_type=report.report_type,
        title=report.title,
        schedule_config=schedule_config,
        recipients=report.recipients,
    )

    return {"id": created.id, "status": "created"}


@admin_router.patch("/scheduled/{report_id}", responses={404: {"description": "Report not found"}})
async def update_scheduled_report(
    report_id: int,
    update: ScheduledReportUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Update a scheduled report"""
    service = RapportsService(db)
    existing = await service.get_by_id(report_id)

    if not existing:
        raise HTTPException(status_code=404, detail="Report not found")

    update_data = {}
    if update.title:
        update_data["titre"] = update.title
    if update.is_active is not None:
        update_data["is_active"] = update.is_active

    if update.frequency or update.day_of_week or update.time or update.recipients:
        existing_config = existing.schedule_config or {}
        schedule_config = {
            "frequency": update.frequency or existing_config.get("frequency", "weekly"),
            "day_of_week": update.day_of_week
            if update.day_of_week is not None
            else existing_config.get("day_of_week"),
            "time": update.time or existing_config.get("time", "08:00"),
            "recipients": update.recipients or existing_config.get("recipients", []),
        }
        update_data["schedule_config"] = schedule_config

    await service.update(report_id, update_data)
    return {"status": "updated", "id": report_id}


@admin_router.delete("/scheduled/{report_id}", responses={404: {"description": "Report not found"}})
async def delete_scheduled_report(
    report_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Delete a scheduled report"""
    service = RapportsService(db)
    deleted = await service.delete(report_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"status": "deleted", "id": report_id}


@admin_router.get("/download/{report_type}")
async def download_report(
    *, report_type: str,
    format: Annotated[str, Query(regex="^(json|pdf|excel)$")] = "json",
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Generate and download a report on-demand"""
    service = RapportsService(db)

    if report_type == "asset_health":
        data = await service.generate_asset_health_report()
    elif report_type == "weekly_digest":
        data = await service.generate_weekly_digest()
    else:
        data = {"report_type": report_type, "generated_at": datetime.now().isoformat()}

    return {
        "report_type": report_type,
        "format": format,
        "data": data,
        "message": f"Report generated in {format} format",
    }


@admin_router.post("/test-email", responses={400: {"description": "User email not found"}})
async def send_test_email(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Send a test email with sample report"""
    from core.email import EmailService

    service = RapportsService(db)
    report_data = await service.generate_asset_health_report()

    email_service = EmailService()
    subject = "Test - Rapport EAM"

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Rapport de Test</h2>
            <p>Ceci est un email de test du système de rapports.</p>
            <pre>{json.dumps(report_data, indent=2)}</pre>
        </body>
    </html>
    """

    # Send to user's email
    user_email = getattr(current_user, "email", None)
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")

    sent = email_service.send_email(user_email, subject, html_content, None)

    return {"sent": sent, "email": user_email}


import json  # noqa: E402
