from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from motopay.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "motopay",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    imports=["motopay.infrastructure.messaging.tasks"],
)

celery_app.conf.beat_schedule = {
    "daily-motopay-automation": {
        "task": "motopay.infrastructure.messaging.tasks.daily_automation_tick",
        "schedule": crontab(hour=11, minute=0),
    },
}
