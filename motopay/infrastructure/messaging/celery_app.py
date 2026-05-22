from __future__ import annotations

import ssl

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
    timezone=_settings.app_timezone,
    enable_utc=False,
    imports=["motopay.infrastructure.messaging.tasks"],
)

if _settings.redis_url.startswith("rediss://"):
    ssl_backend = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    celery_app.conf.broker_use_ssl = ssl_backend
    celery_app.conf.redis_backend_use_ssl = ssl_backend

if _settings.sentry_dsn.strip():
    try:
        import sentry_sdk
        from celery.signals import task_failure
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_sdk.init(
            dsn=_settings.sentry_dsn,
            environment=_settings.environment,
            integrations=[CeleryIntegration()],
            traces_sample_rate=0.1,
        )

        @task_failure.connect
        def _celery_task_failure(sender=None, task_id=None, exception=None, **kwargs):  # noqa: ARG001
            sentry_sdk.capture_exception(exception)
    except ImportError:
        pass

celery_app.conf.beat_schedule = {
    "daily-motopay-automation": {
        "task": "motopay.infrastructure.messaging.tasks.daily_automation_tick",
        "schedule": crontab(hour=_settings.celery_beat_hour, minute=_settings.celery_beat_minute),
    },
}
