"""Alert management system."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from motopay.observability.logger import get_logger

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Alert:
    """System alert."""
    
    id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: AlertSeverity = AlertSeverity.INFO
    title: str = ""
    message: str = ""
    tenant_id: int | None = None
    tags: dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False
    
    def __hash__(self) -> int:
        return hash(self.id)


class AlertManager:
    """Central alert management."""
    
    def __init__(self):
        self.alerts: dict[str, Alert] = {}
        self.handlers: list[Callable[[Alert], Any]] = []
        self.max_alerts = 1000
    
    def register_handler(self, handler: Callable[[Alert], Any]) -> None:
        """Register a handler to be called when alerts are triggered."""
        self.handlers.append(handler)
    
    def trigger(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        tenant_id: int | None = None,
        tags: dict[str, str] | None = None,
    ) -> Alert:
        """Trigger a new alert."""
        alert = Alert(
            severity=severity,
            title=title,
            message=message,
            tenant_id=tenant_id,
            tags=tags or {},
        )
        
        self.alerts[alert.id] = alert
        
        if len(self.alerts) > self.max_alerts:
            oldest = min(self.alerts.values(), key=lambda a: a.timestamp)
            del self.alerts[oldest.id]
        
        logger.info(
            f"Alert triggered: {severity} — {title}",
            extra={"extra_data": {"alert_id": alert.id, "tenant_id": tenant_id}},
        )

        self._dispatch_handlers(alert)
        return alert

    def trigger_sync(
        self,
        severity: AlertSeverity,
        title: str,
        message: str,
        tenant_id: int | None = None,
        tags: dict[str, str] | None = None,
    ) -> Alert:
        """Trigger alert from sync context (Celery worker)."""
        return self.trigger(severity, title, message, tenant_id=tenant_id, tags=tags)

    def _dispatch_handlers(self, alert: Alert) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._call_handlers(alert))
        except RuntimeError:
            for handler in self.handlers:
                try:
                    if not asyncio.iscoroutinefunction(handler):
                        handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")
            self._publish_realtime(alert)

    def _publish_realtime(self, alert: Alert) -> None:
        try:
            from motopay.realtime.publish import publish_event

            publish_event(
                "alert.new",
                {
                    "id": alert.id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "tenant_id": alert.tenant_id,
                    "acknowledged": alert.acknowledged,
                },
                tenant_id=alert.tenant_id,
            )
        except Exception:
            pass
    
    async def _call_handlers(self, alert: Alert) -> None:
        """Call all registered handlers."""
        for handler in self.handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        self._publish_realtime(alert)
    
    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            return True
        return False
    
    def get_alert(self, alert_id: str) -> Alert | None:
        """Get alert by ID."""
        return self.alerts.get(alert_id)
    
    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        tenant_id: int | None = None,
        acknowledged: bool | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts with optional filtering."""
        alerts = list(self.alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if tenant_id:
            alerts = [a for a in alerts if a.tenant_id == tenant_id]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def clear_old_alerts(self, seconds: int = 86400) -> int:
        """Clear alerts older than specified seconds."""
        import time
        now = time.time()
        old_ids = [
            a_id for a_id, alert in self.alerts.items()
            if (now - alert.timestamp.timestamp()) > seconds
        ]
        for a_id in old_ids:
            del self.alerts[a_id]
        return len(old_ids)


# Global alert manager
alert_manager = AlertManager()


# Alert handler for Telegram (optional)
async def telegram_alert_handler(alert: Alert) -> None:
    """Send alert to Telegram (requires telegram client setup)."""
    if alert.severity != AlertSeverity.CRITICAL:
        return
    
    try:
        _alert_text = f"🚨 ALERTA CRÍTICO\n{alert.title}\n{alert.message}"
        del _alert_text
        # send_telegram_text(chat_id="ADMIN_CHAT_ID", text=message)
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


# Register default handlers
# alert_manager.register_handler(telegram_alert_handler)
