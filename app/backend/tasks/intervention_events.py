from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.celery_app import celery_app
from core.email import EmailService

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.notify_intervention_requested")
def notify_intervention_requested(
    intervention: Dict[str, Any],
    technician: Dict[str, Any],
    cheftech_recipients: List[Dict[str, Any]],
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Demande d'intervention - OT #{intervention.get('ordre_travail_id', '')}"

    ok = 0
    failed: List[str] = []

    for recipient in cheftech_recipients:
        to_email = (recipient or {}).get("email")
        if not to_email:
            continue

        user_name = (recipient or {}).get("nom", "")
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #f59e0b;">Demande d'Intervention</h2>
                    <p>Bonjour {user_name},</p>
                    <p>Le technicien <strong>{technician.get('nom', '')}</strong> a soumis une demande d'intervention.</p>
                    <ul>
                        <li><strong>Ordre de travail:</strong> #{intervention.get('ordre_travail_id', '')}</li>
                        <li><strong>Problème:</strong> {intervention.get('problem_description', 'Non spécifié')}</li>
                        <li><strong>Priorité:</strong> {intervention.get('priority', 'Non spécifiée')}</li>
                        <li><strong>Durée estimée:</strong> {intervention.get('estimated_duration_minutes', 'N/A')} min</li>
                        <li><strong>Matériaux requis:</strong> {intervention.get('required_materials', 'Non spécifiés')}</li>
                    </ul>
                    <p>Veuillez approuver ou rejeter cette demande.</p>
                </div>
            </body>
        </html>
        """

        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Le technicien {technician.get('nom', '')} a soumis une demande d'intervention.\n"
            f"Ordre de travail: #{intervention.get('ordre_travail_id', '')}\n"
            f"Problème: {intervention.get('problem_description', 'Non spécifié')}\n"
            f"Priorité: {intervention.get('priority', 'Non spécifiée')}\n"
        )

        if email_service.send_email(to_email, subject, html_content, text_content):
            ok += 1
        else:
            failed.append(to_email)

    logger.info(f"Intervention requested notifications: sent={ok}, failed={len(failed)}")
    return {"sent": ok, "failed": failed}


@celery_app.task(name="tasks.notify_intervention_approved")
def notify_intervention_approved(
    intervention: Dict[str, Any],
    approved_by: Dict[str, Any],
    technician_recipient: Dict[str, Any],
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Intervention approuvée - OT #{intervention.get('ordre_travail_id', '')}"

    to_email = technician_recipient.get("email")
    if not to_email:
        return {"sent": 0, "failed": []}

    user_name = technician_recipient.get("nom", "")
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #10b981;">Intervention Approuvée</h2>
                <p>Bonjour {user_name},</p>
                <p>Votre demande d'intervention a été <strong style="color: #10b981;">approuvée</strong> par <strong>{approved_by.get('nom', 'ChefTech')}</strong>.</p>
                <ul>
                    <li><strong>Ordre de travail:</strong> #{intervention.get('ordre_travail_id', '')}</li>
                    <li><strong>Intervention ID:</strong> #{intervention.get('id', '')}</li>
                </ul>
                <p>Vous pouvez maintenant démarrer l'intervention.</p>
            </div>
        </body>
    </html>
    """

    text_content = (
        f"Bonjour {user_name},\n\n"
        f"Votre demande d'intervention a été approuvée par {approved_by.get('nom', 'ChefTech')}.\n"
        f"Ordre de travail: #{intervention.get('ordre_travail_id', '')}\n"
        f"Vous pouvez maintenant démarrer l'intervention.\n"
    )

    if email_service.send_email(to_email, subject, html_content, text_content):
        logger.info("Intervention approved notification sent")
        return {"sent": 1, "failed": []}

    logger.warning(f"Failed to send intervention approved notification to {to_email}")
    return {"sent": 0, "failed": [to_email]}


@celery_app.task(name="tasks.notify_intervention_rejected")
def notify_intervention_rejected(
    intervention: Dict[str, Any],
    rejected_by: Dict[str, Any],
    technician_recipient: Dict[str, Any],
    reason: str = "",
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Intervention rejetée - OT #{intervention.get('ordre_travail_id', '')}"

    to_email = technician_recipient.get("email")
    if not to_email:
        return {"sent": 0, "failed": []}

    user_name = technician_recipient.get("nom", "")
    reason_html = f"<li><strong>Raison:</strong> {reason}</li>" if reason else ""
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #ef4444;">Intervention Rejetée</h2>
                <p>Bonjour {user_name},</p>
                <p>Votre demande d'intervention a été <strong style="color: #ef4444;">rejetée</strong> par <strong>{rejected_by.get('nom', 'ChefTech')}</strong>.</p>
                <ul>
                    <li><strong>Ordre de travail:</strong> #{intervention.get('ordre_travail_id', '')}</li>
                    <li><strong>Intervention ID:</strong> #{intervention.get('id', '')}</li>
                    {reason_html}
                </ul>
                <p>Vous pouvez soumettre une nouvelle demande si nécessaire.</p>
            </div>
        </body>
    </html>
    """

    text_content = (
        f"Bonjour {user_name},\n\n"
        f"Votre demande d'intervention a été rejetée par {rejected_by.get('nom', 'ChefTech')}.\n"
        f"Ordre de travail: #{intervention.get('ordre_travail_id', '')}\n"
        f"Raison: {reason}\n" if reason else ""
    )

    if email_service.send_email(to_email, subject, html_content, text_content):
        logger.info("Intervention rejected notification sent")
        return {"sent": 1, "failed": []}

    logger.warning(f"Failed to send intervention rejected notification to {to_email}")
    return {"sent": 0, "failed": [to_email]}


@celery_app.task(name="tasks.notify_intervention_status_changed")
def notify_intervention_status_changed(
    intervention: Dict[str, Any],
    old_status: str,
    new_status: str,
    changed_by: Dict[str, Any],
    recipients: List[Dict[str, Any]],
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Statut intervention modifié - OT #{intervention.get('ordre_travail_id', '')}"

    ok = 0
    failed: List[str] = []

    for recipient in recipients:
        to_email = (recipient or {}).get("email")
        if not to_email:
            continue

        user_name = (recipient or {}).get("nom", "")
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #8b5cf6;">Changement de Statut - Intervention</h2>
                    <p>Bonjour {user_name},</p>
                    <p>Le statut de l'intervention #{intervention.get('id', '')} a été modifié.</p>
                    <ul>
                        <li><strong>Ordre de travail:</strong> #{intervention.get('ordre_travail_id', '')}</li>
                        <li><strong>Ancien statut:</strong> {old_status}</li>
                        <li><strong>Nouveau statut:</strong> {new_status}</li>
                        <li><strong>Modifié par:</strong> {changed_by.get('nom', '')}</li>
                    </ul>
                </div>
            </body>
        </html>
        """

        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Statut de l'intervention #{intervention.get('id', '')} modifié.\n"
            f"Ancien statut: {old_status}\n"
            f"Nouveau statut: {new_status}\n"
            f"Modifié par: {changed_by.get('nom', '')}\n"
        )

        if email_service.send_email(to_email, subject, html_content, text_content):
            ok += 1
        else:
            failed.append(to_email)

    logger.info(f"Intervention status changed notifications: sent={ok}, failed={len(failed)}")
    return {"sent": ok, "failed": failed}
