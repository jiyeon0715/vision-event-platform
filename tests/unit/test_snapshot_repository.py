from __future__ import annotations

from datetime import datetime, timezone

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
sqlalchemy_orm = pytest.importorskip("sqlalchemy.orm")

create_engine = sqlalchemy.create_engine
Session = sqlalchemy_orm.Session

from app.database.base import Base
from app.database.models import Event as EventModel
from app.repositories.snapshot_repository import SnapshotRepository


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def make_event(session: Session, camera_id: str = "gate_01") -> EventModel:
    event = EventModel(
        event_type="danger_zone",
        camera_id=camera_id,
        track_id=42,
        timestamp=123.45,
        message="Track 42 stayed inside the danger zone.",
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def make_snapshot_payload(
    event_id: int,
    camera_id: str = "gate_01",
    file_name: str = "event-1.jpg",
    captured_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "camera_id": camera_id,
        "file_path": f"data/snapshots/{camera_id}/{file_name}",
        "file_name": file_name,
        "width": 1280,
        "height": 720,
        "mime_type": "image/jpeg",
        "captured_at": captured_at
        or datetime(2026, 6, 22, 10, 30, tzinfo=timezone.utc),
    }


def test_create_persists_snapshot() -> None:
    session = make_session()
    event = make_event(session)
    repository = SnapshotRepository(session=session)

    saved = repository.create(make_snapshot_payload(event.id))

    assert saved.id == 1
    assert saved.event_id == event.id
    assert saved.camera_id == "gate_01"
    assert saved.file_path == "data/snapshots/gate_01/event-1.jpg"
    assert saved.file_name == "event-1.jpg"
    assert saved.width == 1280
    assert saved.height == 720
    assert saved.mime_type == "image/jpeg"
    assert saved.created_at is not None


def test_list_by_event_returns_only_event_snapshots_newest_first() -> None:
    session = make_session()
    first_event = make_event(session, camera_id="gate_01")
    second_event = make_event(session, camera_id="gate_02")
    repository = SnapshotRepository(session=session)
    repository.create(
        make_snapshot_payload(
            first_event.id,
            file_name="older.jpg",
            captured_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
        )
    )
    repository.create(
        make_snapshot_payload(
            second_event.id,
            camera_id="gate_02",
            file_name="other-event.jpg",
            captured_at=datetime(2026, 6, 22, 11, 0, tzinfo=timezone.utc),
        )
    )
    repository.create(
        make_snapshot_payload(
            first_event.id,
            file_name="newer.jpg",
            captured_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
        )
    )

    result = repository.list_by_event(first_event.id)

    assert result["total"] == 2
    assert [snapshot.file_name for snapshot in result["items"]] == [
        "newer.jpg",
        "older.jpg",
    ]


def test_get_by_id_returns_none_for_missing_snapshot() -> None:
    session = make_session()
    repository = SnapshotRepository(session=session)

    assert repository.get_by_id(404) is None
