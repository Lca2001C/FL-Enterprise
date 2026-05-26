"""Realtime event publishing via Redis Pub/Sub."""
from __future__ import annotations

import json
from typing import Any

from motopay.infrastructure.redis_client import get_redis_connection
from motopay.observability.logger import get_logger

logger = get_logger(__name__)

PLATFORM_CHANNEL = "events:platform"


def publish_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    tenant_id: int | None = None,
) -> None:
    message = json.dumps({"type": event_type, "payload": payload})
    r = get_redis_connection()
    r.publish(PLATFORM_CHANNEL, message)
    if tenant_id is not None:
        r.publish(f"events:operacao:{tenant_id}", message)
    logger.debug("Published event %s tenant=%s", event_type, tenant_id)
