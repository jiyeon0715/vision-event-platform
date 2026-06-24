from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.database.base import Base
from app.database.models import Event
from app.database.session import get_engine
from app.database.urls import database_backend


def initialize_database(engine: Engine | None = None) -> None:
    """Create application tables when they do not already exist."""

    Base.metadata.create_all(bind=engine or get_engine())


def check_database_health(
    engine: Engine | None = None,
    database_url: str | None = None,
) -> dict[str, str]:
    """Verify the configured database accepts a simple query."""

    active_engine = engine or get_engine()
    active_url = database_url or get_settings().database.url
    result = {
        "status": "ok",
        "backend": database_backend(active_url),
    }

    try:
        with active_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        result["status"] = "error"
        result["error"] = error.__class__.__name__

    return result


__all__ = ["Event", "check_database_health", "initialize_database"]
