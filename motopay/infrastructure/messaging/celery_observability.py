"""Celery observability - signals, metrics, Dead Letter Queue."""
from __future__ import annotations

import json
import time
from functools import wraps
from typing import Any

from celery import Task, signals
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

from motopay.alerts import AlertSeverity, alert_manager
from motopay.config import get_settings
from motopay.infrastructure.messaging.celery_app import celery_app
from motopay.infrastructure.redis_client import get_redis_connection
from motopay.infrastructure.resilience.redis_circuit_breaker import RedisCircuitBreaker
from motopay.observability.logger import get_logger
from motopay.observability.metrics import (
    celery_dlq_size,
    celery_queue_length,
    celery_task_duration,
    celery_task_retries_total,
    celery_tasks_in_progress,
    celery_tasks_total,
    celery_workers_online,
    clientes_inadimplentes,
    cobrancas_atrasadas,
    cobrancas_pendentes,
    telegram_bot_status,
    tenants_active,
)

logger = get_logger(__name__)

_task_times: dict[str, float] = {}
_DLQ_LIST_KEY = "dlq:tasks"
_DLQ_META_PREFIX = "dlq:meta:"
_DLQ_MAX_SIZE = 1000
_MONITOR_QUEUES = ("default", "telegram", "billing", "celery")


class DLQTask(Task):
    autoretry_for = ()
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 5
    soft_time_limit = 3600
    time_limit = 3700

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task failed: %s",
            self.name,
            extra={
                "extra_data": {
                    "task_id": task_id,
                    "task_name": self.name,
                    "retry_count": self.request.retries,
                    "max_retries": self.max_retries,
                    "exception": str(exc),
                }
            },
        )
        if isinstance(exc, (MaxRetriesExceededError, SoftTimeLimitExceeded)):
            _move_to_dlq(
                task_name=self.name,
                task_id=task_id,
                args=args,
                kwargs=kwargs,
                error=str(exc),
                retry_count=self.request.retries,
            )
            alert_manager.trigger_sync(
                AlertSeverity.CRITICAL,
                f"Task Failed - {self.name}",
                f"Task {task_id} moved to DLQ after {self.request.retries} retries",
                tags={"task_name": self.name, "type": "task_failure"},
            )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Task retrying: %s attempt %s",
            self.name,
            self.request.retries + 1,
            extra={
                "extra_data": {
                    "task_id": task_id,
                    "task_name": self.name,
                    "retry_count": self.request.retries + 1,
                    "exception": str(exc),
                }
            },
        )


def _redis():
    return get_redis_connection()


def _move_to_dlq(
    task_name: str,
    task_id: str,
    args: tuple,
    kwargs: dict,
    error: str,
    retry_count: int,
) -> None:
    r = _redis()
    meta = {
        "task_id": task_id,
        "task_name": task_name,
        "args": list(args),
        "kwargs": kwargs,
        "error": error,
        "retry_count": retry_count,
        "timestamp": time.time(),
        "status": "pending_review",
    }
    r.hset(_DLQ_META_PREFIX + task_id, mapping={k: json.dumps(v) if isinstance(v, (list, dict)) else str(v) for k, v in meta.items()})
    r.lpush(_DLQ_LIST_KEY, task_id)
    while r.llen(_DLQ_LIST_KEY) > _DLQ_MAX_SIZE:
        old_id = r.rpop(_DLQ_LIST_KEY)
        if old_id:
            r.delete(_DLQ_META_PREFIX + old_id)
    celery_dlq_size.set(r.llen(_DLQ_LIST_KEY))
    logger.critical("Task moved to DLQ: %s (%s)", task_name, task_id)


def _load_dlq_item(task_id: str) -> dict[str, Any] | None:
    raw = _redis().hgetall(_DLQ_META_PREFIX + task_id)
    if not raw:
        return None
    item: dict[str, Any] = {}
    for key, value in raw.items():
        if key in ("args", "kwargs"):
            item[key] = json.loads(value)
        elif key in ("retry_count",):
            item[key] = int(value)
        elif key in ("timestamp",):
            item[key] = float(value)
        else:
            item[key] = value
    return item


def get_dlq() -> list[dict[str, Any]]:
    r = _redis()
    ids = r.lrange(_DLQ_LIST_KEY, 0, -1)
    items = []
    for task_id in ids:
        item = _load_dlq_item(task_id)
        if item:
            items.append(item)
    celery_dlq_size.set(len(items))
    return items


def dlq_retry(task_id: str) -> bool:
    item = _load_dlq_item(task_id)
    if not item:
        return False
    task = celery_app.tasks.get(item["task_name"])
    if not task:
        return False
    task.apply_async(args=tuple(item.get("args", [])), kwargs=item.get("kwargs", {}))
    _redis().hset(_DLQ_META_PREFIX + task_id, "status", "retried")
    logger.info("Retried task from DLQ: %s", task_id)
    return True


