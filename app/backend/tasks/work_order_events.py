from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.celery_app import celery_app
from core.email import EmailService

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.notify_work_order_created")
def notify_work_order_created(
    work_order: Dict[str, Any],
    creator: Dict[str, Any],
    cheftech_recipients: List[Dict[str, Any]],
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Nouvel ordre de travail: {work_order.get('titre', '')}"

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
                    <h2 style="color: #2563eb;">Nouvel Ordre de Travail</h2>
                    <p>Bonjour {user_name},</p>
                    <p>Un nouvel ordre de travail a été créé par <strong>{creator.get('nom', 'Chef Opérations')}</strong>.</p>
                    <ul>
                        <li><strong>Titre:</strong> {work_order.get('titre', '')}</li>
                        <li><strong>Priorité:</strong> {work_order.get('priorite', '')}</li>
                        <li><strong>Machine ID:</strong> {work_order.get('machine_id', '')}</li>
                        <li><strong>Date échéance:</strong> {work_order.get('date_echeance', 'Non définie')}</li>
                    </ul>
                    <p>Veuillez consulter le système pour plus de détails.</p>
                </div>
            </body>
        </html>
        """

        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Un nouvel ordre de travail a été créé par {creator.get('nom', 'Chef Opérations')}.\n"
            f"Titre: {work_order.get('titre', '')}\n"
            f"Priorité: {work_order.get('priorite', '')}\n"
            f"Machine ID: {work_order.get('machine_id', '')}\n"
            f"Date échéance: {work_order.get('date_echeance', 'Non définie')}\n"
        )

        if email_service.send_email(to_email, subject, html_content, text_content):
            ok += 1
        else:
            failed.append(to_email)

    logger.info(f"Work order created notifications: sent={ok}, failed={len(failed)}")
    return {"sent": ok, "failed": failed}


@celery_app.task(name="tasks.notify_work_order_assigned")
def notify_work_order_assigned(
    work_order: Dict[str, Any],
    assigner: Dict[str, Any],
    technician_recipients: List[Dict[str, Any]],
    creator_recipient: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Ordre de travail assigné: {work_order.get('titre', '')}"

    ok = 0
    failed: List[str] = []

    for recipient in technician_recipients:
        to_email = (recipient or {}).get("email")
        if not to_email:
            continue

        user_name = (recipient or {}).get("nom", "")
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #f59e0b;">Ordre de Travail Assigné</h2>
                    <p>Bonjour {user_name},</p>
                    <p>Un ordre de travail vous a été assigné par <strong>{assigner.get('nom', 'ChefTech')}</strong>.</p>
                    <ul>
                        <li><strong>Titre:</strong> {work_order.get('titre', '')}</li>
                        <li><strong>Priorité:</strong> {work_order.get('priorite', '')}</li>
                        <li><strong>Description:</strong> {work_order.get('description', '')}</li>
                    </ul>
                    <p>Veuillez commencer le travail dès que possible.</p>
                </div>
            </body>
        </html>
        """

        text_content = (
            f"Bonjour {user_name},\n\n"
            f"Un ordre de travail vous a été assigné par {assigner.get('nom', 'ChefTech')}.\n"
            f"Titre: {work_order.get('titre', '')}\n"
            f"Priorité: {work_order.get('priorite', '')}\n"
            f"Description: {work_order.get('description', '')}\n"
        )

        if email_service.send_email(to_email, subject, html_content, text_content):
            ok += 1
        else:
            failed.append(to_email)

    if creator_recipient:
        to_email = creator_recipient.get("email")
        if to_email:
            user_name = creator_recipient.get("nom", "")
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #10b981;">Ordre de Travail Assigné</h2>
                        <p>Bonjour {user_name},</p>
                        <p>Votre ordre de travail <strong>{work_order.get('titre', '')}</strong> a été assigné par le ChefTech.</p>
                        <p>Les techniciens assignés commenceront le travail prochainement.</p>
                    </div>
                </body>
            </html>
            """
            text_content = (
                f"Bonjour {user_name},\n\n"
                f"Votre ordre de travail '{work_order.get('titre', '')}' a été assigné par le ChefTech.\n"
            )
            if email_service.send_email(to_email, subject, html_content, text_content):
                ok += 1
            else:
                failed.append(to_email)

    logger.info(f"Work order assigned notifications: sent={ok}, failed={len(failed)}")
    return {"sent": ok, "failed": failed}


@celery_app.task(name="tasks.notify_work_order_status_changed")
def notify_work_order_status_changed(
    work_order: Dict[str, Any],
    old_status: str,
    new_status: str,
    changed_by: Dict[str, Any],
    recipients: List[Dict[str, Any]],
) -> Dict[str, Any]:
    email_service = EmailService()
    subject = f"Statut ordre de travail modifié: {work_order.get('titre', '')}"

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
                    <h2 style="color: #8b5cf6;">Changement de Statut</h2>
                    <p>Bonjour {user_name},</p>
                    <p>Le statut de l'ordre de travail <strong>{work_order.get('titre', '')}</strong> a été modifié.</p>
                    <ul>
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
            f"Statut de l'ordre de travail '{work_order.get('titre', '')}' modifié.\n"
            f"Ancien statut: {old_status}\n"
            f"Nouveau statut: {new_status}\n"
            f"Modifié par: {changed_by.get('nom', '')}\n"
        )

        if email_service.send_email(to_email, subject, html_content, text_content):
            ok += 1
        else:
            failed.append(to_email)

    logger.info(f"Work order status changed notifications: sent={ok}, failed={len(failed)}")
    return {"sent": ok, "failed": failed}
