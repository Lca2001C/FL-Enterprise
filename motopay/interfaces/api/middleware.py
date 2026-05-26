"""Middleware for observability (logging, metrics, context)."""
from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from motopay.alerts import AlertSeverity, alert_manager
from motopay.observability.context import RequestContext, set_context
from motopay.observability.logger import get_logger
from motopay.observability.metrics import (
    api_errors,
    api_request_duration,
    api_requests_total,
)
from motopay.security.rate_limiter import RATE_LIMITS, RateLimiter

logger = get_logger(__name__)
rate_limiter = RateLimiter()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for logging, metrics, and context."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with observability."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Create request context
        ctx = RequestContext(
            ip=client_ip,
            endpoint=request.url.path,
            method=request.method,
        )
        
        # Add auth info if available
        try:
            if hasattr(request.state, "user"):
                ctx.user_id = request.state.user.id
                ctx.email = request.state.user.email
                ctx.tenant_id = request.state.user.operacao_id
        except Exception:
            pass
        
        set_context(ctx)
        
        # Check rate limit
        rate_limit_key = f"{client_ip}:{request.url.path}"
        rate_limit_config = RATE_LIMITS.get(
            "api_admin" if ctx.tenant_id == 0 else "api_default"
        )
        
        if rate_limit_config:
            result = rate_limiter.check(
                rate_limit_key,
                rate_limit_config["limit"],
                rate_limit_config["window"],
            )
            
            if not result.allowed:
                alert_manager.trigger(
                    AlertSeverity.WARNING,
                    "Rate limit exceeded",
                    f"IP {client_ip} exceeded rate limit on {request.url.path}",
                    tenant_id=ctx.tenant_id,
                    tags={"type": "rate_limit"},
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many requests",
                        "retry_after": int(result.retry_after),
                    },
                    headers={"Retry-After": str(int(result.retry_after))},
                )
        
        # Time the request
        start_time = time.time()
        response = None

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.time() - start_time) * 1000
            status_code = response.status_code if response else 500
            
            # Record metrics
            api_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code,
            ).inc()
            
            api_request_duration.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration_ms / 1000)
            
            # Record errors
            if status_code >= 400:
                error_type = "client_error" if status_code < 500 else "server_error"
                api_errors.labels(
                    endpoint=request.url.path,
                    error_type=error_type,
                    status=status_code,
                ).inc()
                
                if status_code >= 500:
                    alert_manager.trigger(
                        AlertSeverity.WARNING,
                        f"API Error {status_code}",
                        f"{request.method} {request.url.path}",
                        tenant_id=ctx.tenant_id,
                        tags={"status": str(status_code)},
                    )
            
            # Log
            log_level = "error" if status_code >= 500 else "info"
            log_data = {
                "status": status_code,
                "duration_ms": duration_ms,
                "method": request.method,
                "path": request.url.path,
            }
            
            getattr(logger, log_level)(
                f"{request.method} {request.url.path} {status_code} {duration_ms:.1f}ms",
                extra={"extra_data": log_data},
            )
