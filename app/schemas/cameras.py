from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


class CameraSourceType(str, Enum):
    image = "image"
    video = "video"
    camera = "camera"
    rtsp = "rtsp"
    webcam = "webcam"


class CameraStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class CameraCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    source_type: CameraSourceType
    source_uri: str = Field(..., min_length=1, max_length=500)
    location: str | None = Field(default=None, max_length=255)
    status: CameraStatus = CameraStatus.active
    last_seen_at: datetime | None = None


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    source_type: CameraSourceType | None = None
    source_uri: str | None = Field(default=None, min_length=1, max_length=500)
    location: str | None = Field(default=None, max_length=255)
    status: CameraStatus | None = None
    last_seen_at: datetime | None = None


if ConfigDict is not None:

    class CameraResponse(BaseModel):
        id: int
        name: str
        source_type: CameraSourceType
        source_uri: str
        location: str | None = None
        status: CameraStatus
        last_seen_at: datetime | None = None
        created_at: datetime
        updated_at: datetime

        model_config = ConfigDict(from_attributes=True)

else:

    class CameraResponse(BaseModel):
        id: int
        name: str
        source_type: CameraSourceType
        source_uri: str
        location: str | None = None
        status: CameraStatus
        last_seen_at: datetime | None = None
        created_at: datetime
        updated_at: datetime

        class Config:
            orm_mode = True


class CameraListResponse(BaseModel):
    items: list[CameraResponse]
    page: int
    limit: int
    total: int
    total_pages: int
