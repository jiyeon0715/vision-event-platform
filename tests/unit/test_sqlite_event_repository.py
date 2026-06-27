from __future__ import annotations

import json
import sqlite3

from storage.event_repository import EventRepository


def make_event(track_id: int = 42, camera_id: str = "camera-1") -> dict:
    return {
        "event_type": "danger_zone",
        "camera_id": camera_id,
        "track_id": track_id,
        "timestamp": 123.45,
        "message": f"Track {track_id} stayed inside the danger zone.",
        "metadata": {"zone": "loading-dock"},
    }


def test_initialization_creates_events_table(tmp_path) -> None:
    db_path = tmp_path / "events.db"

    EventRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        table_name = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'events'"
        ).fetchone()

    assert table_name == ("events",)


def test_insert_event(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")

    event_id = repository.save(make_event())
    events = repository.list_events()

    assert event_id == 1
    assert len(events) == 1
    assert events[0]["id"] == 1
    assert events[0]["event_type"] == "danger_zone"
    assert events[0]["camera_id"] == "camera-1"
    assert events[0]["track_id"] == 42
    assert events[0]["timestamp"] == 123.45
    assert events[0]["created_at"]


def test_list_events(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    repository.save(make_event(track_id=1))
    repository.save(make_event(track_id=2))

    events = repository.list_events()

    assert [event["track_id"] for event in events] == [1, 2]


def test_list_events_filters_by_camera_id(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    repository.save(make_event(track_id=1, camera_id="gate_01"))
    repository.save(make_event(track_id=2, camera_id="gate_02"))

    events = repository.list_events(camera_id="gate_02")

    assert [event["track_id"] for event in events] == [2]
    assert [event["camera_id"] for event in events] == ["gate_02"]


def test_latest_events_filters_by_camera_id(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    repository.save(make_event(track_id=1, camera_id="gate_01"))
    repository.save(make_event(track_id=2, camera_id="gate_02"))
    repository.save(make_event(track_id=3, camera_id="gate_01"))

    events = repository.list_latest_events(limit=2, camera_id="gate_01")

    assert [event["track_id"] for event in events] == [3, 1]


def test_payload_json_is_preserved(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    event = make_event()

    repository.save(event)
    saved_event = repository.list_events()[0]

    assert json.loads(saved_event["payload_json"]) == event


def test_snapshot_path_is_persisted(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    event = make_event()
    event["snapshot_path"] = "data/snapshots/event-1.jpg"

    repository.save(event)
    saved_event = repository.list_events()[0]

    assert saved_event["snapshot_path"] == "data/snapshots/event-1.jpg"
    assert json.loads(saved_event["payload_json"])["snapshot_path"] == (
        "data/snapshots/event-1.jpg"
    )


def test_stats_aggregates_and_filters_events(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    repository.save(make_event(track_id=1, camera_id="gate_01"))
    repository.save(make_event(track_id=2, camera_id="gate_02"))
    repository.save(
        {
            **make_event(track_id=3, camera_id="gate_01"),
            "event_type": "loitering",
        }
    )

    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            "UPDATE events SET created_at = ? WHERE track_id = ?",
            ("2026-06-22T10:15:00+00:00", 1),
        )
        connection.execute(
            "UPDATE events SET created_at = ? WHERE track_id = ?",
            ("2026-06-22T11:15:00+00:00", 2),
        )
        connection.execute(
            "UPDATE events SET created_at = ? WHERE track_id = ?",
            ("2026-06-22T10:45:00+00:00", 3),
        )
        connection.commit()

    stats = repository.stats(
        start_at="2026-06-22T10:00:00+00:00",
        end_at="2026-06-22T10:59:59+00:00",
        camera_id="gate_01",
    )

    assert stats == {
        "total_event_count": 2,
        "event_count_by_rule_name": {"danger_zone": 1, "loitering": 1},
        "event_count_by_camera_id": {"gate_01": 2},
        "hourly_event_counts": {"2026-06-22T10:00:00+00:00": 2},
        "latest_event_timestamp": "2026-06-22T10:45:00+00:00",
    }


def test_existing_database_adds_snapshot_path_column(tmp_path) -> None:
    db_path = tmp_path / "events.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                camera_id TEXT,
                track_id INTEGER,
                timestamp REAL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()

    repository = EventRepository(db_path)
    repository.save(make_event())
    saved_event = repository.list_events()[0]

    assert "snapshot_path" in saved_event.keys()
    assert saved_event["snapshot_path"] is None
