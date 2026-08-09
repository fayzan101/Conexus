from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.bootstrap import seed_dev_users
from app.config import Settings, get_settings
from app.db.models import Role, User
from app.db.session import Base, get_db
from app.deps import hash_password
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        secret_key="test-secret",
        auth_provider="dev",
        environment="test",
        auto_migrate=False,
        embedding_provider="hash",
        llm_api_key="",
        queue_backend="memory",
        queue_inline=True,
        connector_auto_ingest=False,
        event_bus_backend="memory",
        default_tenant_id="default",
        hybrid_rerank=True,
        hybrid_graph_hops=0,
        dev_admin_email="admin@example.com",
        dev_admin_password="admin123",
        dev_user_email="user@example.com",
        dev_user_password="user123",
        object_store_endpoint="http://localhost:9000",
        neo4j_uri="bolt://localhost:7687",
        qdrant_url="http://localhost:6333",
    )


@pytest.fixture
def db_engine(test_settings: Settings):
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(db_engine) -> Session:
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_db(db: Session, test_settings: Settings) -> Session:
    seed_dev_users(db, test_settings)
    return db


@pytest.fixture
def app(db: Session, test_settings: Settings, monkeypatch: pytest.MonkeyPatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", test_settings.database_url)
    monkeypatch.setenv("SECRET_KEY", test_settings.secret_key)
    monkeypatch.setenv("AUTH_PROVIDER", "dev")
    monkeypatch.setenv("AUTO_MIGRATE", "false")

    application = create_app(enable_lifespan=False)

    def _settings() -> Settings:
        return test_settings

    def _get_db():
        try:
            yield db
        finally:
            pass

    application.dependency_overrides[get_settings] = _settings
    application.dependency_overrides[get_db] = _get_db
    yield application
    application.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def client(app, seeded_db: Session) -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client: TestClient, test_settings: Settings) -> str:
    res = client.post(
        "/v1/auth/login",
        json={"email": test_settings.dev_admin_email, "password": test_settings.dev_admin_password},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def user_token(client: TestClient, test_settings: Settings) -> str:
    res = client.post(
        "/v1/auth/login",
        json={"email": test_settings.dev_user_email, "password": test_settings.dev_user_password},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}


def make_user(db: Session, email: str, password: str, role: Role = Role.employee, tenant_id: str = "default") -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0],
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
