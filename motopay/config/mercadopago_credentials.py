from __future__ import annotations

import logging

from motopay.config.settings import Settings, get_settings

_logger = logging.getLogger(__name__)


def effective_mercadopago_credentials_mode(settings: Settings | None = None) -> str:
    """Retorna 'test' ou 'production'. Em ENVIRONMENT=production sempre 'production'."""
    s = settings or get_settings()
    if s.environment == "production":
        return "production"
    mode = (s.mercadopago_credentials_mode or "test").strip().lower()
    if mode not in ("test", "production"):
        mode = "test"
    if mode == "test" and s.mercadopago_access_token_test.strip():
        return "test"
    if mode == "test" and not s.mercadopago_access_token_test.strip():
        _logger.warning(
            "MERCADOPAGO_CREDENTIALS_MODE=test sem MERCADOPAGO_ACCESS_TOKEN_TEST; "
            "usando credenciais de produção."
        )
    return "production"


def effective_mercadopago_access_token(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    if effective_mercadopago_credentials_mode(s) == "test":
        return s.mercadopago_access_token_test.strip()
    return s.mercadopago_access_token.strip()


def effective_mercadopago_public_key(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    if effective_mercadopago_credentials_mode(s) == "test":
        return s.mercadopago_public_key_test.strip()
    return s.mercadopago_public_key.strip()


def effective_mercadopago_webhook_secret(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    if effective_mercadopago_credentials_mode(s) == "test":
        return s.mercadopago_webhook_secret_test.strip()
    return s.mercadopago_webhook_secret.strip()
