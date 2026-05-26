"""Redis-backed circuit breaker for multi-worker processes."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypeVar

from motopay.alerts import AlertSeverity, alert_manager
from motopay.infrastructure.redis_client import get_redis_connection
from motopay.observability.logger import get_logger
from motopay.observability.metrics import telegram_circuit_breaker_state

logger = get_logger(__name__)

T = TypeVar("T")

_STATE_CLOSED = 0
_STATE_OPEN = 1
_STATE_HALF_OPEN = 2


class RedisCircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: int = 600,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures_key = f"cb:{name}:failures"
        self._state_key = f"cb:{name}:state"
        self._opened_at_key = f"cb:{name}:opened_at"

    def _redis(self):
        return get_redis_connection()

    def _get_state(self) -> str:
        state = self._redis().get(self._state_key) or "closed"
        if state == "open":
            opened = self._redis().get(self._opened_at_key)
            if opened and (time.time() - float(opened)) > self.recovery_timeout:
                self._redis().set(self._state_key, "half-open")
                telegram_circuit_breaker_state.set(_STATE_HALF_OPEN)
                return "half-open"
        mapping = {"closed": _STATE_CLOSED, "open": _STATE_OPEN, "half-open": _STATE_HALF_OPEN}
        telegram_circuit_breaker_state.set(mapping.get(state, _STATE_CLOSED))
        return state

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        state = self._get_state()
        if state == "open":
            raise RuntimeError(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            if state == "half-open":
                self._redis().delete(self._failures_key, self._opened_at_key)
                self._redis().set(self._state_key, "closed")
                telegram_circuit_breaker_state.set(_STATE_CLOSED)
                logger.info("Circuit breaker %s CLOSED", self.name)
            return result
        except Exception:
            r = self._redis()
            failures = r.incr(self._failures_key)
            r.expire(self._failures_key, self.recovery_timeout * 2)
            if failures >= self.failure_threshold:
                r.set(self._state_key, "open")
                r.set(self._opened_at_key, str(time.time()))
                telegram_circuit_breaker_state.set(_STATE_OPEN)
                logger.error("Circuit breaker %s OPEN after %s failures", self.name, failures)
                alert_manager.trigger_sync(
                    AlertSeverity.CRITICAL,
                    f"Circuit Breaker Open — {self.name}",
                    f"Service unavailable after {failures} consecutive failures",
                    tags={"type": "circuit_breaker", "service": self.name},
                )
            raise
