"""Prometheus metrics setup."""
from __future__ import annotations

from prometheus_client import REGISTRY, Counter, Gauge, Histogram

# API Metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)

api_errors = Counter(
    "api_errors_total",
    "Total API errors",
    ["endpoint", "error_type", "status"],
    registry=REGISTRY,
)

# Database Metrics
db_pool_size = Gauge(
    "db_pool_size",
    "Database connection pool size",
    registry=REGISTRY,
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=REGISTRY,
)

db_slow_queries = Counter(
    "db_slow_queries_total",
    "Total slow database queries (>100ms)",
    ["query_type"],
    registry=REGISTRY,
)

# Celery Metrics
celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
    registry=REGISTRY,
)

celery_task_duration = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

celery_queue_length = Gauge(
    "celery_queue_length",
    "Number of tasks in Celery queue",
    ["queue_name"],
    registry=REGISTRY,
)

celery_workers_online = Gauge(
    "celery_workers_online",
    "Number of Celery workers online",
    registry=REGISTRY,
)

celery_tasks_in_progress = Gauge(
    "celery_tasks_in_progress",
    "Number of Celery tasks currently running",
    registry=REGISTRY,
)

celery_task_retries_total = Counter(
    "celery_task_retries_total",
    "Total Celery task retries",
    ["task_name"],
    registry=REGISTRY,
)

celery_dlq_size = Gauge(
    "celery_dlq_size",
    "Number of tasks in the dead letter queue",
    registry=REGISTRY,
)

telegram_circuit_breaker_state = Gauge(
    "telegram_circuit_breaker_state",
    "Telegram circuit breaker state (0=closed, 1=open, 2=half-open)",
    registry=REGISTRY,
)

clientes_inadimplentes = Gauge(
    "clientes_inadimplentes_total",
    "Total delinquent clients across platform",
    registry=REGISTRY,
)

cobrancas_pendentes = Gauge(
    "cobrancas_pendentes_total",
    "Total pending billing charges",
    registry=REGISTRY,
)

cobrancas_atrasadas = Gauge(
    "cobrancas_atrasadas_total",
    "Total overdue billing charges",
    registry=REGISTRY,
)

# Telegram Bot Metrics
telegram_bot_status = Gauge(
    "telegram_bot_status",
    "Telegram bot online status (1=online, 0=offline)",
    ["tenant_id"],
    registry=REGISTRY,
)

telegram_messages_sent = Counter(
    "telegram_messages_sent_total",
    "Total Telegram messages sent",
    ["tenant_id"],
    registry=REGISTRY,
)

telegram_messages_failed = Counter(
    "telegram_messages_failed_total",
    "Total Telegram message failures",
    ["tenant_id"],
    registry=REGISTRY,
)

telegram_rate_limit_hits = Counter(
    "telegram_rate_limit_hits_total",
    "Telegram rate limit hits",
    registry=REGISTRY,
)

# Business Metrics
tenants_active = Gauge(
    "tenants_active",
    "Number of active tenants",
    registry=REGISTRY,
)

api_errors_critical = Counter(
    "api_errors_critical_total",
    "Critical API errors",
    ["tenant_id", "error_type"],
    registry=REGISTRY,
)

payment_failures = Counter(
    "payment_failures_total",
    "Payment processing failures",
    ["gateway", "error_type"],
    registry=REGISTRY,
)


def setup_metrics() -> None:
    """Initialize metrics (already done via module import)."""
    pass
