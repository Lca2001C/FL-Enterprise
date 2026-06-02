from __future__ import annotations

from motopay.config import get_settings
from motopay.config.mercadopago_credentials import (
    effective_mercadopago_access_token,
    effective_mercadopago_credentials_mode,
    effective_mercadopago_public_key,
    effective_mercadopago_webhook_secret,
)
from motopay.infrastructure.payments.mercadopago_client import payer_email_for_mercadopago


def test_effective_credentials_use_test_mode_when_configured(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "test")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "prod-token")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "prod-pk")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "prod-wh")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "test-token")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY_TEST", "test-pk")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET_TEST", "test-wh")
    get_settings.cache_clear()

    assert effective_mercadopago_credentials_mode() == "test"
    assert effective_mercadopago_access_token() == "test-token"
    assert effective_mercadopago_public_key() == "test-pk"
    assert effective_mercadopago_webhook_secret() == "test-wh"
    get_settings.cache_clear()


def test_effective_credentials_fallback_to_production_without_test_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "test")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "prod-token")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "")
    get_settings.cache_clear()

    assert effective_mercadopago_credentials_mode() == "production"
    assert effective_mercadopago_access_token() == "prod-token"
    get_settings.cache_clear()


def test_effective_credentials_force_production_in_production_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "x" + "a" * 48)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:strongpass@prod-db.example:5432/motopay",
    )
    monkeypatch.setenv("REDIS_URL", "rediss://:strong-redis@redis.example:6380/0")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "test")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "prod-token")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "test-token")
    get_settings.cache_clear()

    assert effective_mercadopago_credentials_mode() == "production"
    assert effective_mercadopago_access_token() == "prod-token"
    get_settings.cache_clear()


def test_payer_email_uses_testuser_domain_in_test_mode(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "test")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "test-token")
    get_settings.cache_clear()

    assert payer_email_for_mercadopago(7) == "test_user_7@testuser.com"
    get_settings.cache_clear()


def test_payer_email_uses_motopay_domain_in_production_mode(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "production")
    get_settings.cache_clear()

    assert payer_email_for_mercadopago(7) == "cliente7@motopay.local"
    get_settings.cache_clear()
