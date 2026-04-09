from __future__ import annotations

from typing import Any, Dict, List

from core.celery_app import celery_app
from core.email import EmailService


@celery_app.task(name="tasks.send_planning_assignment_emails")
def send_planning_assignment_emails(recipients: List[Dict[str, Any]], planning: Dict[str, Any]) -> Dict[str, Any]:
    email_service = EmailService()

    subject = f"Planning assignment: {planning.get('identifiant_planning', '')}"

    ok = 0
    failed: List[str] = []

    for recipient in recipients:
        to_email = (recipient or {}).get("email")
        if not to_email:
            continue

        user_name = (recipient or {}).get("nom") or ""
        html_content = f"""
        <html>
            <body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #333;\">
                <div style=\"max-width: 600px; margin: 0 auto; padding: 20px;\">
                    <h2 style=\"color: #2563eb;\">Bonjour {user_name},</h2>
                    <p>Vous avez été assigné au planning <strong>{planning.get('identifiant_planning', '')}</strong>.</p>
                    <ul>
                        <li><strong>Date début:</strong> {planning.get('date_debut', '')}</li>
                        <li><strong>Date fin:</strong> {planning.get('date_fin', '')}</li>
                        <li><strong>Type:</strong> {planning.get('type', '')}</li>
                        <li><strong>Zone:</strong> {planning.get('zone_travail') or ''}</li>
                    </ul>
                    <p>Merci.</p>
                </div>
            </body>
        </html>
        """

        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Vous avez été assigné au planning {planning.get('identifiant_planning', '')}.\n"
            f"Date début: {planning.get('date_debut', '')}\n"
            f"Date fin: {planning.get('date_fin', '')}\n"
            f"Type: {planning.get('type', '')}\n"
            f"Zone: {planning.get('zone_travail') or ''}\n"
        )

        if email_service.send_email(to_email, subject, html_content, text_content):
            ok += 1
        else:
            failed.append(to_email)

    return {"sent": ok, "failed": failed}
