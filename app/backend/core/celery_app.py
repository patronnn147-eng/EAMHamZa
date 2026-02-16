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
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
