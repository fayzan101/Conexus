from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    chat,
    connectors,
    decisions,
    documents,
    graph,
    health,
    intelligence,
    knowledge,
    meetings,
    metrics,
    os_platform,
    projects,
    search,
    security,
    timeline,
    users,
)
from app.bootstrap import seed_dev_users
from app.config import get_settings
from app.db.migrate import ensure_schema
from app.db.session import SessionLocal, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.auto_migrate:
        ensure_schema(engine, settings.database_url, prefer_migrations=True)
    db = SessionLocal()
    try:
        if settings.auth_provider == "dev":
            seed_dev_users(db, settings)
    finally:
        db.close()
    yield


def create_app(*, enable_lifespan: bool = True) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Enterprise Brain API",
        version="0.1.0",
        description="AI-Powered Enterprise Memory & Intelligence Platform (MVP)",
        lifespan=lifespan if enable_lifespan else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(projects.router)
    app.include_router(documents.router)
    app.include_router(meetings.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(graph.router)
    app.include_router(decisions.router)
    app.include_router(connectors.router)
    app.include_router(timeline.router)
    app.include_router(intelligence.router)
    app.include_router(knowledge.router)
    app.include_router(security.router)
    app.include_router(os_platform.router)
    app.include_router(metrics.router)
    return app


app = create_app()
