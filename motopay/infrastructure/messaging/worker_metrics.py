"""Prometheus metrics HTTP server for Celery workers."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from motopay.config import get_settings
from motopay.observability.logger import get_logger

logger = get_logger(__name__)
_server_started = False


class _MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        payload = generate_latest()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def start_worker_metrics_server() -> None:
    global _server_started
    if _server_started:
        return
    port = get_settings().worker_metrics_port
    server = HTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="worker-metrics")
    thread.start()
    _server_started = True
    logger.info("Worker metrics server listening on :%s/metrics", port)
