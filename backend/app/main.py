from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    chat,
    decisions,
    documents,
    graph,
    health,
    meetings,
    metrics,
    search,
    users,
)
from app.bootstrap import seed_dev_users
from app.config import get_settings
from app.db.session import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.auth_provider == "dev":
            seed_dev_users(db, settings)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Enterprise Brain API",
        version="0.1.0",
        description="AI-Powered Enterprise Memory & Intelligence Platform (MVP)",
        lifespan=lifespan,
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
    app.include_router(documents.router)
    app.include_router(meetings.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(graph.router)
    app.include_router(decisions.router)
    app.include_router(metrics.router)
    return app


app = create_app()
