from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_event_repository
from main import app


@dataclass(frozen=True)
class FakeEvent:
    id: int
    event_type: str
    camera_id: str
    track_id: int
    timestamp: float
    message: str
    created_at: datetime


class FakeEventRepository:
    def __init__(self, events: list[FakeEvent]) -> None:
        self.events = events
        self.list_recent_calls: list[tuple[int, str | None]] = []
        self.stats_calls: list[
            tuple[datetime | None, datetime | None, str | None, str | None]
        ] = []

    def list_recent(
        self,
        limit: int = 100,
        camera_id: str | None = None,
    ) -> list[FakeEvent]:
        self.list_recent_calls.append((limit, camera_id))
        events = self.events
        if camera_id is not None:
            events = [event for event in events if event.camera_id == camera_id]
        return events[:limit]

    def get(self, event_id: int) -> FakeEvent | None:
        return next((event for event in self.events if event.id == event_id), None)

    def stats(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        camera_id: str | None = None,
        rule_name: str | None = None,
    ) -> dict[str, object]:
        self.stats_calls.append((start_at, end_at, camera_id, rule_name))
        return {
            "total_event_count": 2,
            "event_count_by_rule_name": {"danger_zone": 2},
            "event_count_by_camera_id": {"gate_01": 2},
            "hourly_event_counts": {"2026-06-22T10:00:00+00:00": 2},
            "latest_event_timestamp": datetime(
                2026,
                6,
                22,
                10,
                30,
                tzinfo=timezone.utc,
            ),
        }


def make_event(event_id: int = 1, created_at: datetime | None = None) -> FakeEvent:
    return FakeEvent(
        id=event_id,
        event_type="danger_zone",
        camera_id="gate_01",
        track_id=42,
        timestamp=123.45,
        message="Track 42 stayed inside the danger zone.",
        created_at=created_at or datetime(2026, 6, 22, 10, 30, tzinfo=timezone.utc),
    )


def make_client(repository: FakeEventRepository) -> TestClient:
    app.dependency_overrides[get_event_repository] = lambda: repository
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)


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
            "camera_id": "gate_01",
            "track_id": 42,
            "timestamp": 123.45,
            "message": "Track 42 stayed inside the danger zone.",
            "created_at": "2026-06-22T10:30:00Z",
        },
        {
            "id": 2,
            "event_type": "danger_zone",
            "camera_id": "gate_01",
            "track_id": 42,
            "timestamp": 123.45,
            "message": "Track 42 stayed inside the danger zone.",
            "created_at": "2026-06-22T10:30:00Z",
        },
    ]
    assert repository.list_recent_calls == [(100, None)]


def test_protected_route_allows_local_access_without_api_key() -> None:
    repository = FakeEventRepository([make_event(event_id=1)])
    client = make_client(repository)

    response = client.get("/events")

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_protected_route_requires_api_key_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-key")
    repository = FakeEventRepository([make_event(event_id=1)])
    client = make_client(repository)

    response = client.get("/events")

    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_protected_route_accepts_valid_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-key")
    repository = FakeEventRepository([make_event(event_id=1)])
    client = make_client(repository)

    response = client.get("/events", headers={"X-API-Key": "secret-key"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()[0]["id"] == 1


def test_protected_route_rejects_invalid_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_KEY", "secret-key")
    repository = FakeEventRepository([make_event(event_id=1)])
    client = make_client(repository)

    response = client.get("/events", headers={"X-API-Key": "wrong-key"})

    app.dependency_overrides.clear()
    assert response.status_code == 401


def test_list_events_passes_limit_to_repository() -> None:
    repository = FakeEventRepository([make_event(event_id=1), make_event(event_id=2)])
    client = make_client(repository)

    response = client.get("/events?limit=1")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == [1]
    assert repository.list_recent_calls == [(1, None)]


def test_list_events_passes_camera_id_to_repository() -> None:
    repository = FakeEventRepository([make_event(event_id=1), make_event(event_id=2)])
    client = make_client(repository)

    response = client.get("/events?camera_id=gate_01")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == [1, 2]
    assert repository.list_recent_calls == [(100, "gate_01")]


def test_latest_events_passes_camera_id_to_repository() -> None:
    repository = FakeEventRepository([make_event(event_id=1)])
    client = make_client(repository)

    response = client.get("/events/latest?camera_id=gate_01&limit=5")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert repository.list_recent_calls == [(5, "gate_01")]


def test_event_stats_passes_filters_to_repository() -> None:
    repository = FakeEventRepository([make_event(event_id=1)])
    client = make_client(repository)

    response = client.get(
        "/events/stats?"
        "camera_id=gate_01&"
        "rule_name=danger_zone&"
        "start_at=2026-06-22T00:00:00Z&"
        "end_at=2026-06-23T00:00:00Z"
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "total_event_count": 2,
        "event_count_by_rule_name": {"danger_zone": 2},
        "event_count_by_camera_id": {"gate_01": 2},
        "hourly_event_counts": {"2026-06-22T10:00:00+00:00": 2},
        "latest_event_timestamp": "2026-06-22T10:30:00Z",
    }
    start_at, end_at, camera_id, rule_name = repository.stats_calls[0]
    assert start_at == datetime(2026, 6, 22, tzinfo=timezone.utc)
    assert end_at == datetime(2026, 6, 23, tzinfo=timezone.utc)
    assert camera_id == "gate_01"
    assert rule_name == "danger_zone"


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
