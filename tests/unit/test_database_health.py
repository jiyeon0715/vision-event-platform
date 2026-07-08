from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text

from app.api import routes
from app.database.health import check_database_health, initialize_database
from app.database.urls import database_backend, redact_database_url


def test_database_backend_detects_postgresql_without_driver_details() -> None:
    assert database_backend("postgresql://vision:secret@postgres/vision_events") == (
        "postgresql"
    )


def test_database_backend_preserves_sqlite_support() -> None:
    assert database_backend("sqlite:///data/events.db") == "sqlite"


def test_redact_database_url_hides_password() -> None:
    url = redact_database_url("postgresql://vision:secret@postgres/vision_events")

    assert "secret" not in url
    assert "***" in url


def test_check_database_health_returns_ok_for_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")

    assert check_database_health(
        engine=engine,
        database_url="sqlite:///:memory:",
    ) == {"status": "ok", "backend": "sqlite"}


def test_initialize_database_adds_event_dashboard_filter_columns() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(64) NOT NULL,
                    camera_id VARCHAR(128) NOT NULL DEFAULT 'default',
                    track_id INTEGER NOT NULL,
                    timestamp FLOAT NOT NULL,
                    message VARCHAR(500) NOT NULL,
                    snapshot_path VARCHAR(500),
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    initialize_database(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("events")}
    assert {"severity", "status"}.issubset(columns)


def test_initialize_database_seeds_minimal_event_types() -> None:
    engine = create_engine("sqlite:///:memory:")

    initialize_database(engine)

    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT key, default_severity FROM event_types ORDER BY key")
        ).all()

    assert rows == [
        ("custom_event", "info"),
        ("object_detected", "info"),
        ("person_detected", "info"),
        ("vehicle_detected", "info"),
        ("zone_entered", "warning"),
    ]


def test_database_health_endpoint_returns_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.database.health.check_database_health",
        lambda: {"status": "ok", "backend": "postgresql"},
    )

    response = asyncio.run(routes.database_health_check())

    assert response == {"status": "ok", "backend": "postgresql"}


def test_database_health_endpoint_raises_503_when_database_is_unhealthy(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.database.health.check_database_health",
        lambda: {
            "status": "error",
            "backend": "postgresql",
            "error": "OperationalError",
        },
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.database_health_check())

    assert error.value.status_code == 503
    assert error.value.detail == {
        "status": "error",
        "backend": "postgresql",
        "error": "OperationalError",
    }
