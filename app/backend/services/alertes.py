import logging
import sys
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# Ensure /app is on sys.path so `from modules.ml...` works in all execution
# contexts (Celery ForkPoolWorkers, pytest, etc.) regardless of cwd.
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.alertes import Alert, AlertConfig, AlertType, AlertSeverity
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from core.notifications import broadcaster

logger = logging.getLogger(__name__)


class AlertService:
    """Service layer for Predictive Maintenance Alerts"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(
        self,
        machine_id: int,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        rul_days: Optional[float] = None,
        failure_probability: Optional[float] = None,
    ) -> Alert:
        """Create a new predictive maintenance alert"""
        try:
            # Check if there's already an active alert for this machine and type
            existing_query = select(Alert).where(
                and_(
                    Alert.machine_id == machine_id,
                    Alert.alert_type == alert_type,
                    Alert.is_active == True,
                )
            )
            result = await self.db.execute(existing_query)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Active alert already exists for machine {machine_id}, type {alert_type}")
                return existing

            obj = Alert(
                machine_id=machine_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                rul_days=rul_days,
                failure_probability=failure_probability,
            )
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created alert with id: {obj.id} for machine {machine_id}")

            # Get machine name for notification
            machine_result = await self.db.execute(
                select(Machines).where(Machines.id == machine_id)
            )
            machine = machine_result.scalar_one_or_none()
            machine_name = machine.nom if machine else f"Machine {machine_id}"

            # Send in-app notification
            await self._send_alert_notification(obj, machine_name)

            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating alert: {str(e)}")
            raise

    async def _send_alert_notification(self, alert: Alert, machine_name: str):
        """Send real-time notification for alert creation"""
        try:
            from services.notifications import NotificationsService

            notification_data = {
                "utilisateur_id": 0,  # Would be sent to relevant users
                "type": "ALERT_PREDICTIVE",
                "message": f"[{alert.severity.value}] {alert.alert_type.value}: {machine_name} - {alert.message}",
            }

            # Use the notifications service
            notif_service = NotificationsService(self.db)
            await notif_service.create(notification_data)

            # Also broadcast to WebSocket clients
            await broadcaster.broadcast(
                0,  # broadcast to all
                {
                    "type": "alert",
                    "alert_id": alert.id,
                    "machine_name": machine_name,
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "message": alert.message,
                },
            )
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")

    async def get_active_alerts(
        self,
        machine_id: Optional[int] = None,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """Get list of active alerts, optionally filtered"""
        try:
            query = select(Alert).where(Alert.is_active == True)

            if machine_id is not None:
                query = query.where(Alert.machine_id == machine_id)
            if severity is not None:
                query = query.where(Alert.severity == severity)

            query = query.order_by(
                # Order by severity importance, then by date
                case(
                    (Alert.severity == AlertSeverity.CRITICAL, 1),
                    (Alert.severity == AlertSeverity.HIGH, 2),
                    (Alert.severity == AlertSeverity.MEDIUM, 3),
                    (Alert.severity == AlertSeverity.LOW, 4),
                    else_=5,
                ),
                Alert.created_at.desc(),
            )

            result = await self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error fetching active alerts: {str(e)}")
            raise

    async def dismiss_alert(self, alert_id: int, user_id: int) -> Optional[Alert]:
        """Dismiss an alert"""
        try:
            result = await self.db.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = result.scalar_one_or_none()

            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return None

            alert.is_active = False
            alert.dismissed_at = datetime.now(timezone.utc)
            alert.dismissed_by = user_id

            await self.db.commit()
            await self.db.refresh(alert)
            logger.info(f"Dismissed alert {alert_id} by user {user_id}")
            return alert
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error dismissing alert {alert_id}: {str(e)}")
            raise

    async def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics summary"""
        try:
            # Total active alerts
            total_query = select(func.count(Alert.id)).where(Alert.is_active == True)
            total_result = await self.db.execute(total_query)
            total_active = total_result.scalar() or 0

            # By severity
            severity_counts = {}
            for severity in AlertSeverity:
                query = select(func.count(Alert.id)).where(
                    and_(Alert.is_active == True, Alert.severity == severity)
                )
                result = await self.db.execute(query)
                severity_counts[severity.value] = result.scalar() or 0

            # By machine count
            machine_query = select(
                func.count(func.distinct(Alert.machine_id))
            ).where(Alert.is_active == True)
            machine_result = await self.db.execute(machine_query)
            machines_affected = machine_result.scalar() or 0

            return {
                "total_active": total_active,
                "by_severity": severity_counts,
                "machines_affected": machines_affected,
            }
        except Exception as e:
            logger.error(f"Error fetching alert stats: {str(e)}")
            raise

    async def get_config(self) -> AlertConfig:
        """Get alert configuration"""
        try:
            query = select(AlertConfig).limit(1)
            result = await self.db.execute(query)
            config = result.scalar_one_or_none()

            if not config:
                # Create default config
                config = AlertConfig()
                self.db.add(config)
                await self.db.commit()
                await self.db.refresh(config)
                logger.info("Created default alert config")

            return config
        except Exception as e:
            logger.error(f"Error fetching alert config: {str(e)}")
            raise

    async def update_config(self, config_data: Dict[str, Any]) -> AlertConfig:
        """Update alert configuration"""
        try:
            config = await self.get_config()

            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            await self.db.commit()
            await self.db.refresh(config)
            logger.info("Updated alert config")
            return config
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating alert config: {str(e)}")
            raise

    async def check_and_create_alerts(self) -> Dict[str, Any]:
        """Run ML predictions and create alerts for machines crossing thresholds"""
        try:
            config = await self.get_config()

            # Get all machines
            machines_result = await self.db.execute(select(Machines))
            machines = list(machines_result.scalars().all())

            alerts_created = {
                "rul_warnings": 0,
                "failure_predicted": 0,
                "anomaly_detected": 0,
            }

            # Check ML microservice availability ONCE before iterating machines.
            # Calling is_ml_service_available() per machine = N health-check HTTP requests.
            from modules.ml.rul_calculator import RULCalculator
            from core.ml_client import ml_client, is_ml_service_available
            _ml_available = await is_ml_service_available()

            for machine in machines:
                try:
                    # Get intervention history
                    interventions_query = select(Ordres_intervention).where(
                        Ordres_intervention.machine_id == machine.id
                    )
                    itv_result = await self.db.execute(interventions_query)
                    interventions = list(itv_result.scalars().all())

                    # Get latest telemetry reading for this machine
                    telemetry_query = (
                        select(MachineTelemetry)
                        .where(MachineTelemetry.machine_id == machine.id)
                        .order_by(MachineTelemetry.recorded_at.desc())
                        .limit(10)
                    )
                    tel_result = await self.db.execute(telemetry_query)
                    telemetry_entries = list(reversed(tel_result.scalars().all()))

                    # Use latest telemetry values if available, else nominal defaults
                    if telemetry_entries:
                        latest = telemetry_entries[-1]
                        air  = float(latest.air_temperature)
                        proc = float(latest.process_temperature)
                        rpm  = int(latest.rotational_speed)
                        torq = float(latest.torque)
                        wear = int(latest.tool_wear)
                    else:
                        air, proc, rpm, torq, wear = 300.0, 310.0, 1500, 40.0, 0

                    # Best-effort microservice call; fall back to formula if unavailable
                    fusion_result = None
                    try:
                        if _ml_available:
                            fusion_result = await ml_client.predict_all(
                                air_temperature=air,
                                process_temperature=proc,
                                rotational_speed=rpm,
                                torque=torq,
                                tool_wear=wear,
                                machine_id=machine.id,
                            )
                    except Exception:
                        pass

                    prediction = RULCalculator.calculate_rul(
                        machine,
                        list(interventions),
                        telemetry_entries=telemetry_entries,
                        fusion_result=fusion_result,
                    )

                    rul_days = prediction.get("rul_days")
                    failure_prob = prediction.get("failure_probability", 0) / 100  # Convert from percentage

                    # Check RUL threshold
                    if config.enable_rul_alerts and rul_days is not None and rul_days < config.rul_threshold_days:
                        severity = self._get_rul_severity(rul_days)
                        message = f"RUL prediction: {rul_days:.1f} days remaining (threshold: {config.rul_threshold_days} days)"

                        await self.create_alert(
                            machine_id=machine.id,
                            alert_type=AlertType.RUL_WARNING,
                            severity=severity,
                            message=message,
                            rul_days=rul_days,
                        )
                        alerts_created["rul_warnings"] += 1

                    # Check failure probability threshold
                    if config.enable_failure_alerts and failure_prob > config.failure_probability_threshold:
                        await self.create_alert(
                            machine_id=machine.id,
                            alert_type=AlertType.FAILURE_PREDICTED,
                            severity=AlertSeverity.HIGH,
                            message=f"Failure probability: {failure_prob*100:.1f}% (threshold: {config.failure_probability_threshold*100:.1f}%)",
                            failure_probability=failure_prob,
                        )
                        alerts_created["failure_predicted"] += 1

                except Exception as e:
                    logger.error(f"Error processing machine {machine.id}: {e}")
                    continue

            logger.info(f"Alert check complete: {alerts_created}")
            return alerts_created
        except Exception as e:
            logger.error(f"Error in check_and_create_alerts: {str(e)}")
            raise

    def _get_rul_severity(self, rul_days: float) -> AlertSeverity:
        """Determine severity based on RUL days"""
        if rul_days <= 1:
            return AlertSeverity.CRITICAL
        elif rul_days <= 3:
            return AlertSeverity.HIGH
        elif rul_days <= 7:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    async def create_work_order_from_alert(
        self,
        alert_id: int,
        wo_data: Dict[str, Any],
    ) -> Optional[Ordres_travail]:
        """Create a work order linked to an alert"""
        try:
            alert_result = await self.db.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return None
            
            if alert.is_linked_to_wo and alert.work_order_id:
                logger.info(f"Alert {alert_id} already linked to work order {alert.work_order_id}")
                existing_wo = await self.db.execute(
                    select(Ordres_travail).where(Ordres_travail.id == alert.work_order_id)
                )
                return existing_wo.scalar_one_or_none()
            
            priority_map = {
                "LOW": "BASSE",
                "MEDIUM": "MOYENNE", 
                "HIGH": "ÉLEVÉE",
                "CRITICAL": "URGENTE"
            }
            
            wo = Ordres_travail(
                titre=wo_data.get("title", f"Maintenance - {alert.machine.name if alert.machine else 'Machine #'+str(alert.machine_id)}"),
                description=wo_data.get("description", alert.message),
                priorite=priority_map.get(alert.severity.value, "MOYENNE"),
                machine_id=alert.machine_id,
                utilisateur_id=wo_data.get("assigned_to"),
                date_echeance=wo_data.get("due_date"),
                created_by=wo_data.get("created_by"),
                statut="EN_ATTENTE"
            )
            
            self.db.add(wo)
            await self.db.commit()
            await self.db.refresh(wo)
            
            alert.is_linked_to_wo = True
            alert.work_order_id = wo.id
            alert.priority = wo_data.get("priority", alert.severity.value)
            await self.db.commit()
            
            logger.info(f"Created work order {wo.id} from alert {alert_id}")
            
            from services.notifications import NotificationsService
            notif_service = NotificationsService(self.db)
            await notif_service.send_workflow_notification(
                "WORK_ORDER_CREATED",
                {"title": wo.titre}
            )
            
            return wo
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating work order from alert {alert_id}: {str(e)}")
            raise

    async def link_existing_work_order(self, alert_id: int, work_order_id: int) -> Optional[Alert]:
        """Link an existing work order to an alert"""
        try:
            alert_result = await self.db.execute(
                select(Alert).where(Alert.id == alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            
            if not alert:
                return None
            
            wo_result = await self.db.execute(
                select(Ordres_travail).where(Ordres_travail.id == work_order_id)
            )
            wo = wo_result.scalar_one_or_none()
            
            if not wo:
                return None
            
            alert.is_linked_to_wo = True
            alert.work_order_id = work_order_id
            
            await self.db.commit()
            await self.db.refresh(alert)
            
            logger.info(f"Linked alert {alert_id} to work order {work_order_id}")
            return alert
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error linking work order: {str(e)}")
            raise

    async def send_alert_email(self, alert: Alert, config: AlertConfig) -> bool:
        """Send email notification for critical alerts"""
        if not config.notification_email:
            return False
        
        if alert.severity not in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            if config.frequency in ["daily", "weekly"]:
                return False
        
        try:
            from core.email import EmailService
            
            machine_name = alert.machine.name if alert.machine else f"Machine {alert.machine_id}"
            
            subject = f"[{alert.severity.value}] Predictive Alert - {machine_name}"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2 style="color: #d32f2f;">Predictive Maintenance Alert</h2>
                    <table style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Machine</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{machine_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Alert Type</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{alert.alert_type.value}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Severity</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd; color: {'red' if alert.severity == AlertSeverity.CRITICAL else 'orange'};">{alert.severity.value}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Message</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{alert.message}</td>
                        </tr>
                        {f'<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>RUL Days</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.rul_days}</td></tr>' if alert.rul_days else ''}
                        {f'<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Failure Probability</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.failure_probability*100:.1f}%</td></tr>' if alert.failure_probability else ''}
                    </table>
                    <p style="margin-top: 20px;">
                        <a href="/alerts" style="background-color: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View All Alerts</a>
                    </p>
                </body>
            </html>
            """
            
            email_service = EmailService()
            from models.utilisateurs import Utilisateurs, UserRole
            
            result = await self.db.execute(
                select(Utilisateurs.email).where(
                    Utilisateurs.role.in_([UserRole.ADMIN, UserRole.CHEFTECH]),
                    Utilisateurs.status == "ACTIVE"
                )
            )
            emails = [row[0] for row in result.all() if row[0]]
            
            for email in emails:
                email_service.send_email(email, subject, html_content, None)
            
            logger.info(f"Sent alert email for alert {alert.id} to {len(emails)} recipients")
            return True
        except Exception as e:
            logger.error(f"Error sending alert email: {str(e)}")
            return False