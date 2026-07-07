from __future__ import annotations

from datetime import datetime, timezone

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
sqlalchemy_orm = pytest.importorskip("sqlalchemy.orm")

create_engine = sqlalchemy.create_engine
inspect = sqlalchemy.inspect
Session = sqlalchemy_orm.Session

from app.database.base import Base
from app.repositories.camera_repository import CameraRepository
from app.schemas.cameras import CameraCreate, CameraUpdate


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def test_camera_table_is_created() -> None:
    session = make_session()

    columns = {column["name"] for column in inspect(session.bind).get_columns("cameras")}

    assert {
        "id",
        "name",
        "source_type",
        "source_uri",
        "location",
        "status",
        "last_seen_at",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_camera_repository_create_list_get_update_and_deactivate() -> None:
    session = make_session()
    repository = CameraRepository(session=session)
    last_seen_at = datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc)

    created = repository.create(
        CameraCreate(
            name="Gate 01",
            source_type="rtsp",
            source_uri="rtsp://example.test/gate-01",
            location="North gate",
            last_seen_at=last_seen_at,
        )
    )

    listed = repository.list_cameras(page=1, limit=10)
    found = repository.get_by_id(created.id)
    updated = repository.update(
        created.id,
        CameraUpdate(name="Gate 01 Updated", status="error"),
    )

    assert listed["total"] == 1
    assert found is not None
    assert found.source_uri == "rtsp://example.test/gate-01"
    assert updated is not None
    assert updated.name == "Gate 01 Updated"
    assert updated.status == "error"

    deactivated = repository.deactivate(created.id)

    assert deactivated is not None
    assert deactivated.status == "inactive"


def test_camera_repository_returns_none_for_missing_camera() -> None:
    session = make_session()
    repository = CameraRepository(session=session)

    assert repository.get_by_id(404) is None
    assert repository.update(404, CameraUpdate(name="Missing")) is None
    assert repository.deactivate(404) is None
