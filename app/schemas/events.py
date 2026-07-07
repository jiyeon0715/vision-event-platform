from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


if ConfigDict is not None:

    class EventResponse(BaseModel):
        id: int
        event_type: str
        camera_id: str
        track_id: int
        timestamp: float
        message: str
        severity: str | None = None
        status: str | None = None
        snapshot_path: str | None = None
        created_at: datetime

        model_config = ConfigDict(from_attributes=True)

else:

    class EventResponse(BaseModel):
        id: int
        event_type: str
        camera_id: str
        track_id: int
        timestamp: float
        message: str
        severity: str | None = None
        status: str | None = None
        snapshot_path: str | None = None
        created_at: datetime

        class Config:
            orm_mode = True


class EventListResponse(BaseModel):
    items: list[EventResponse]
    page: int
    limit: int
    total: int
    total_pages: int


class EventStatsResponse(BaseModel):
    total_event_count: int
    event_count_by_type: dict[str, int]
    event_count_by_rule_name: dict[str, int]
    event_count_by_camera_id: dict[str, int]
    event_count_by_status: dict[str, int]
    hourly_event_counts: dict[str, int]
    latest_event_timestamp: datetime | None