def dlq_discard(task_id: str) -> bool:
    r = _redis()
    removed = r.lrem(_DLQ_LIST_KEY, 0, task_id)
    r.delete(_DLQ_META_PREFIX + task_id)
    celery_dlq_size.set(r.llen(_DLQ_LIST_KEY))
    return removed > 0


def update_queue_lengths() -> dict[str, int]:
    r = _redis()
    lengths: dict[str, int] = {}
    for queue in _MONITOR_QUEUES:
        length = int(r.llen(queue))
        lengths[queue] = length
        celery_queue_length.labels(queue_name=queue).set(length)
    return lengths


@signals.task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    _task_times[task_id] = time.time()
    celery_tasks_in_progress.inc()
    logger.info(
        "Task started: %s",
        task.name,
        extra={"extra_data": {"task_id": task_id, "task_name": task.name}},
    )


@signals.task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, state=None, **kwargs):
    celery_tasks_in_progress.dec()
    if task_id not in _task_times:
        return
    duration = time.time() - _task_times.pop(task_id)
    celery_task_duration.labels(task_name=task.name).observe(duration)
    status = "success" if state == "SUCCESS" else "failure"
    celery_tasks_total.labels(task_name=task.name, status=status).inc()
    if duration > 10:
        logger.warning(
            "Slow task: %s took %.2fs",
            task.name,
            duration,
            extra={
                "extra_data": {
                    "task_id": task_id,
                    "task_name": task.name,
                    "duration_ms": duration * 1000,
                }
            },
        )


@signals.task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    if task_id in _task_times:
        duration = time.time() - _task_times.pop(task_id)
    else:
        duration = 0
    celery_task_duration.labels(task_name=sender.name).observe(duration)
    celery_tasks_total.labels(task_name=sender.name, status="failure").inc()
    logger.error(
        "Task failed: %s: %s",
        sender.name,
        exception,
        extra={
            "extra_data": {
                "task_id": task_id,
                "task_name": sender.name,
                "exception": str(exception),
                "duration_ms": duration * 1000,
            }
        },
    )


@signals.task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, **kwargs):
    celery_tasks_total.labels(task_name=sender.name, status="retry").inc()
    celery_task_retries_total.labels(task_name=sender.name).inc()
    logger.warning(
        "Task retrying: %s: %s",
        sender.name,
        reason,
        extra={
            "extra_data": {
                "task_id": task_id,
                "task_name": sender.name,
                "reason": str(reason),
            }
        },
    )


@signals.worker_ready.connect
def worker_ready_handler(**kwargs):
    from motopay.infrastructure.messaging.worker_metrics import start_worker_metrics_server

    start_worker_metrics_server()


telegram_circuit_breaker = RedisCircuitBreaker("telegram", failure_threshold=5, recovery_timeout=600)


def telegram_safe_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return telegram_circuit_breaker.call(func, *args, **kwargs)

    return wrapper


def get_worker_stats() -> dict[str, Any]:
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        registered = inspect.registered()
        if not stats:
            celery_workers_online.set(0)
            celery_tasks_in_progress.set(0)
            return {
                "workers_online": 0,
                "active_tasks": 0,
                "registered_tasks": 0,
                "workers": [],
            }
        total_active = sum(len(tasks) for tasks in (active or {}).values())
        total_registered = sum(len(tasks) for tasks in (registered or {}).values())
        celery_workers_online.set(len(stats))
        celery_tasks_in_progress.set(total_active)
        workers_info = []
        for worker_name, worker_stats in stats.items():
            workers_info.append(
                {
                    "name": worker_name,
                    "pool": worker_stats.get("pool", {}).get("implementation"),
                    "concurrency": worker_stats.get("pool", {}).get("max-concurrency"),
                    "active_tasks": len(active.get(worker_name, [])) if active else 0,
                }
            )
        return {
            "workers_online": len(stats),
            "active_tasks": total_active,
            "registered_tasks": total_registered,
            "workers": workers_info,
        }
    except Exception as e:
        logger.error("Failed to get worker stats: %s", e)
        return {
            "workers_online": 0,
            "active_tasks": 0,
            "registered_tasks": 0,
            "workers": [],
        }


def get_queue_stats() -> dict[str, Any]:
    backlog = update_queue_lengths()
    active_stats: dict[str, int] = {}
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active:
            for _worker, tasks in active.items():
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "unknown")
                    active_stats[queue] = active_stats.get(queue, 0) + 1
    except Exception as e:
        logger.error("Failed to get active queue stats: %s", e)
    return {"backlog": backlog, "active": active_stats}


