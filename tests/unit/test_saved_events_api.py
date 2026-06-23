from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from storage.event_repository import EventRepository


def make_event(
    event_type: str = "danger_zone",
    track_id: int = 42,
) -> dict:
    return {
        "event_type": event_type,
        "camera_id": "camera-1",
        "track_id": track_id,
        "timestamp": 123.45 + track_id,
        "message": f"Track {track_id} emitted {event_type}.",
        "metadata": {"zone": "loading-dock"},
    }


def make_client(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    db_path = tmp_path / "events.db"
    monkeypatch.setenv("EVENT_DB_PATH", str(db_path))
    return TestClient(app), str(db_path)


def test_health_returns_status_and_db_path(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "db_path": db_path,
    }


def test_list_events_supports_limit_offset_and_event_type(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone", track_id=1))
    repository.save(make_event(event_type="line_crossing", track_id=2))
    repository.save(make_event(event_type="danger_zone", track_id=3))

    response = client.get("/events?event_type=danger_zone&limit=1&offset=1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 3,
            "event_type": "danger_zone",
            "camera_id": "camera-1",
            "track_id": 3,
            "timestamp": 126.45,
            "created_at": response.json()[0]["created_at"],
            "payload": make_event(event_type="danger_zone", track_id=3),
        }
    ]


def test_latest_events_returns_newest_events_first(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(track_id=1))
    repository.save(make_event(track_id=2))
    repository.save(make_event(track_id=3))

    response = client.get("/events/latest?limit=2")

    assert response.status_code == 200
    assert [event["track_id"] for event in response.json()] == [3, 2]


def test_stats_returns_total_and_counts_by_type(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone"))
    repository.save(make_event(event_type="danger_zone"))
    repository.save(make_event(event_type="line_crossing"))

    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json() == {
        "total_event_count": 3,
        "event_count_by_type": {
            "danger_zone": 2,
            "line_crossing": 1,
        },
    }


def test_dashboard_route_shows_saved_event_summary(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone", track_id=1))
    repository.save(make_event(event_type="line_crossing", track_id=2))

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Vision Events Dashboard" in response.text
    assert "Service status" in response.text
    assert "OK" in response.text
    assert "Total event count" in response.text
    assert "<p class=\"value\">2</p>" in response.text
    assert "danger_zone" in response.text
    assert "line_crossing" in response.text
    assert "camera-1" in response.text
    assert "track_id" in response.text
    assert db_path in response.text


def test_root_route_serves_dashboard(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone", track_id=7))

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Vision Events Dashboard" in response.text
    assert "danger_zone" in response.text
    assert "<td>7</td>" in response.text
