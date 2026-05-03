from __future__ import annotations

from typing import Any, Dict

from core.celery_app import celery_app
from core.email import EmailService


@celery_app.task(name="tasks.send_task_assignment_email")
def send_task_assignment_email(
    technician: Dict[str, Any],
    task: Dict[str, Any],
    machine_name: str,
    planning_identifiant: str,
) -> Dict[str, Any]:
    to_email = (technician or {}).get("email")
    if not to_email:
        return {"status": "skipped", "reason": "no email"}

    user_name = (technician or {}).get("nom") or ""
    subject = f"Nouvelle tâche de planning assignée — {task.get('titre', '')}"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Bonjour {user_name},</h2>
                <p>Une nouvelle tâche de planning vous a été assignée :</p>
                <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; width: 140px;">Tâche</td>
                        <td style="padding: 8px;">{task.get('titre', '')}</td>
                    </tr>
                    <tr style="background:#f9fafb;">
                        <td style="padding: 8px; font-weight: bold;">Type</td>
                        <td style="padding: 8px;">{task.get('task_type', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Machine</td>
                        <td style="padding: 8px;">{machine_name}</td>
                    </tr>
                    <tr style="background:#f9fafb;">
                        <td style="padding: 8px; font-weight: bold;">Planning</td>
                        <td style="padding: 8px;">{planning_identifiant}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Début</td>
                        <td style="padding: 8px;">{task.get('date_debut', '')}</td>
                    </tr>
                    <tr style="background:#f9fafb;">
                        <td style="padding: 8px; font-weight: bold;">Fin</td>
                        <td style="padding: 8px;">{task.get('date_fin', '')}</td>
                    </tr>
                </table>
                <p>Connectez-vous à l'application pour consulter les détails et demander une intervention si nécessaire.</p>
            </div>
        </body>
    </html>
    """

    email_service = EmailService()
    success = email_service.send_email(to_email, subject, html_content)
    return {"status": "sent" if success else "failed", "to": to_email}
