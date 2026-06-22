from __future__ import annotations

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


def test_save_many_ignores_empty_event_list() -> None:
    session = make_session()
    repository = EventRepository(session=session)

    assert repository.save_many([]) == []
    assert session.scalars(select(EventModel)).all() == []
