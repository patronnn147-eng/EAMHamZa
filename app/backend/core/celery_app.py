import os

from celery import Celery


def _get_broker_url() -> str:
    return os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")


celery_app = Celery(
    "asset_management",
    broker=_get_broker_url(),
    include=[
        "tasks.planning_emails",
        "tasks.work_order_events",
        "tasks.intervention_events",
        "tasks.maintenance_scheduler",
        "tasks.alert_checker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-maintenance-daily": {
            "task": "tasks.check_preventive_maintenance",
            "schedule": 86400.0,  # Once every 24 hours
        },
        "check-predictive-alerts": {
            "task": "tasks.check_predictive_alerts",
            "schedule": 300.0,  # Every 15 minutes
        },
    },
)
