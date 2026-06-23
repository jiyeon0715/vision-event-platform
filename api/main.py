from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Query

from storage.event_repository import EventRepository

DEFAULT_DB_PATH = Path("data/events.db")

app = FastAPI(title="Vision Events API")


def get_db_path() -> Path:
    return Path(os.environ.get("EVENT_DB_PATH", DEFAULT_DB_PATH))


def get_event_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> EventRepository:
    return EventRepository(db_path)


@app.get("/health")
def health(db_path: Annotated[Path, Depends(get_db_path)]) -> dict[str, str]:
    return {
        "status": "ok",
        "db_path": str(db_path),
    }


@app.get("/events")
def list_events(
    repository: Annotated[EventRepository, Depends(get_event_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    event_type: str | None = None,
) -> list[dict]:
    events = repository.list_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
    )
    return [_format_event(event) for event in events]


@app.get("/events/latest")
def latest_events(
    repository: Annotated[EventRepository, Depends(get_event_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 10,
) -> list[dict]:
    events = repository.list_latest_events(limit=limit)
    return [_format_event(event) for event in events]


@app.get("/stats")
def stats(
    repository: Annotated[EventRepository, Depends(get_event_repository)],
) -> dict:
    return {
        "total_event_count": repository.count_events(),
        "event_count_by_type": repository.count_events_by_type(),
    }


def _format_event(event: dict) -> dict:
    readable_event = {
        "id": event["id"],
        "event_type": event["event_type"],
        "camera_id": event["camera_id"],
        "track_id": event["track_id"],
        "timestamp": event["timestamp"],
        "created_at": event["created_at"],
        "payload": _parse_payload(event["payload_json"]),
    }
    return readable_event


def _parse_payload(payload_json: str) -> dict:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return {"raw": payload_json}

    if isinstance(payload, dict):
        return payload

    return {"value": payload}
