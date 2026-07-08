from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


if ConfigDict is not None:

    class SnapshotResponse(BaseModel):
        id: int
        event_id: int
        camera_id: str
        file_path: str
        file_name: str
        width: int | None = None
        height: int | None = None
        mime_type: str | None = None
        captured_at: datetime
        created_at: datetime

        model_config = ConfigDict(from_attributes=True)

else:

    class SnapshotResponse(BaseModel):
        id: int
        event_id: int
        camera_id: str
        file_path: str
        file_name: str
        width: int | None = None
        height: int | None = None
        mime_type: str | None = None
        captured_at: datetime
        created_at: datetime

        class Config:
            orm_mode = True


class SnapshotListResponse(BaseModel):
    items: list[SnapshotResponse]
    page: int
    limit: int
    total: int
    total_pages: int
