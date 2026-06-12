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
        "tasks.reservation_expiry",
        "tasks.archive_sweep",
        "tasks.rag_db_sync",
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
            "schedule": 86400.0,  # 24 h
        },
        "check-predictive-alerts": {
            "task": "tasks.check_predictive_alerts",
            "schedule": 300.0,  # 5 min
        },
        "release-expired-reservations": {
            "task": "tasks.release_expired_reservations",
            "schedule": 3600.0,  # 1 h
        },
        "archive-past-due-items": {
            "task": "tasks.archive_past_due",
            "schedule": 3600.0,  # 1 h
        },
        "purge-archive-weekly": {
            "task": "tasks.purge_archive_old",
            "schedule": 604800.0,  # 7 d
        },
        # NOTE: RAG sync is event-driven via SQLAlchemy after_commit hooks
        # (see services/rag_change_hooks.py). No periodic beat task needed.
    },
)
