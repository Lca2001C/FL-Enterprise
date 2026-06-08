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
    enable_utc=True,
    imports=[
        "motopay.infrastructure.messaging.tasks",
        "motopay.infrastructure.messaging.celery_observability",
    ],
    task_routes={
        "motopay.infrastructure.messaging.tasks.daily_automation_tick": {"queue": "default"},
        "motopay.infrastructure.messaging.tasks.handle_domain_event": {"queue": "telegram"},
        "motopay.infrastructure.messaging.tasks.send_d3_reminder": {"queue": "telegram"},
        "motopay.infrastructure.messaging.tasks.send_d1_reminder": {"queue": "telegram"},
        "motopay.infrastructure.messaging.tasks.send_d0_reminder": {"queue": "telegram"},
        "motopay.infrastructure.messaging.tasks.reconcile_mercadopago_payments": {
            "queue": "default"
        },
        "motopay.infrastructure.messaging.celery_observability.monitor_queues": {"queue": "default"},
        "motopay.infrastructure.messaging.celery_observability.collect_business_metrics": {
            "queue": "default"
        },
    },
    task_default_queue="default",
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

celery_app.conf.beat_scheduler = "redbeat.schedulers:RedBeatScheduler"
celery_app.conf.redbeat_redis_url = _settings.redis_url
celery_app.conf.redbeat_key_prefix = "motopay:redbeat:"

celery_app.conf.beat_schedule = {
    "daily-motopay-automation": {
        "task": "motopay.infrastructure.messaging.tasks.daily_automation_tick",
        "schedule": crontab(hour=_settings.celery_beat_hour, minute=_settings.celery_beat_minute),
    },
    "monitor-celery-queues": {
        "task": "motopay.infrastructure.messaging.celery_observability.monitor_queues",
        "schedule": 300.0,
    },
    "collect-business-metrics": {
        "task": "motopay.infrastructure.messaging.celery_observability.collect_business_metrics",
        "schedule": 60.0,
    },
    "reconcile-mercadopago-payments": {
        "task": "motopay.infrastructure.messaging.tasks.reconcile_mercadopago_payments",
        "schedule": 900.0,
    },
}
