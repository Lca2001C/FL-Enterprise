from __future__ import annotations

from motopay.config import get_settings
from motopay.infrastructure.db.models import Operacao
from motopay.infrastructure.payments.mercadopago_client import (
    mp_configured_for_operacao,
    mp_credentials_complete,
    mp_credentials_source,
    mp_public_key_for_operacao,
    mp_token_for_operacao,
    mp_webhook_secret_for_operacao,
    operacao_mp_fields_complete,
    uses_operacao_mercadopago_credentials,
)


def test_operacao_mp_fields_complete_requires_trio():
    op = Operacao(
        nome="X",
        mercadopago_access_token="tok",
        mercadopago_public_key="pk",
        mercadopago_webhook_secret="wh",
    )
    assert operacao_mp_fields_complete(op)


def test_partial_operacao_credentials_strict_mode(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "global-tok")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "global-pk")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "global-wh")
    get_settings.cache_clear()

    op = Operacao(nome="X", mercadopago_access_token="op-only")
    assert uses_operacao_mercadopago_credentials(op)
    assert not operacao_mp_fields_complete(op)
    assert mp_token_for_operacao(op) == ""
    assert mp_configured_for_operacao(op) is False

    get_settings.cache_clear()


def test_complete_operacao_credentials_no_global_fallback(monkeypatch):
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "global-tok")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "global-pk")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "global-wh")
    get_settings.cache_clear()

    op = Operacao(
        nome="X",
        mercadopago_access_token="op-tok",
        mercadopago_public_key="op-pk",
        mercadopago_webhook_secret="op-wh",
    )
    assert mp_token_for_operacao(op) == "op-tok"
    assert mp_public_key_for_operacao(op) == "op-pk"
    assert mp_webhook_secret_for_operacao(op) == "op-wh"
    assert mp_credentials_source(op) == "operacao"
    assert mp_credentials_complete(op)

    get_settings.cache_clear()


def test_empty_operacao_uses_global_fallback(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MERCADOPAGO_CREDENTIALS_MODE", "production")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "global-tok")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY", "global-pk")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "global-wh")
    monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "")
    monkeypatch.setenv("MERCADOPAGO_PUBLIC_KEY_TEST", "")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET_TEST", "")
    get_settings.cache_clear()

    op = Operacao(nome="X")
    assert not uses_operacao_mercadopago_credentials(op)
    assert mp_token_for_operacao(op) == "global-tok"
    assert mp_credentials_source(op) == "global"

    get_settings.cache_clear()
