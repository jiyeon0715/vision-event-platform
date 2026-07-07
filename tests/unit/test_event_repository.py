from __future__ import annotations

from datetime import datetime, timezone

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
sqlalchemy_orm = pytest.importorskip("sqlalchemy.orm")

create_engine = sqlalchemy.create_engine
select = sqlalchemy.select
Session = sqlalchemy_orm.Session

from app.database.base import Base
from app.database.models import Event as EventModel
from app.repositories.event_repository import EventRepository
from app.rules.danger_zone_rule import Event


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def make_event(track_id: int = 42) -> Event:
    return Event(
        event_type="danger_zone",
        track_id=track_id,
        timestamp=123.45,
        message=f"Track {track_id} stayed inside the danger zone.",
        camera_id="gate_01",
    )


def test_save_persists_event() -> None:
    session = make_session()
    repository = EventRepository(session=session)

    saved = repository.save(make_event())

    persisted = session.scalar(select(EventModel).where(EventModel.id == saved.id))
    assert persisted is not None
    assert persisted.event_type == "danger_zone"
    assert persisted.camera_id == "gate_01"
    assert persisted.track_id == 42
    assert persisted.timestamp == 123.45
    assert persisted.message == "Track 42 stayed inside the danger zone."


def test_save_many_persists_multiple_events() -> None:
    session = make_session()
    repository = EventRepository(session=session)

    saved = repository.save_many([make_event(track_id=1), make_event(track_id=2)])

    persisted = session.scalars(select(EventModel).order_by(EventModel.track_id)).all()
    assert [event.track_id for event in saved] == [1, 2]
    assert [event.track_id for event in persisted] == [1, 2]


def test_save_accepts_dict_event_payload() -> None:
    session = make_session()
    repository = EventRepository(session=session)

    saved = repository.save(
        {
            "event_type": "danger_zone",
            "camera_id": "gate_02",
            "track_id": 7,
            "timestamp": 12.3,
            "message": "Track 7 stayed inside the danger zone.",
            "severity": "critical",
            "status": "new",
            "snapshot_path": "data/snapshots/event.jpg",
        }
    )

    persisted = session.get(EventModel, saved.id)
    assert persisted is not None
    assert persisted.track_id == 7
    assert persisted.camera_id == "gate_02"
    assert persisted.severity == "critical"
    assert persisted.status == "new"
    assert persisted.snapshot_path == "data/snapshots/event.jpg"


def test_save_many_ignores_empty_event_list() -> None:
    session = make_session()
    repository = EventRepository(session=session)

    assert repository.save_many([]) == []
    assert session.scalars(select(EventModel)).all() == []


def test_list_recent_returns_newest_events_first() -> None:
    session = make_session()
    repository = EventRepository(session=session)
    older = EventModel(
        event_type="danger_zone",
        camera_id="gate_01",
        track_id=1,
        timestamp=1.0,
        message="Older event",
        created_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
    )
    newer = EventModel(
        event_type="danger_zone",
        camera_id="gate_02",
        track_id=2,
        timestamp=2.0,
        message="Newer event",
        created_at=datetime(2026, 6, 22, 11, 0, tzinfo=timezone.utc),
    )
    session.add_all([older, newer])
    session.commit()

    events = repository.list_recent(limit=1)

    assert [event.track_id for event in events] == [2]


def test_list_recent_filters_by_camera_id() -> None:
    session = make_session()
    repository = EventRepository(session=session)
    repository.save(make_event(track_id=1))
    repository.save(
        Event(
            event_type="danger_zone",
            track_id=2,
            timestamp=123.45,
            message="Track 2 stayed inside the danger zone.",
            camera_id="gate_02",
        )
    )

    events = repository.list_recent(camera_id="gate_02")

    assert [event.track_id for event in events] == [2]
    assert [event.camera_id for event in events] == ["gate_02"]


def test_list_events_filters_and_paginates() -> None:
    session = make_session()
    repository = EventRepository(session=session)
    session.add_all(
        [
            EventModel(
                event_type="danger_zone",
                camera_id="gate_01",
                track_id=1,
                timestamp=1.0,
                message="First event",
                severity="critical",
                status="new",
                created_at=datetime(2026, 6, 22, 10, 15, tzinfo=timezone.utc),
            ),
            EventModel(
                event_type="danger_zone",
                camera_id="gate_01",
                track_id=2,
                timestamp=2.0,
                message="Second event",
                severity="critical",
                status="acknowledged",
                created_at=datetime(2026, 6, 22, 10, 45, tzinfo=timezone.utc),
            ),
            EventModel(
                event_type="loitering",
                camera_id="gate_02",
                track_id=3,
                timestamp=3.0,
                message="Third event",
                severity="warning",
                status="new",
                created_at=datetime(2026, 6, 22, 11, 5, tzinfo=timezone.utc),
            ),
        ]
    )
    session.commit()

    result = repository.list_events(
        page=1,
        limit=1,
        camera_id="gate_01",
        event_type="danger_zone",
        severity="critical",
        status="acknowledged",
        date_from=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
        date_to=datetime(2026, 6, 22, 10, 59, tzinfo=timezone.utc),
    )

    assert result["total"] == 1
    assert [event.track_id for event in result["items"]] == [2]


def test_get_returns_event_by_id() -> None:
    session = make_session()
    repository = EventRepository(session=session)
    saved = repository.save(make_event(track_id=99))

    found = repository.get(saved.id)

    assert found is not None
    assert found.id == saved.id
    assert found.track_id == 99


def test_stats_aggregates_events_and_filters() -> None:
    session = make_session()
    repository = EventRepository(session=session)
    session.add_all(
        [
            EventModel(
                event_type="danger_zone",
                camera_id="gate_01",
                track_id=1,
                timestamp=1.0,
                message="First event",
                status="new",
                created_at=datetime(2026, 6, 22, 10, 15, tzinfo=timezone.utc),
            ),
            EventModel(
                event_type="danger_zone",
                camera_id="gate_01",
                track_id=2,
                timestamp=2.0,
                message="Second event",
                status="acknowledged",
                created_at=datetime(2026, 6, 22, 10, 45, tzinfo=timezone.utc),
            ),
            EventModel(
                event_type="loitering",
                camera_id="gate_02",
                track_id=3,
                timestamp=3.0,
                message="Third event",
                status="new",
                created_at=datetime(2026, 6, 22, 11, 5, tzinfo=timezone.utc),
            ),
        ]
    )
    session.commit()

    stats = repository.stats(
        start_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 6, 22, 10, 59, tzinfo=timezone.utc),
        camera_id="gate_01",
        rule_name="danger_zone",
    )

    assert stats == {
        "total_event_count": 2,
        "event_count_by_type": {"danger_zone": 2},
        "event_count_by_rule_name": {"danger_zone": 2},
        "event_count_by_camera_id": {"gate_01": 2},
        "event_count_by_status": {"acknowledged": 1, "new": 1},
        "hourly_event_counts": {"2026-06-22T10:00:00": 2},
        "latest_event_timestamp": datetime(2026, 6, 22, 10, 45),
    }
