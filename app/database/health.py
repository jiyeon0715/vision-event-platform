from __future__ import annotations

from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.database.base import Base
from app.database.models import Event
from app.database.session import get_engine
from app.database.urls import database_backend


def initialize_database(engine: Engine | None = None) -> None:
    """Create application tables when they do not already exist."""

    active_engine = engine or get_engine()
    Base.metadata.create_all(bind=active_engine)
    _ensure_camera_id_column(active_engine)
    _ensure_optional_event_column(active_engine, "severity", "VARCHAR(32)")
    _ensure_optional_event_column(active_engine, "status", "VARCHAR(32)")


def _ensure_camera_id_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("events"):
        return

    columns = {column["name"] for column in inspector.get_columns("events")}
    if "camera_id" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE events "
                "ADD COLUMN camera_id VARCHAR(128) NOT NULL DEFAULT 'default'"
            )
        )


def _ensure_optional_event_column(engine: Engine, column_name: str, column_type: str) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("events"):
        return

    columns = {column["name"] for column in inspector.get_columns("events")}
    if column_name in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(f"ALTER TABLE events ADD COLUMN {column_name} {column_type}")
        )


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