def detect_stuck_tasks() -> list[dict[str, Any]]:
    settings = get_settings()
    stuck: list[dict[str, Any]] = []
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active() or {}
        now = time.time()
        for worker, tasks in active.items():
            for task in tasks:
                started = task.get("time_start")
                if started and (now - started) > settings.celery_stuck_task_seconds:
                    stuck.append(
                        {
                            "worker": worker,
                            "task_id": task.get("id"),
                            "task_name": task.get("name"),
                            "seconds_running": int(now - started),
                        }
                    )
    except Exception as e:
        logger.error("Failed to detect stuck tasks: %s", e)
    return stuck


def health_check_celery() -> dict[str, Any]:
    worker_stats = get_worker_stats()
    queue_stats = get_queue_stats()
    dlq_size = _redis().llen(_DLQ_LIST_KEY)
    celery_dlq_size.set(dlq_size)
    healthy = worker_stats["workers_online"] > 0
    return {
        "status": "healthy" if healthy else "unhealthy",
        "workers_online": worker_stats["workers_online"],
        "active_tasks": worker_stats["active_tasks"],
        "queue_stats": queue_stats,
        "dlq_size": dlq_size,
        "workers": worker_stats.get("workers", []),
    }


def get_celery_summary() -> dict[str, Any]:
    worker_stats = get_worker_stats()
    queue_stats = get_queue_stats()
    stuck = detect_stuck_tasks()
    dlq_size = _redis().llen(_DLQ_LIST_KEY)
    celery_dlq_size.set(dlq_size)
    bot_online = 1 if _redis().exists("bot:heartbeat") else 0
    telegram_bot_status.labels(tenant_id="global").set(bot_online)
    return {
        "workers_online": worker_stats["workers_online"],
        "active_tasks": worker_stats["active_tasks"],
        "queue_backlog": queue_stats.get("backlog", {}),
        "queue_active": queue_stats.get("active", {}),
        "dlq_size": dlq_size,
        "stuck_tasks": stuck,
        "bot_online": bool(bot_online),
        "workers": worker_stats.get("workers", []),
    }


@celery_app.task(bind=True, name="motopay.infrastructure.messaging.celery_observability.monitor_queues")
def monitor_queues(self) -> None:
    settings = get_settings()
    try:
        stats = get_worker_stats()
        queue_stats = get_queue_stats()
        stuck = detect_stuck_tasks()
        summary = get_celery_summary()

        if stats["workers_online"] == 0:
            alert_manager.trigger_sync(
                AlertSeverity.CRITICAL,
                "No Celery Workers Online",
                "All Celery workers are offline!",
                tags={"type": "celery_worker_down"},
            )

        for queue, count in queue_stats.get("backlog", {}).items():
            if count > settings.celery_queue_backlog_threshold:
                alert_manager.trigger_sync(
                    AlertSeverity.WARNING,
                    f"Queue Backlog - {queue}",
                    f"Queue '{queue}' has {count} pending tasks",
                    tags={"queue": queue, "type": "queue_backlog"},
                )

        for item in stuck:
            alert_manager.trigger_sync(
                AlertSeverity.WARNING,
                "Stuck Celery Task",
                f"{item['task_name']} running for {item['seconds_running']}s on {item['worker']}",
                tags={"type": "stuck_task", "task_name": item["task_name"]},
            )

        try:
            from motopay.realtime.publish import publish_event

            publish_event("celery.queue_stats", summary)
        except Exception:
            pass

        logger.info(
            "Queue monitoring: %s workers, %s active tasks",
            stats["workers_online"],
            stats["active_tasks"],
            extra={"extra_data": queue_stats},
        )
    except Exception as e:
        logger.error("Queue monitoring failed: %s", e)


@celery_app.task(name="motopay.infrastructure.messaging.celery_observability.collect_business_metrics")
def collect_business_metrics() -> None:
    from sqlalchemy import func, select

    from motopay.domain.enums import CobrancaStatus, ContratoStatus
    from motopay.infrastructure.db.models import Cobranca, Contrato, Operacao
    from motopay.infrastructure.db.session import SessionLocal

    db = SessionLocal()
    try:
        tenants = db.scalar(select(func.count()).select_from(Operacao)) or 0
        tenants_active.set(tenants)

        inadimplentes = db.scalar(
            select(func.count())
            .select_from(Contrato)
            .where(
                Contrato.status == ContratoStatus.ATIVO.value,
                Contrato.inadimplente.is_(True),
            )
        ) or 0
        clientes_inadimplentes.set(inadimplentes)

        pendentes = db.scalar(
            select(func.count())
            .select_from(Cobranca)
            .where(Cobranca.status == CobrancaStatus.PENDENTE.value)
        ) or 0
        cobrancas_pendentes.set(pendentes)

        atrasadas = db.scalar(
            select(func.count())
            .select_from(Cobranca)
            .where(Cobranca.status == CobrancaStatus.ATRASADO.value)
        ) or 0
        cobrancas_atrasadas.set(atrasadas)

        bot_online = 1 if _redis().exists("bot:heartbeat") else 0
        telegram_bot_status.labels(tenant_id="global").set(bot_online)
    finally:
        db.close()
