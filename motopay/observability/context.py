"""Request context for correlation and tenant isolation."""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field

__context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


@dataclass
class RequestContext:
    """Request context containing correlation ID, tenant info, user info."""
    
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int | None = None
    user_id: int | None = None
    email: str | None = None
    ip: str | None = None
    endpoint: str | None = None
    method: str | None = None
    
    def __repr__(self) -> str:
        return (
            f"RequestContext(correlation_id={self.correlation_id!r}, "
            f"tenant_id={self.tenant_id}, user_id={self.user_id}, "
            f"endpoint={self.endpoint})"
        )


def set_context(ctx: RequestContext) -> None:
    """Set the current request context."""
    __context.set(ctx)


def get_context() -> RequestContext | None:
    """Get the current request context."""
    return __context.get()


def clear_context() -> None:
    """Clear the current request context."""
    __context.set(None)
