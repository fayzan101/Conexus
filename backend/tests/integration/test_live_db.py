"""Live data-plane integration tests (Compose Postgres/Redis/Qdrant).

Run: LIVE_INTEGRATION=1 pytest -m integration
CI spins docker compose services then runs this mark.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

LIVE = os.getenv("LIVE_INTEGRATION", "").lower() in {"1", "true", "yes"}


@pytest.mark.skipif(not LIVE, reason="Set LIVE_INTEGRATION=1 with Compose services up")
def test_postgres_roundtrip():
    from sqlalchemy import create_engine, text

    url = os.getenv("DATABASE_URL", "postgresql+psycopg://eb:eb@localhost:5432/enterprise_brain")
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
    engine.dispose()


@pytest.mark.skipif(not LIVE, reason="Set LIVE_INTEGRATION=1 with Compose services up")
def test_redis_queue_ping():
    import redis

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(url)
    assert client.ping() is True
    client.close()


@pytest.mark.skipif(not LIVE, reason="Set LIVE_INTEGRATION=1 with Compose services up")
def test_qdrant_collections():
    import httpx

    base = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
    resp = httpx.get(f"{base}/collections", timeout=10.0)
    assert resp.status_code == 200


@pytest.mark.skipif(not LIVE, reason="Set LIVE_INTEGRATION=1 with Compose services up")
def test_settings_crypto_against_live_postgres(tmp_path):
    """Ensure AES-GCM tenant keys persist on live Postgres."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import Settings
    from app.db.session import Base
    from app.services.security import decrypt_credentials, encrypt_credentials, ensure_tenant_key

    url = os.getenv("DATABASE_URL", "postgresql+psycopg://eb:eb@localhost:5432/enterprise_brain")
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    settings = Settings(
        environment="test",
        auth_provider="dev",
        secret_key="integration-secret",
        kms_master_key="integration-kms",
        database_url=url,
        embedding_provider="hash",
    )
    try:
        key = ensure_tenant_key(db, settings, "integration-tenant")
        blob = encrypt_credentials(settings, "integration-tenant", {"access_token": "x"}, key.wrapped_dek)
        assert decrypt_credentials(settings, "integration-tenant", blob, key.wrapped_dek)["access_token"] == "x"
    finally:
        db.close()
        engine.dispose()
