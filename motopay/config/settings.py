from __future__ import annotations

import logging
from datetime import date, datetime
from functools import lru_cache
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

_INSECURE_PASSWORDS = frozenset({"", "postgres", "change-me"})


def _password_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.password is None:
        return None
    return unquote(parsed.password)


def _redis_url_has_password(redis_url: str) -> bool:
    parsed = urlparse(redis_url)
    return bool(parsed.password and parsed.password.strip())


def _database_password_is_insecure(database_url: str, postgres_password: str) -> bool:
    from_url = _password_from_url(database_url)
    password = from_url if from_url is not None else postgres_password.strip()
    if not password or password.lower() in _INSECURE_PASSWORDS or password.startswith("change-me"):
        return True
    return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    # Credencial Postgres usada pelo docker-compose (validada em produção junto com DATABASE_URL).
    postgres_password: str = ""
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

    telegram_bot_token: str = ""
    api_public_base_url: str = "http://localhost:8000"
    upload_dir: str = "/data/uploads"
    app_timezone: str = "America/Sao_Paulo"

    # Storage de imagens (motos): "local" (disco em upload_dir) ou "s3" (S3-compatível).
    # Use "s3" em plataformas de disco efêmero (Render, Railway). Veja DEPLOY.md.
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""  # vazio = AWS S3; preencha p/ R2/B2/Spaces/MinIO
    s3_region: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    # production: definir APP_CORS_ORIGINS (URLs separadas por vírgula). API usa Bearer; credenciais CORS desligadas.
    environment: str = "development"
    cors_origins: str = ""

    # Escape hatches só para staging controlado ou exceções documentadas (.env.example + README).
    allow_production_without_mercadopago: bool = False
    allow_production_without_telegram: bool = False
    # Redis gerenciado em rede privada e sem senha (ex.: Render Key Value interno):
    # a conexão não é exposta à internet, então a ausência de senha é aceitável.
    allow_production_redis_without_auth: bool = False
    allow_webhook_token_in_query: bool = True

    mercadopago_access_token: str = ""
    mercadopago_public_key: str = ""
    mercadopago_webhook_secret: str = ""
    mercadopago_credentials_mode: str = "test"
    mercadopago_access_token_test: str = ""
    mercadopago_public_key_test: str = ""
    mercadopago_webhook_secret_test: str = ""
    mercadopago_oauth_client_id: str = ""
    mercadopago_oauth_client_secret: str = ""
    mercadopago_oauth_redirect_uri: str = ""
    payer_portal_base_url: str = ""
    payer_portal_token_ttl_days: int = 30

    celery_beat_hour: int = 11
    celery_beat_minute: int = 0
    celery_queue_backlog_threshold: int = 100
    celery_stuck_task_seconds: int = 600
    worker_metrics_port: int = 9808
    worker_metrics_host: str = "127.0.0.1"
    metrics_token: str = ""
    log_level: str = "INFO"

    sentry_dsn: str = ""
    openai_api_key: str = ""
    ai_bot_enabled: bool = False

    @model_validator(mode="after")
    def validate_storage_backend(self) -> Settings:
        backend = (self.storage_backend or "local").strip().lower()
        if backend not in ("local", "s3"):
            raise RuntimeError(
                f"STORAGE_BACKEND inválido: {self.storage_backend!r}. Use 'local' ou 's3'."
            )
        if backend == "s3":
            missing = [
                name
                for name, value in (
                    ("S3_BUCKET", self.s3_bucket),
                    ("S3_ACCESS_KEY_ID", self.s3_access_key_id),
                    ("S3_SECRET_ACCESS_KEY", self.s3_secret_access_key),
                )
                if not value.strip()
            ]
            if missing:
                raise RuntimeError(
                    "STORAGE_BACKEND=s3 exige: " + ", ".join(missing) + " (veja DEPLOY.md)."
                )
        return self

    @model_validator(mode="after")
    def reject_insecure_defaults_in_production(self) -> Settings:
        if self.environment != "production":
            return self
        if (self.storage_backend or "local").strip().lower() == "local":
            _logger.warning(
                "STORAGE_BACKEND=local em production: imagens de motos ficam no disco "
                "(UPLOAD_DIR=%s). Garanta um volume/disco persistente; em plataformas "
                "de disco efêmero (Render, Railway) as imagens somem no redeploy — use "
                "STORAGE_BACKEND=s3 (S3/R2/B2/Spaces). Veja DEPLOY.md.",
                self.upload_dir,
            )
        # Acumula TODAS as variáveis faltando e falha uma única vez — evita o
        # "gato e rato" de descobrir um erro por deploy.
        errors: list[str] = []
        if not self.jwt_secret or self.jwt_secret.startswith("change-me"):
            errors.append(
                "JWT_SECRET: defina um segredo forte (gere com `openssl rand -hex 32`; "
                "valores que começam com 'change-me' são recusados)."
            )
        if not self.allow_production_without_mercadopago and not self.mercadopago_access_token.strip():
            errors.append(
                "MERCADOPAGO_ACCESS_TOKEN: obrigatório em produção "
                "(ou ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO=true para subir sem Mercado Pago temporariamente)."
            )
        if not self.allow_production_without_telegram and not self.telegram_bot_token.strip():
            errors.append(
                "TELEGRAM_BOT_TOKEN: obrigatório em produção "
                "(ou ALLOW_PRODUCTION_WITHOUT_TELEGRAM=true para subir sem o bot temporariamente)."
            )
        if _database_password_is_insecure(self.database_url, self.postgres_password):
            errors.append(
                "POSTGRES_PASSWORD / senha em DATABASE_URL: use senha forte "
                "(valores 'postgres' e 'change-me' são recusados)."
            )
        if not _redis_url_has_password(self.redis_url) and not self.allow_production_redis_without_auth:
            errors.append(
                "REDIS_URL: exige autenticação (ex.: rediss://:SENHA@host:6379/0). "
                "Em Redis de rede privada sem senha (ex.: Render Key Value interno), "
                "defina ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH=true."
            )
        if errors:
            raise RuntimeError(
                "Configuração de produção incompleta — corrija TODAS as variáveis abaixo "
                "(detalhes em DEPLOY.md, Apêndice A):\n  - " + "\n  - ".join(errors)
            )

        if not _redis_url_has_password(self.redis_url) and self.allow_production_redis_without_auth:
            _logger.warning(
                "REDIS_URL sem senha aceito em production (ALLOW_PRODUCTION_REDIS_WITHOUT_AUTH=true): "
                "garanta que o Redis está em rede privada e NÃO exposto à internet."
            )

        self.allow_webhook_token_in_query = False

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

        if not self.trusted_proxy_ips.strip():
            _logger.warning(
                "TRUSTED_PROXY_IPS está vazio em production: quando atrás de Railway/Render/Cloudflare, "
                "o rate-limiting usará o IP do proxy em vez do IP real do cliente, tornando-o ineficaz. "
                "Defina TRUSTED_PROXY_IPS com os CIDRs do seu proxy reverso (ex.: 127.0.0.1,10.0.0.0/8)."
            )

        if not self.sentry_dsn.strip():
            _logger.warning(
                "SENTRY_DSN não configurado em production: erros não serão capturados automaticamente. "
                "Crie um projeto em sentry.io e defina SENTRY_DSN para rastreamento de erros em produção."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def app_today() -> date:
    """Data atual no fuso horário configurado da aplicação (APP_TIMEZONE).

    Usar sempre esta função em vez de date.today(): em servidores UTC,
    date.today() vira o dia 3h antes do Brasil, deslocando vencimentos,
    juros e filtros de período.
    """
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()
