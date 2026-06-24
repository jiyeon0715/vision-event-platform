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
    )


def test_save_persists_event() -> None:
    session = make_session()
    repository = EventRepository(session=session)

    saved = repository.save(make_event())

    persisted = session.scalar(select(EventModel).where(EventModel.id == saved.id))
    assert persisted is not None
    assert persisted.event_type == "danger_zone"
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
            "track_id": 7,
            "timestamp": 12.3,
            "message": "Track 7 stayed inside the danger zone.",
            "snapshot_path": "data/snapshots/event.jpg",
        }
    )

    persisted = session.get(EventModel, saved.id)
    assert persisted is not None
    assert persisted.track_id == 7
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
        track_id=1,
        timestamp=1.0,
        message="Older event",
        created_at=datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc),
    )
    newer = EventModel(
        event_type="danger_zone",
        track_id=2,
        timestamp=2.0,
        message="Newer event",
        created_at=datetime(2026, 6, 22, 11, 0, tzinfo=timezone.utc),
    )
    session.add_all([older, newer])
    session.commit()

    events = repository.list_recent(limit=1)

    assert [event.track_id for event in events] == [2]


def test_get_returns_event_by_id() -> None:
    session = make_session()
    repository = EventRepository(session=session)
    saved = repository.save(make_event(track_id=99))

    found = repository.get(saved.id)

    assert found is not None
    assert found.id == saved.id
    assert found.track_id == 99
