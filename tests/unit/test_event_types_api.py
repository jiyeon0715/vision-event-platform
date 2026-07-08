from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_event_type_repository
from app.schemas.event_types import EventTypeCreate, EventTypeUpdate
from main import app


@dataclass(frozen=True)
class FakeEventType:
    id: int
    key: str
    name: str
    description: str | None
    default_severity: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FakeEventTypeRepository:
    def __init__(self, event_types: list[FakeEventType] | None = None) -> None:
        self.event_types = event_types or []
        self.next_id = (
            max((event_type.id for event_type in self.event_types), default=0) + 1
        )

    def create(self, event_type: EventTypeCreate) -> FakeEventType:
        now = datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc)
        values = _schema_values(event_type, exclude_unset=False)
        created = FakeEventType(
            id=self.next_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.next_id += 1
        self.event_types.append(created)
        return created

    def list_event_types(
        self,
        page: int = 1,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> dict[str, object]:
        event_types = self.event_types
        if is_active is not None:
            event_types = [
                event_type
                for event_type in event_types
                if event_type.is_active == is_active
            ]
        start = (page - 1) * limit
        return {"items": event_types[start : start + limit], "total": len(event_types)}

    def get_by_id(self, event_type_id: int) -> FakeEventType | None:
        return next(
            (
                event_type
                for event_type in self.event_types
                if event_type.id == event_type_id
            ),
            None,
        )

    def get_by_key(self, key: str) -> FakeEventType | None:
        return next(
            (event_type for event_type in self.event_types if event_type.key == key),
            None,
        )

    def update(
        self,
        event_type_id: int,
        event_type: EventTypeUpdate,
    ) -> FakeEventType | None:
        existing = self.get_by_id(event_type_id)
        if existing is None:
            return None

        values = _schema_values(event_type, exclude_unset=True)
        updated = replace(
            existing,
            updated_at=datetime(2026, 7, 7, 10, 5, tzinfo=timezone.utc),
            **values,
        )
        self.event_types = [
            updated if event_type.id == event_type_id else event_type
            for event_type in self.event_types
        ]
        return updated

    def deactivate(self, event_type_id: int) -> FakeEventType | None:
        existing = self.get_by_id(event_type_id)
        if existing is None:
            return None

        updated = replace(
            existing,
            is_active=False,
            updated_at=datetime(2026, 7, 7, 10, 10, tzinfo=timezone.utc),
        )
        self.event_types = [
            updated if event_type.id == event_type_id else event_type
            for event_type in self.event_types
        ]
        return updated


def make_event_type(
    event_type_id: int = 1,
    key: str = "person_detected",
    is_active: bool = True,
) -> FakeEventType:
    now = datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc)
    return FakeEventType(
        id=event_type_id,
        key=key,
        name="Person Detected",
        description="A person was detected.",
        default_severity="info",
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def make_client(repository: FakeEventTypeRepository) -> TestClient:
    app.dependency_overrides[get_event_type_repository] = lambda: repository
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)


@pytest.fixture(autouse=True)
def clear_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def test_create_event_type() -> None:
    repository = FakeEventTypeRepository()
    client = make_client(repository)

    response = client.post(
        "/event-types",
        json={
            "key": "person_detected",
            "name": "Person Detected",
            "description": "A person was detected.",
            "default_severity": "info",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["key"] == "person_detected"
    assert response.json()["default_severity"] == "info"
    assert response.json()["is_active"] is True


def test_list_event_types() -> None:
    repository = FakeEventTypeRepository(
        [
            make_event_type(event_type_id=1),
            make_event_type(
                event_type_id=2,
                key="vehicle_detected",
                is_active=False,
            ),
        ]
    )
    client = make_client(repository)

    response = client.get("/event-types?is_active=true")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [event_type["id"] for event_type in response.json()["items"]] == [1]


def test_get_event_type_detail() -> None:
    repository = FakeEventTypeRepository([make_event_type(event_type_id=7)])
    client = make_client(repository)

    response = client.get("/event-types/7")

    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["key"] == "person_detected"


def test_create_event_type_rejects_duplicate_key() -> None:
    repository = FakeEventTypeRepository([make_event_type()])
    client = make_client(repository)

    response = client.post(
        "/event-types",
        json={"key": "person_detected", "name": "Duplicate"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Event type key already exists"}


def test_update_event_type() -> None:
    repository = FakeEventTypeRepository([make_event_type(event_type_id=1)])
    client = make_client(repository)

    response = client.patch(
        "/event-types/1",
        json={
            "name": "Person Event",
            "description": "Updated description",
            "default_severity": "warning",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Person Event"
    assert response.json()["description"] == "Updated description"
    assert response.json()["default_severity"] == "warning"


def test_update_event_type_rejects_duplicate_key() -> None:
    repository = FakeEventTypeRepository(
        [
            make_event_type(event_type_id=1, key="person_detected"),
            make_event_type(event_type_id=2, key="vehicle_detected"),
        ]
    )
    client = make_client(repository)

    response = client.patch("/event-types/1", json={"key": "vehicle_detected"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Event type key already exists"}


def test_delete_event_type_marks_inactive() -> None:
    repository = FakeEventTypeRepository([make_event_type(event_type_id=1)])
    client = make_client(repository)

    response = client.delete("/event-types/1")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert repository.get_by_id(1).is_active is False


def _schema_values(
    schema: EventTypeCreate | EventTypeUpdate,
    exclude_unset: bool,
) -> dict[str, object]:
    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_unset=exclude_unset)
    return schema.dict(exclude_unset=exclude_unset)
