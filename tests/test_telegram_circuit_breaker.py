from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from motopay.infrastructure.resilience.redis_circuit_breaker import RedisCircuitBreaker


@pytest.fixture
def mock_redis():
    store: dict[str, str | int] = {}

    r = MagicMock()

    def get(key):
        return store.get(key)

    def set(key, value):
        store[key] = value

    def delete(*keys):
        for k in keys:
            store.pop(k, None)

    def incr(key):
        store[key] = int(store.get(key, 0)) + 1
        return store[key]

    def expire(key, _ttl):
        return True

    r.get = get
    r.set = set
    r.delete = delete
    r.incr = incr
    r.expire = expire
    return r, store


def test_circuit_breaker_opens_after_threshold(mock_redis):
    r, _store = mock_redis
    cb = RedisCircuitBreaker("test", failure_threshold=3, recovery_timeout=60)

    with patch(
        "motopay.infrastructure.resilience.redis_circuit_breaker.get_redis_connection",
        return_value=r,
    ):
        with patch(
            "motopay.infrastructure.resilience.redis_circuit_breaker.alert_manager.trigger_sync"
        ):
            for _ in range(3):
                with pytest.raises(ValueError):
                    cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

            with pytest.raises(RuntimeError, match="OPEN"):
                cb.call(lambda: "ok")


def test_circuit_breaker_success_resets(mock_redis):
    r, store = mock_redis
    store["cb:test:state"] = "half-open"
    cb = RedisCircuitBreaker("test", failure_threshold=3, recovery_timeout=60)

    with patch(
        "motopay.infrastructure.resilience.redis_circuit_breaker.get_redis_connection",
        return_value=r,
    ):
        assert cb.call(lambda: "ok") == "ok"
        assert store.get("cb:test:state", "closed") == "closed"
