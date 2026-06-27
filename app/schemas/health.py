from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class CameraHealthResponse(BaseModel):
    camera_id: str
    source: str | None = None
    status: str
    last_frame_at: datetime | None = None
    last_event_at: datetime | None = None
    processed_frame_count: int
    emitted_event_count: int
    last_error: str | None = None
