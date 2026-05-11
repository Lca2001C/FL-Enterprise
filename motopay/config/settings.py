from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    redis_url: str = "redis://localhost:6379/0"

    asaas_api_key: str = ""
    asaas_api_base_url: str = "https://sandbox.asaas.com/api/v3"
    asaas_webhook_token: str = ""

    telegram_bot_token: str = ""
    api_public_base_url: str = "http://localhost:8000"
    app_timezone: str = "America/Sao_Paulo"

    # production: definir APP_CORS_ORIGINS (URLs separadas por vírgula). API usa Bearer; credenciais CORS desligadas.
    environment: str = "development"
    cors_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
