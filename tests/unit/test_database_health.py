from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine

from app.api import routes
from app.database.health import check_database_health
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
