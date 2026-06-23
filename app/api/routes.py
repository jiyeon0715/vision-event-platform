from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.events import EventResponse

router = APIRouter()


class EventReader(Protocol):
    def list_recent(self, limit: int = 100) -> list[object]:
        ...

    def get(self, event_id: int) -> object | None:
        ...


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a simple service health response."""
    return {"status": "ok"}


def get_event_repository() -> EventReader:
    from app.repositories.event_repository import EventRepository

    return EventRepository()


@router.get(
    "/events",
    response_model=list[EventResponse],
    response_model_exclude_none=True,
    tags=["events"],
)
async def list_events(
    repository: Annotated[EventReader, Depends(get_event_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[object]:
    """Return recent events ordered by creation time."""
    return repository.list_recent(limit=limit)


@router.get(
    "/events/{event_id}",
    response_model=EventResponse,
    response_model_exclude_none=True,
    tags=["events"],
)
async def get_event(
    event_id: int,
    repository: Annotated[EventReader, Depends(get_event_repository)],
) -> object:
    """Return one event by id."""
    event = repository.get(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return event
