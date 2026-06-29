from __future__ import annotations

import os
from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
from fastapi.testclient import TestClient
from motopay.config.settings import get_settings
from motopay.domain.enums import UserRole
from motopay.infrastructure.db.base import Base
from motopay.infrastructure.db.models import Moto, Operacao, Usuario
from motopay.infrastructure.db.session import get_db
from motopay.interfaces.api.main import app
from motopay.services.auth_service import hash_password
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/motopay_test",
)


def _ensure_test_env() -> None:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["JWT_SECRET"] = "test-jwt-secret-not-for-production"
    os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")
    # Neutraliza TODAS as credenciais MP: sem isso, valores do .env local
    # vazam via pydantic-settings (env_file) e os testes divergem do CI.
    os.environ["MERCADOPAGO_WEBHOOK_SECRET"] = ""
    os.environ["MERCADOPAGO_WEBHOOK_SECRET_TEST"] = ""
    os.environ["MERCADOPAGO_ACCESS_TOKEN"] = ""
    os.environ["MERCADOPAGO_PUBLIC_KEY"] = ""
    os.environ["MERCADOPAGO_CREDENTIALS_MODE"] = "test"
    os.environ["MERCADOPAGO_ACCESS_TOKEN_TEST"] = "TEST-token"
    os.environ["MERCADOPAGO_PUBLIC_KEY_TEST"] = "TEST-pk"
    os.environ["MERCADOPAGO_WEBHOOK_SECRET_TEST"] = "whsec-test-webhook-secret-12"
    os.environ["ENCRYPTION_KEY"] = "sqDDNXiljsDzXzwlu2WJ-z00XTD04TLW967jWrYCF18="
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOGIN_RATE_LIMIT_ENABLED"] = "false"
    get_settings.cache_clear()


_ensure_test_env()

TEST_MP_WEBHOOK_SECRET = "whsec-test-webhook-secret-12"
_PRODUCTION_ENCRYPTION_KEY = "sqDDNXiljsDzXzwlu2WJ-z00XTD04TLW967jWrYCF18="


def mp_webhook_headers(data_id: str, *, secret: str | None = None) -> dict[str, str]:
    """Headers x-signature/x-request-id válidos para webhooks MP nos testes."""
    from tests.test_mercadopago_client import _signature_headers

    return _signature_headers(
        secret=secret or TEST_MP_WEBHOOK_SECRET,
        data_id=data_id,
    )


def apply_base_production_env(monkeypatch: MonkeyPatch) -> None:
    """Env mínimo para Settings() em ENVIRONMENT=production (igual CI)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pw@prod-db.example:5432/motopay")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "x" + "a" * 48)
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_ID", "mp-oauth-client-id")
    monkeypatch.setenv("MERCADOPAGO_OAUTH_CLIENT_SECRET", "mp-oauth-client-secret")
    monkeypatch.setenv("MERCADOPAGO_WEBHOOK_SECRET", "whsec-production-webhook-secret")
    monkeypatch.setenv("ENCRYPTION_KEY", _PRODUCTION_ENCRYPTION_KEY)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("REDIS_URL", "rediss://:strong-redis-secret@redis.example:6380/0")
    monkeypatch.setenv("CORS_ORIGINS", "https://admin.example.test")
    monkeypatch.delenv("ALLOW_PRODUCTION_WITHOUT_MERCADOPAGO", raising=False)
    monkeypatch.delenv("ALLOW_PRODUCTION_WITHOUT_TELEGRAM", raising=False)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres de teste indisponível ({TEST_DATABASE_URL}): {exc}")
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autocommit=False, autoflush=False, class_=Session)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def operacao_a(db_session: Session) -> Operacao:
    op = Operacao(nome="Operação A")
    db_session.add(op)
    db_session.flush()
    return op


@pytest.fixture
def operacao_b(db_session: Session) -> Operacao:
    op = Operacao(nome="Operação B")
    db_session.add(op)
    db_session.flush()
    return op


@pytest.fixture
def admin_user(db_session: Session) -> Usuario:
    user = Usuario(
        email="admin@test.local",
        senha_hash=hash_password("adminadmin"),
        tipo=UserRole.ADMIN.value,
        operacao_id=None,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def dono_user(db_session: Session, operacao_a: Operacao) -> Usuario:
    user = Usuario(
        email="dono@test.local",
        senha_hash=hash_password("donodono"),
        tipo=UserRole.DONO.value,
        operacao_id=operacao_a.id,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def moto_operacao_a(db_session: Session, operacao_a: Operacao) -> Moto:
    moto = Moto(
        operacao_id=operacao_a.id,
        placa="AAA1A11",
        modelo="CG 160",
        status="disponivel",
        km=100,
    )
    db_session.add(moto)
    db_session.flush()
    return moto


@pytest.fixture
def moto_operacao_b(db_session: Session, operacao_b: Operacao) -> Moto:
    moto = Moto(
        operacao_id=operacao_b.id,
        placa="BBB2B22",
        modelo="Fan 160",
        status="disponivel",
        km=200,
    )
    db_session.add(moto)
    db_session.flush()
    return moto


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()
