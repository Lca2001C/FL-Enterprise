"""Rate limiting with Redis."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from motopay.infrastructure.redis_client import get_redis_connection


@dataclass
class RateLimitResult:
    """Rate limit check result."""

    allowed: bool
    remaining: int
    reset_at: float
    retry_after: float


class RateLimiter:
    """Redis-backed rate limiter using token bucket algorithm.

    Usa get_redis_connection(): com REDIS_URL vazio cai no shim em memória,
    então nunca falha na construção (antes quebrava com URL vazia).
    """

    def __init__(self, redis_client: Any | None = None):
        self.redis = redis_client or get_redis_connection()
    
    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Check if key is within rate limit."""
        now = time.time()
        window_key = f"rate_limit:{key}:{int(now // window_seconds)}"
        
        try:
            count = self.redis.incr(window_key)
            if count == 1:
                self.redis.expire(window_key, window_seconds + 1)
            
            allowed = count <= limit
            remaining = max(0, limit - count)
            reset_at = now + window_seconds
            retry_after = (count - limit) * (window_seconds / limit) if count > limit else 0
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=retry_after,
            )
        except Exception:
            return RateLimitResult(allowed=True, remaining=limit, reset_at=now, retry_after=0)


# Common rate limits
RATE_LIMITS = {
    "login": {"limit": 5, "window": 300},  # 5 per 5min
    "api_default": {"limit": 1000, "window": 3600},  # 1000 per hour
    "api_admin": {"limit": 5000, "window": 3600},  # 5000 per hour
    "api_create": {"limit": 100, "window": 3600},  # 100 creates per hour
}
