from __future__ import annotations

import json
import sqlite3

from storage.event_repository import EventRepository


def make_event(track_id: int = 42) -> dict:
    return {
        "event_type": "danger_zone",
        "camera_id": "camera-1",
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


def test_payload_json_is_preserved(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    event = make_event()

    repository.save(event)
    saved_event = repository.list_events()[0]

    assert json.loads(saved_event["payload_json"]) == event
