from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from storage.event_repository import EventRepository


def make_event(
    event_type: str = "danger_zone",
    track_id: int = 42,
    camera_id: str = "camera-1",
) -> dict:
    return {
        "event_type": event_type,
        "camera_id": camera_id,
        "track_id": track_id,
        "timestamp": 123.45 + track_id,
        "message": f"Track {track_id} emitted {event_type}.",
        "metadata": {"zone": "loading-dock"},
    }


def make_client(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    db_path = tmp_path / "events.db"
    snapshot_dir = tmp_path / "snapshots"
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("PROTECT_DASHBOARD", raising=False)
    monkeypatch.setenv("EVENT_DB_PATH", str(db_path))
    monkeypatch.setenv("SNAPSHOT_DIR", str(snapshot_dir))
    return TestClient(app), str(db_path)


def test_health_returns_status_and_db_path(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "db_path": db_path,
    }


def test_database_health_requires_api_key_when_configured(
    tmp_path,
    monkeypatch,
) -> None:
    client, _ = make_client(tmp_path, monkeypatch)
    monkeypatch.setenv("API_KEY", "secret-key")

    response = client.get("/health/db")
    authorized_response = client.get(
        "/health/db",
        headers={"X-API-Key": "secret-key"},
    )

    assert response.status_code == 401
    assert authorized_response.status_code == 200
    assert authorized_response.json()["status"] == "ok"


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


def test_list_events_supports_camera_id_filter(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(track_id=1, camera_id="gate_01"))
    repository.save(make_event(track_id=2, camera_id="gate_02"))
    repository.save(make_event(track_id=3, camera_id="gate_01"))

    response = client.get("/events?camera_id=gate_01")

    assert response.status_code == 200
    assert [event["track_id"] for event in response.json()] == [1, 3]
    assert {event["camera_id"] for event in response.json()} == {"gate_01"}


def test_latest_events_returns_newest_events_first(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(track_id=1))
    repository.save(make_event(track_id=2))
    repository.save(make_event(track_id=3))

    response = client.get("/events/latest?limit=2")

    assert response.status_code == 200
    assert [event["track_id"] for event in response.json()] == [3, 2]


def test_latest_events_supports_camera_id_filter(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(track_id=1, camera_id="gate_01"))
    repository.save(make_event(track_id=2, camera_id="gate_02"))
    repository.save(make_event(track_id=3, camera_id="gate_01"))

    response = client.get("/events/latest?camera_id=gate_01&limit=5")

    assert response.status_code == 200
    assert [event["track_id"] for event in response.json()] == [3, 1]


def test_stats_returns_total_and_counts_by_type(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone"))
    repository.save(make_event(event_type="danger_zone"))
    repository.save(make_event(event_type="line_crossing"))

    response = client.get("/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_event_count"] == 3
    assert payload["event_count_by_rule_name"] == {
        "danger_zone": 2,
        "line_crossing": 1,
    }
    assert payload["event_count_by_camera_id"] == {"camera-1": 3}
    assert payload["latest_event_timestamp"] is not None


def test_event_stats_supports_camera_and_rule_filters(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone", track_id=1, camera_id="gate_01"))
    repository.save(make_event(event_type="danger_zone", track_id=2, camera_id="gate_02"))
    repository.save(make_event(event_type="loitering", track_id=3, camera_id="gate_01"))

    response = client.get("/events/stats?camera_id=gate_01&rule_name=loitering")

    assert response.status_code == 200
    assert response.json()["total_event_count"] == 1
    assert response.json()["event_count_by_rule_name"] == {"loitering": 1}
    assert response.json()["event_count_by_camera_id"] == {"gate_01": 1}


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
    assert "Today total events" in response.text
    assert "<p class=\"value\">2</p>" in response.text
    assert "Events By Rule" in response.text
    assert "Events By Camera" in response.text
    assert "Camera Health" in response.text
    assert "danger_zone" in response.text
    assert "line_crossing" in response.text
    assert "camera-1" in response.text
    assert 'name="camera_id"' in response.text
    assert "track_id" in response.text
    assert db_path in response.text


def test_dashboard_supports_camera_id_filter(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    repository = EventRepository(db_path)
    repository.save(make_event(track_id=1, camera_id="gate_01"))
    repository.save(make_event(track_id=2, camera_id="gate_02"))

    response = client.get("/dashboard?camera_id=gate_02")

    assert response.status_code == 200
    assert "gate_02" in response.text
    assert "gate_01" not in response.text


def test_dashboard_renders_snapshot_thumbnail(tmp_path, monkeypatch) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    snapshot_dir = tmp_path / "snapshots"
    camera_snapshot_dir = snapshot_dir / "gate_01"
    camera_snapshot_dir.mkdir(parents=True)
    (camera_snapshot_dir / "event-1.jpg").write_bytes(b"jpeg bytes")
    repository = EventRepository(db_path)
    event = make_event(event_type="danger_zone", track_id=1, camera_id="gate_01")
    event["snapshot_path"] = str(camera_snapshot_dir / "event-1.jpg")
    repository.save(event)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "<th>Snapshot</th>" in response.text
    assert 'href="/snapshots/gate_01/event-1.jpg"' in response.text
    assert 'src="/snapshots/gate_01/event-1.jpg"' in response.text
    assert 'class="snapshot-thumb"' in response.text


def test_snapshot_endpoint_serves_file_and_missing_returns_404(
    tmp_path,
    monkeypatch,
) -> None:
    client, _ = make_client(tmp_path, monkeypatch)
    snapshot_dir = tmp_path / "snapshots"
    camera_snapshot_dir = snapshot_dir / "gate_01"
    camera_snapshot_dir.mkdir(parents=True)
    (camera_snapshot_dir / "event-1.jpg").write_bytes(b"jpeg bytes")

    response = client.get("/snapshots/gate_01/event-1.jpg")
    missing_response = client.get("/snapshots/missing.jpg")

    assert response.status_code == 200
    assert response.content == b"jpeg bytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert missing_response.status_code == 404


def test_snapshot_endpoint_requires_api_key_when_configured(
    tmp_path,
    monkeypatch,
) -> None:
    client, _ = make_client(tmp_path, monkeypatch)
    snapshot_dir = tmp_path / "snapshots"
    camera_snapshot_dir = snapshot_dir / "gate_01"
    camera_snapshot_dir.mkdir(parents=True)
    (camera_snapshot_dir / "event-1.jpg").write_bytes(b"jpeg bytes")
    monkeypatch.setenv("API_KEY", "secret-key")

    response = client.get("/snapshots/gate_01/event-1.jpg")
    authorized_response = client.get(
        "/snapshots/gate_01/event-1.jpg",
        headers={"X-API-Key": "secret-key"},
    )

    assert response.status_code == 401
    assert authorized_response.status_code == 200
    assert authorized_response.content == b"jpeg bytes"


def test_snapshot_endpoint_blocks_path_traversal(tmp_path, monkeypatch) -> None:
    client, _ = make_client(tmp_path, monkeypatch)
    outside_file = tmp_path / "outside.jpg"
    outside_file.write_bytes(b"outside")

    response = client.get("/snapshots/%2E%2E/outside.jpg")

    assert response.status_code == 404


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


def test_dashboard_remains_public_by_default_with_api_key(
    tmp_path,
    monkeypatch,
) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    monkeypatch.setenv("API_KEY", "secret-key")
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone", track_id=8))

    root_response = client.get("/")
    dashboard_response = client.get("/dashboard")

    assert root_response.status_code == 200
    assert dashboard_response.status_code == 200
    assert "Vision Events Dashboard" in root_response.text
    assert "Vision Events Dashboard" in dashboard_response.text


def test_dashboard_can_require_api_key(
    tmp_path,
    monkeypatch,
) -> None:
    client, db_path = make_client(tmp_path, monkeypatch)
    monkeypatch.setenv("API_KEY", "secret-key")
    monkeypatch.setenv("PROTECT_DASHBOARD", "true")
    repository = EventRepository(db_path)
    repository.save(make_event(event_type="danger_zone", track_id=9))

    root_response = client.get("/")
    dashboard_response = client.get("/dashboard")
    authorized_response = client.get(
        "/dashboard",
        headers={"X-API-Key": "secret-key"},
    )

    assert root_response.status_code == 401
    assert dashboard_response.status_code == 401
    assert authorized_response.status_code == 200
    assert "Vision Events Dashboard" in authorized_response.text
