from __future__ import annotations

import logging
from typing import Any, Dict, List
from datetime import datetime

from core.celery_app import celery_app
from core.email import EmailService
from core.database import AsyncSessionLocal
from services.rapports import RapportsService

logger = logging.getLogger(__name__)

_DEFAULT_ADMIN = [{"email": "admin@example.com", "nom": "Admin"}]


def _collect_recipients(scheduled, frequency: str) -> List:
    """Extract recipient list from scheduled reports matching a frequency."""
    recipients = []
    for report in scheduled:
        if report.schedule_config and report.schedule_config.get("frequency") == frequency:
            recipients.extend(report.schedule_config.get("recipients", []))
    return recipients or list(_DEFAULT_ADMIN)


def _send_batch(email_service: EmailService, recipients: List, subject: str, html: str) -> int:
    """Send email to every recipient; return count of successful sends."""
    sent = 0
    for recipient in recipients:
        to_email = recipient.get("email") if isinstance(recipient, dict) else recipient
        if to_email and email_service.send_email(to_email, subject, html, None):
            sent += 1
    return sent


@celery_app.task(name="tasks.send_weekly_report")
def send_weekly_report() -> Dict[str, Any]:
    """Generate and send weekly digest report to all recipients"""
    logger.info("Starting weekly report generation")

    async def _send():
        async with AsyncSessionLocal() as db:
            service = RapportsService(db)
            scheduled = await service.get_scheduled_reports(active_only=True)
            recipients = _collect_recipients(scheduled, "weekly")
            report_data = await service.generate_weekly_digest()

            email_service = EmailService()
            subject = f"Rapport Hebdomadaire - {datetime.now().strftime('%d/%m/%Y')}"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2563eb;">Rapport Hebdomadaire</h2>
                        <p>Période: {report_data.get("period", "N/A")}</p>
                        <hr/>
                        <h3>Résumé</h3>
                        <ul>
                            <li><strong>Total Machines:</strong> {report_data["summary"]["total_machines"]}</li>
                            <li><strong>Alertes Générées:</strong> {report_data["summary"]["alerts_generated"]}</li>
                        </ul>
                        <p>Voir le dashboard pour plus de détails.</p>
                    </div>
                </body>
            </html>
            """
            sent = _send_batch(email_service, recipients, subject, html_content)
            return {"sent": sent, "report_type": "WEEKLY_DIGEST"}

    return asyncio.run(_send())


@celery_app.task(name="tasks.send_daily_digest")
def send_daily_digest() -> Dict[str, Any]:
    """Generate and send daily digest report"""
    logger.info("Starting daily digest report generation")

    async def _send():
        async with AsyncSessionLocal() as db:
            service = RapportsService(db)
            scheduled = await service.get_scheduled_reports(active_only=True)
            recipients = _collect_recipients(scheduled, "daily")
            report_data = await service.generate_asset_health_report()

            email_service = EmailService()
            subject = f"Résumé Quotidien - {datetime.now().strftime('%d/%m/%Y')}"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2563eb;">Résumé Quotidien</h2>
                        <p>Généré: {report_data.get("generated_at", "N/A")}</p>
                        <hr/>
                        <h3>État des Actifs</h3>
                        <ul>
                            <li><strong>Total Machines:</strong> {report_data["summary"]["total_machines"]}</li>
                            <li><strong>Alertes Actives:</strong> {report_data["summary"]["active_alerts"]}</li>
                            <li><strong>Alertes Critiques:</strong> {report_data["summary"]["critical_alerts"]}</li>
                        </ul>
                    </div>
                </body>
            </html>
            """
            sent = _send_batch(email_service, recipients, subject, html_content)
            return {"sent": sent, "report_type": "DAILY_DIGEST"}

    return asyncio.run(_send())


@celery_app.task(name="tasks.check_and_send_due_reports")
def check_and_send_due_reports() -> Dict[str, Any]:
    """Check all active scheduled reports and send if due"""
    logger.info("Checking for due scheduled reports")

    # This can be expanded to check specific schedules
    # For now, just trigger weekly and daily
    weekly_result = send_weekly_report()
    daily_result = send_daily_digest()

    return {
        "weekly": weekly_result,
        "daily": daily_result,
    }


import asyncio  # noqa: E402
