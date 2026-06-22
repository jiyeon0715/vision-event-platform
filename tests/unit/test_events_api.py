from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.routes import get_event_repository
from main import app


@dataclass(frozen=True)
class FakeEvent:
    id: int
    event_type: str
    track_id: int
    timestamp: float
    message: str
    created_at: datetime


class FakeEventRepository:
    def __init__(self, events: list[FakeEvent]) -> None:
        self.events = events
        self.list_recent_limits: list[int] = []

    def list_recent(self, limit: int = 100) -> list[FakeEvent]:
        self.list_recent_limits.append(limit)
        return self.events[:limit]

    def get(self, event_id: int) -> FakeEvent | None:
        return next((event for event in self.events if event.id == event_id), None)


def make_event(event_id: int = 1, created_at: datetime | None = None) -> FakeEvent:
    return FakeEvent(
        id=event_id,
        event_type="danger_zone",
        track_id=42,
        timestamp=123.45,
        message="Track 42 stayed inside the danger zone.",
        created_at=created_at or datetime(2026, 6, 22, 10, 30, tzinfo=timezone.utc),
    )


def make_client(repository: FakeEventRepository) -> TestClient:
    app.dependency_overrides[get_event_repository] = lambda: repository
    return TestClient(app)


def test_list_events_returns_recent_events() -> None:
    repository = FakeEventRepository([make_event(event_id=1), make_event(event_id=2)])
    client = make_client(repository)

    response = client.get("/events")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "event_type": "danger_zone",
            "track_id": 42,
            "timestamp": 123.45,
            "message": "Track 42 stayed inside the danger zone.",
            "created_at": "2026-06-22T10:30:00Z",
        },
        {
            "id": 2,
            "event_type": "danger_zone",
            "track_id": 42,
            "timestamp": 123.45,
            "message": "Track 42 stayed inside the danger zone.",
            "created_at": "2026-06-22T10:30:00Z",
        },
    ]
    assert repository.list_recent_limits == [100]


def test_list_events_passes_limit_to_repository() -> None:
    repository = FakeEventRepository([make_event(event_id=1), make_event(event_id=2)])
    client = make_client(repository)

    response = client.get("/events?limit=1")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == [1]
    assert repository.list_recent_limits == [1]


def test_get_event_returns_single_event() -> None:
    repository = FakeEventRepository([make_event(event_id=7)])
    client = make_client(repository)

    response = client.get("/events/7")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["event_type"] == "danger_zone"


def test_get_event_returns_404_for_missing_event() -> None:
    repository = FakeEventRepository([])
    client = make_client(repository)

    response = client.get("/events/404")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}
