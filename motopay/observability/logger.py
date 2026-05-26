"""Structured logging with correlation IDs."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime

from motopay.observability.context import get_context


class JsonFormatter(logging.Formatter):
    """Structured JSON logging formatter."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_context()
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": ctx.correlation_id if ctx else None,
            "tenant_id": ctx.tenant_id if ctx else None,
            "user_id": ctx.user_id if ctx else None,
            "ip": ctx.ip if ctx else None,
            "endpoint": ctx.endpoint if ctx else None,
        }

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
            log_data["exc_type"] = record.exc_info[0].__name__

        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Setup JSON logging."""
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> logging.Logger:
    """Get logger with support for extra_data."""
    return logging.getLogger(name)
