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
        track_id: int
        timestamp: float
        message: str
        created_at: datetime

        model_config = ConfigDict(from_attributes=True)

else:

    class EventResponse(BaseModel):
        id: int
        event_type: str
        track_id: int
        timestamp: float
        message: str
        created_at: datetime

        class Config:
            orm_mode = True
