from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:
    ConfigDict = None


class EventTypeSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class EventTypeCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    default_severity: EventTypeSeverity = EventTypeSeverity.info
    is_active: bool = True


class EventTypeUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    default_severity: EventTypeSeverity | None = None
    is_active: bool | None = None


if ConfigDict is not None:

    class EventTypeResponse(BaseModel):
        id: int
        key: str
        name: str
        description: str | None = None
        default_severity: EventTypeSeverity
        is_active: bool
        created_at: datetime
        updated_at: datetime

        model_config = ConfigDict(from_attributes=True)

else:

    class EventTypeResponse(BaseModel):
        id: int
        key: str
        name: str
        description: str | None = None
        default_severity: EventTypeSeverity
        is_active: bool
        created_at: datetime
        updated_at: datetime

        class Config:
            orm_mode = True


class EventTypeListResponse(BaseModel):
    items: list[EventTypeResponse]
    page: int
    limit: int
    total: int
    total_pages: int
