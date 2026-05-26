from __future__ import annotations

from unittest.mock import patch

from motopay.infrastructure.db.models import Usuario

from tests.conftest import auth_header, login


def test_ops_summary_requires_admin(client, admin_user: Usuario, dono_user: Usuario):
    dono_tokens = login(client, dono_user.email, "donodono")
    r = client.get("/api/v1/ops/celery/summary", headers=auth_header(dono_tokens["access_token"]))
    assert r.status_code == 403

    admin_tokens = login(client, admin_user.email, "adminadmin")
    with patch(
        "motopay.interfaces.api.routers.ops.get_celery_summary",
        return_value={"workers_online": 1, "active_tasks": 0, "dlq_size": 0},
    ):
        r = client.get(
            "/api/v1/ops/celery/summary",
            headers=auth_header(admin_tokens["access_token"]),
        )
    assert r.status_code == 200
    assert r.json()["workers_online"] == 1


def test_metrics_requires_auth(client):
    r = client.get("/health/metrics")
    assert r.status_code == 401


def test_metrics_with_admin(client, admin_user: Usuario):
    tokens = login(client, admin_user.email, "adminadmin")
    r = client.get("/health/metrics", headers=auth_header(tokens["access_token"]))
    assert r.status_code == 200
    assert "api_requests_total" in r.text or r.headers.get("content-type", "").startswith(
        "text/plain"
    )


def test_alerts_list_requires_auth(client):
    r = client.get("/alerts")
    assert r.status_code == 401


def test_dlq_list_admin(client, admin_user: Usuario):
    tokens = login(client, admin_user.email, "adminadmin")
    with patch("motopay.interfaces.api.routers.ops.get_dlq", return_value=[]):
        r = client.get("/api/v1/ops/dlq", headers=auth_header(tokens["access_token"]))
    assert r.status_code == 200
    assert r.json()["total"] == 0
