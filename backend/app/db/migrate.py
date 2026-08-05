from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

from app.db.session import Base


def alembic_config(database_url: str) -> Config:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_migrations(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def ensure_schema(engine: Engine, database_url: str, *, prefer_migrations: bool = True) -> None:
    """Apply schema via Alembic when possible; fall back to metadata.create_all."""
    if database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        return
    if prefer_migrations:
        try:
            run_migrations(database_url)
            return
        except Exception:
            Base.metadata.create_all(bind=engine)
            return
    Base.metadata.create_all(bind=engine)
