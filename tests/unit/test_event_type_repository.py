from __future__ import annotations

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
sqlalchemy_orm = pytest.importorskip("sqlalchemy.orm")

create_engine = sqlalchemy.create_engine
inspect = sqlalchemy.inspect
Session = sqlalchemy_orm.Session

from app.database.base import Base
from app.repositories.event_type_repository import EventTypeRepository
from app.schemas.event_types import EventTypeCreate, EventTypeUpdate


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine, expire_on_commit=False)


def test_event_type_table_is_created() -> None:
    session = make_session()

    columns = {
        column["name"] for column in inspect(session.bind).get_columns("event_types")
    }

    assert {
        "id",
        "key",
        "name",
        "description",
        "default_severity",
        "is_active",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_event_type_repository_create_list_get_update_and_deactivate() -> None:
    session = make_session()
    repository = EventTypeRepository(session=session)

    created = repository.create(
        EventTypeCreate(
            key="person_detected",
            name="Person Detected",
            description="A person was detected.",
        )
    )

    listed = repository.list_event_types(page=1, limit=10)
    found_by_id = repository.get_by_id(created.id)
    found_by_key = repository.get_by_key("person_detected")
    updated = repository.update(
        created.id,
        EventTypeUpdate(
            name="Person Event",
            default_severity="warning",
        ),
    )

    assert listed["total"] == 1
    assert found_by_id is not None
    assert found_by_id.key == "person_detected"
    assert found_by_key is not None
    assert found_by_key.id == created.id
    assert updated is not None
    assert updated.name == "Person Event"
    assert updated.default_severity == "warning"

    deactivated = repository.deactivate(created.id)

    assert deactivated is not None
    assert deactivated.is_active is False


def test_event_type_repository_returns_none_for_missing_event_type() -> None:
    session = make_session()
    repository = EventTypeRepository(session=session)

    assert repository.get_by_id(404) is None
    assert repository.get_by_key("missing") is None
    assert repository.update(404, EventTypeUpdate(name="Missing")) is None
    assert repository.deactivate(404) is None
