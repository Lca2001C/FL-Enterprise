from __future__ import annotations

import redis

from motopay.config import get_settings

_redis_client: redis.Redis | None = None


def get_redis_connection() -> redis.Redis:
    """Conexão única compatível com Redis local e Upstash (rediss://)."""
    global _redis_client
    if _redis_client is None:
        s = get_settings()
        _redis_client = redis.from_url(
            s.redis_url,
            decode_responses=True,
            socket_connect_timeout=float(s.redis_socket_connect_timeout_seconds),
            socket_timeout=float(s.redis_socket_timeout_seconds),
            health_check_interval=int(s.redis_health_check_interval_seconds),
        )
    return _redis_client
