"""Health checks for all dependencies."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

import redis
from pydantic import BaseModel
from sqlalchemy import text

from motopay.config.settings import get_settings
from motopay.infrastructure.db.session import SessionLocal
from motopay.infrastructure.redis_client import InMemoryRedis, get_redis_connection, redis_enabled


class HealthStatus(str, Enum):
    """Health check status."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResult(BaseModel):
    """Single health check result."""
    
    name: str
    status: HealthStatus
    duration_ms: float
    error: str | None = None
    details: dict | None = None


class SystemHealthStatus(BaseModel):
    """Overall system health."""
    
    timestamp: datetime
    status: HealthStatus
    version: str = "1.0.0"
    uptime_seconds: float = 0
    checks: list[HealthCheckResult]
    overall_message: str


async def check_database() -> HealthCheckResult:
    """Check database connectivity and response time."""
    import time
    
    start = time.time()
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                duration_ms=duration_ms,
            )
        finally:
            db.close()
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            duration_ms=duration_ms,
            error=str(e),
        )


async def check_redis() -> HealthCheckResult:
    """Check Redis connectivity."""
    import time

    settings = get_settings()
    if not settings.redis_url.strip():
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.DEGRADED,
            duration_ms=0,
            error="Redis não configurado (modo degradado)",
        )

    start = time.time()
    try:
        r = get_redis_connection()
        if isinstance(r, InMemoryRedis):
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name="redis",
                status=HealthStatus.DEGRADED,
                duration_ms=duration_ms,
                error="REDIS_URL definido mas indisponível (usando memória local)",
            )
        r.ping()
        duration_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.HEALTHY,
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            duration_ms=duration_ms,
            error=str(e),
        )


async def check_celery() -> HealthCheckResult:
    """Check Celery worker availability."""
    import time

    from motopay.infrastructure.messaging.celery_app import celery_app
    
    start = time.time()
    try:
        stats = celery_app.control.inspect().stats()
        if not stats:
            raise Exception("No Celery workers available")
        
        duration_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="celery",
            status=HealthStatus.HEALTHY,
            duration_ms=duration_ms,
            details={"workers": len(stats)},
        )
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="celery",
            status=HealthStatus.DEGRADED,
            duration_ms=duration_ms,
            error=str(e),
        )


async def get_system_health() -> SystemHealthStatus:
    """Get overall system health status."""
    checks = [
        await check_database(),
        await check_redis(),
        await check_celery(),
    ]
    
    statuses = [c.status for c in checks]
    if HealthStatus.UNHEALTHY in statuses:
        overall = HealthStatus.UNHEALTHY
        message = "System is down — critical component failed"
    elif HealthStatus.DEGRADED in statuses:
        overall = HealthStatus.DEGRADED
        message = "System is degraded — some components unavailable"
    else:
        overall = HealthStatus.HEALTHY
        message = "System is healthy"
    
    return SystemHealthStatus(
        timestamp=datetime.utcnow(),
        status=overall,
        checks=checks,
        overall_message=message,
    )
