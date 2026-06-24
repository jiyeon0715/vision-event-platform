from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.events import EventResponse

router = APIRouter()


class EventReader(Protocol):
    def list_recent(
        self,
        limit: int = 100,
        camera_id: str | None = None,
    ) -> list[object]:
        ...

    def get(self, event_id: int) -> object | None:
        ...


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a simple service health response."""
    return {"status": "ok"}


@router.get("/health/db", tags=["health"])
async def database_health_check() -> dict[str, str]:
    """Return database connectivity status."""
    from app.database.health import check_database_health

    result = check_database_health()
    if result["status"] != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result,
        )
    return result


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
    camera_id: str | None = None,
) -> list[object]:
    """Return recent events ordered by creation time."""
    return repository.list_recent(limit=limit, camera_id=camera_id)


@router.get(
    "/events/latest",
    response_model=list[EventResponse],
    response_model_exclude_none=True,
    tags=["events"],
)
async def list_latest_events(
    repository: Annotated[EventReader, Depends(get_event_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 10,
    camera_id: str | None = None,
) -> list[object]:
    """Return the latest persisted events."""
    return repository.list_recent(limit=limit, camera_id=camera_id)


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
