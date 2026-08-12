from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine
from app.services.graph import GraphStore
from app.services.vector import VectorStore

router = APIRouter(tags=["health"])


@router.get("/healthz")
@router.get("/livez")
def healthz():
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    settings = get_settings()
    checks: dict[str, bool] = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False

    try:
        graph = GraphStore(settings)
        checks["neo4j"] = graph.ping()
        graph.close()
    except Exception:
        checks["neo4j"] = False

    try:
        VectorStore(settings).ensure_collection()
        checks["qdrant"] = True
    except Exception:
        checks["qdrant"] = False

    if settings.queue_backend == "redis":
        try:
            import redis

            redis.Redis.from_url(settings.redis_url).ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False

    ready = all(checks.values())
    return {"ready": ready, "checks": checks, "environment": settings.environment}
