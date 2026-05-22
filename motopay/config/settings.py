from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    # Opcional Supabase/deploy: porta 5432 (session/direct) só para migrações; app usa pooling 6543.
    database_migration_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    redis_url: str = "redis://localhost:6379/0"
    redis_socket_connect_timeout_seconds: float = 5.0
    redis_socket_timeout_seconds: float = 10.0
    redis_health_check_interval_seconds: int = 30

    login_rate_limit_enabled: bool = True
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_seconds: int = 900
    refresh_rate_limit_max_attempts: int = 20
    refresh_rate_limit_window_seconds: int = 900
    webhook_rate_limit_max_attempts: int = 30
    webhook_rate_limit_window_seconds: int = 900

    # IPs de proxy reverso confiáveis (vírgula). Só então X-Forwarded-For/X-Real-IP são usados.
    trusted_proxy_ips: str = ""

    asaas_api_key: str = ""
    asaas_api_base_url: str = "https://sandbox.asaas.com/api/v3"
    asaas_webhook_token: str = ""
    # Valida status do pagamento na API Asaas antes de confirmar (requer ASAAS_API_KEY).
    asaas_webhook_verify_with_api: bool = True

    telegram_bot_token: str = ""
    api_public_base_url: str = "http://localhost:8000"
    app_timezone: str = "America/Sao_Paulo"

    # production: definir APP_CORS_ORIGINS (URLs separadas por vírgula). API usa Bearer; credenciais CORS desligadas.
    environment: str = "development"
    cors_origins: str = ""

    # Escape hatches só para staging controlado ou exceções documentadas (.env.example + README).
    allow_production_without_asaas: bool = False
    allow_production_without_telegram: bool = False
    allow_asaas_sandbox_in_production: bool = False

    mercadopago_access_token: str = ""
    mercadopago_webhook_secret: str = ""

    celery_beat_hour: int = 11
    celery_beat_minute: int = 0

    sentry_dsn: str = ""
    openai_api_key: str = ""
    ai_bot_enabled: bool = False

    @model_validator(mode="after")
    def reject_insecure_defaults_in_production(self) -> Settings:
        if self.environment != "production":
            return self
        if not self.jwt_secret or self.jwt_secret.startswith("change-me"):
            raise RuntimeError(
                "JWT_SECRET não foi configurado para produção (use um segredo forte; valores que começam com 'change-me' são recusados)."
            )
        if not self.asaas_webhook_token.strip():
            raise RuntimeError(
                "ASAAS_WEBHOOK_TOKEN não foi configurado para produção (webhook Asaas exige token não vazio)."
            )

        url = self.asaas_api_base_url.lower()
        if "sandbox" in url and not self.allow_asaas_sandbox_in_production:
            raise RuntimeError(
                "Em produção a URL da Asaas deve ser a de produção (não sandbox), "
                "ou defina ALLOW_ASAAS_SANDBOX_IN_PRODUCTION=true só para ambiente controlado."
            )

        if not self.allow_production_without_asaas and not self.asaas_api_key.strip():
            raise RuntimeError(
                "ASAAS_API_KEY é obrigatório em produção (ou ALLOW_PRODUCTION_WITHOUT_ASAAS=true apenas em exceção documentada)."
            )

        if not self.allow_production_without_telegram and not self.telegram_bot_token.strip():
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN é obrigatório em produção (ou ALLOW_PRODUCTION_WITHOUT_TELEGRAM=true apenas em exceção documentada)."
            )

        if not self.cors_origins.strip():
            _logger.warning(
                "CORS_ORIGINS está vazio em production: chamadas cross-origin do admin (ex.: Vercel) falham até definir origens."
            )

        rl = self.redis_url.lower()
        if "localhost" in rl or "127.0.0.1" in rl:
            _logger.warning(
                "REDIS_URL aponta para localhost/127.0.0.1 em production — válido só em cenários pontuais; confirme Redis gerenciado em nuvem."
            )

        du = self.database_url.lower()
        if "localhost" in du or "@127.0.0.1:" in du or "@127.0.0.1/" in du:
            _logger.warning(
                "DATABASE_URL menciona localhost/127.0.0.1 em production — confirme túnel/ambiente antes de escalar."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
