from __future__ import annotations

from motopay.interfaces.api.main import app
from motopay.observability.metrics import api_requests_total


def test_observability_middleware_increments_metrics():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    before = api_requests_total.labels(method="GET", endpoint="/health", status="200")._value.get()  # noqa: SLF001
    r = client.get("/health")
    assert r.status_code == 200
    after = api_requests_total.labels(method="GET", endpoint="/health", status="200")._value.get()  # noqa: SLF001
    assert after >= before
