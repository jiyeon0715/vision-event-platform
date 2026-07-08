from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_snapshot_repository
from main import app


@dataclass(frozen=True)
class FakeSnapshot:
    id: int
    event_id: int
    camera_id: str
    file_path: str
    file_name: str
    captured_at: datetime
    created_at: datetime
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None


class FakeSnapshotRepository:
    def __init__(self, snapshots: list[FakeSnapshot]) -> None:
        self.snapshots = snapshots
        self.list_by_event_calls: list[tuple[int, int, int]] = []

    def create(self, snapshot: object) -> object:
        return snapshot

    def list_by_event(
        self,
        event_id: int,
        page: int = 1,
        limit: int = 100,
    ) -> dict[str, object]:
        self.list_by_event_calls.append((event_id, page, limit))
        snapshots = [
            snapshot for snapshot in self.snapshots if snapshot.event_id == event_id
        ]
        start = (page - 1) * limit
        return {"items": snapshots[start : start + limit], "total": len(snapshots)}

    def get_by_id(self, snapshot_id: int) -> FakeSnapshot | None:
        return next(
            (snapshot for snapshot in self.snapshots if snapshot.id == snapshot_id),
            None,
        )


def make_snapshot(
    snapshot_id: int = 1,
    event_id: int = 10,
    file_name: str = "event-10.jpg",
) -> FakeSnapshot:
    return FakeSnapshot(
        id=snapshot_id,
        event_id=event_id,
        camera_id="gate_01",
        file_path=f"data/snapshots/gate_01/{file_name}",
        file_name=file_name,
        width=1280,
        height=720,
        mime_type="image/jpeg",
        captured_at=datetime(2026, 6, 22, 10, 30, tzinfo=timezone.utc),
        created_at=datetime(2026, 6, 22, 10, 31, tzinfo=timezone.utc),
    )


def make_client(repository: FakeSnapshotRepository) -> TestClient:
    app.dependency_overrides[get_snapshot_repository] = lambda: repository
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)


def test_get_snapshot_returns_snapshot() -> None:
    repository = FakeSnapshotRepository([make_snapshot()])
    client = make_client(repository)

    response = client.get("/snapshots/1")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "event_id": 10,
        "camera_id": "gate_01",
        "file_path": "data/snapshots/gate_01/event-10.jpg",
        "file_name": "event-10.jpg",
        "width": 1280,
        "height": 720,
        "mime_type": "image/jpeg",
        "captured_at": "2026-06-22T10:30:00Z",
        "created_at": "2026-06-22T10:31:00Z",
    }


def test_list_event_snapshots_returns_paginated_snapshots() -> None:
    repository = FakeSnapshotRepository(
        [
            make_snapshot(snapshot_id=1, event_id=10, file_name="first.jpg"),
            make_snapshot(snapshot_id=2, event_id=10, file_name="second.jpg"),
            make_snapshot(snapshot_id=3, event_id=11, file_name="other.jpg"),
        ]
    )
    client = make_client(repository)

    response = client.get("/events/10/snapshots?limit=1&page=2")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 2,
                "event_id": 10,
                "camera_id": "gate_01",
                "file_path": "data/snapshots/gate_01/second.jpg",
                "file_name": "second.jpg",
                "width": 1280,
                "height": 720,
                "mime_type": "image/jpeg",
                "captured_at": "2026-06-22T10:30:00Z",
                "created_at": "2026-06-22T10:31:00Z",
            }
        ],
        "page": 2,
        "limit": 1,
        "total": 2,
        "total_pages": 2,
    }
    assert repository.list_by_event_calls == [(10, 2, 1)]


def test_get_snapshot_returns_404_for_missing_snapshot() -> None:
    repository = FakeSnapshotRepository([])
    client = make_client(repository)

    response = client.get("/snapshots/404")

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json() == {"detail": "Snapshot not found"}
