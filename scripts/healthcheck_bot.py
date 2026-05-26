"""Healthcheck do bot Telegram via chave Redis bot:heartbeat."""
from __future__ import annotations

import os
import sys

import redis


def main() -> int:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)
    return 0 if client.exists("bot:heartbeat") else 1


if __name__ == "__main__":
    sys.exit(main())
