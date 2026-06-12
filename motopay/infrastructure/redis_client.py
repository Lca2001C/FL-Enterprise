from __future__ import annotations

import fnmatch
import threading
import time
from typing import Any

import redis

from motopay.config import get_settings

_redis_client: redis.Redis | InMemoryRedis | None = None


class _InMemoryPubSub:
    """Pub/Sub no-op para modo degradado."""

    def psubscribe(self, *_: Any, **__: Any) -> None:
        return None

    def subscribe(self, *_: Any, **__: Any) -> None:
        return None

    def get_message(self, **_kwargs: Any) -> None:
        return None


class InMemoryRedis:
    """Substituto em memória do Redis para rodar SEM Redis (REDIS_URL vazio).

    Cobre o subconjunto usado no caminho da API (rate-limit, refresh tokens,
    OAuth state). É single-process: o estado vive só neste processo e some no
    restart — adequado para subir a app antes de provisionar o Redis. Pub/Sub e
    fila assíncrona viram no-op. Ao definir REDIS_URL, o Redis real assume.
    """

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}
        self._lock = threading.Lock()

    def _alive(self, key: str) -> bool:
        item = self._data.get(key)
        if item is None:
            return False
        _, expires_at = item
        if expires_at is not None and expires_at <= time.time():
            self._data.pop(key, None)
            return False
        return True

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._data[key][0] if self._alive(key) else None

    def set(
        self,
        key: str,
        value: Any,
        *,
        nx: bool = False,
        ex: int | None = None,
        **_: Any,
    ) -> bool | None:
        with self._lock:
            if nx and self._alive(key):
                return None
            expires_at = time.time() + ex if ex else None
            self._data[key] = (str(value), expires_at)
            return True

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        with self._lock:
            self._data[key] = (str(value), time.time() + int(ttl))
            return True

    def incr(self, key: str, amount: int = 1) -> int:
        with self._lock:
            current = int(self._data[key][0]) if self._alive(key) else 0
            current += amount
            expires_at = self._data[key][1] if self._alive(key) else None
            self._data[key] = (str(current), expires_at)
            return current

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            if not self._alive(key):
                return False
            value, _ = self._data[key]
            self._data[key] = (value, time.time() + int(seconds))
            return True

    def delete(self, *keys: str) -> int:
        with self._lock:
            removed = 0
            for key in keys:
                if self._data.pop(key, None) is not None:
                    removed += 1
            return removed

    def scan_iter(self, match: str = "*", **_: Any):
        with self._lock:
            keys = [k for k in self._data if self._alive(k)]
        for key in keys:
            if fnmatch.fnmatch(key, match):
                yield key

    def publish(self, *_: Any, **__: Any) -> int:
        return 0  # sem subscriber em modo degradado

    def pubsub(self, **_: Any) -> "_InMemoryPubSub":
        return _InMemoryPubSub()

    def ping(self) -> bool:
        return True

    def __getattr__(self, name: str):
        # Qualquer método não implementado vira no-op seguro em modo degradado.
        def _noop(*_: Any, **__: Any) -> None:
            return None

        return _noop


def redis_enabled() -> bool:
    return bool(get_settings().redis_url.strip())


def get_redis_connection() -> redis.Redis | InMemoryRedis:
    """Conexão única. Redis real quando REDIS_URL definido; senão, shim em memória."""
    global _redis_client
    if _redis_client is None:
        s = get_settings()
        if not s.redis_url.strip():
            _redis_client = InMemoryRedis()
        else:
            _redis_client = redis.from_url(
                s.redis_url,
                decode_responses=True,
                socket_connect_timeout=float(s.redis_socket_connect_timeout_seconds),
                socket_timeout=float(s.redis_socket_timeout_seconds),
                health_check_interval=int(s.redis_health_check_interval_seconds),
            )
    return _redis_client


def reset_redis_connection() -> None:
    """Limpa o cache de conexão (usado em testes ao trocar REDIS_URL)."""
    global _redis_client
    _redis_client = None
