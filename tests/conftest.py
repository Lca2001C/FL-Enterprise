from __future__ import annotations

import os
from collections.abc import Generator

import pytest
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
    os.environ["MERCADOPAGO_WEBHOOK_SECRET"] = ""
    os.environ["MERCADOPAGO_CREDENTIALS_MODE"] = "test"
    os.environ["MERCADOPAGO_ACCESS_TOKEN_TEST"] = "TEST-token"
    os.environ["MERCADOPAGO_PUBLIC_KEY_TEST"] = "TEST-pk"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOGIN_RATE_LIMIT_ENABLED"] = "false"
    get_settings.cache_clear()


_ensure_test_env()


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
