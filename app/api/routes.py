from datetime import datetime
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.cameras import (
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraUpdate,
)
from app.core.security import require_api_key
from app.schemas.event_types import (
    EventTypeCreate,
    EventTypeListResponse,
    EventTypeResponse,
    EventTypeUpdate,
)
from app.schemas.events import EventListResponse, EventResponse, EventStatsResponse
from app.schemas.health import CameraHealthResponse
from app.schemas.snapshots import SnapshotListResponse, SnapshotResponse
from app.services.camera_health import camera_health_registry

router = APIRouter()


class EventReader(Protocol):
    def list_events(
        self,
        page: int = 1,
        limit: int = 100,
        camera_id: str | None = None,
        event_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, object]:
        ...

    def list_recent(
        self,
        limit: int = 100,
        camera_id: str | None = None,
    ) -> list[object]:
        ...

    def get(self, event_id: int) -> object | None:
        ...

    def stats(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        camera_id: str | None = None,
        event_type: str | None = None,
        rule_name: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        ...


class CameraReaderWriter(Protocol):
    def create(self, camera: CameraCreate) -> object:
        ...

    def list_cameras(
        self,
        page: int = 1,
        limit: int = 100,
        status: str | None = None,
        source_type: str | None = None,
    ) -> dict[str, object]:
        ...

    def get_by_id(self, camera_id: int) -> object | None:
        ...

    def update(self, camera_id: int, camera: CameraUpdate) -> object | None:
        ...

    def deactivate(self, camera_id: int) -> object | None:
        ...


class EventTypeReaderWriter(Protocol):
    def create(self, event_type: EventTypeCreate) -> object:
        ...

    def list_event_types(
        self,
        page: int = 1,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> dict[str, object]:
        ...

    def get_by_id(self, event_type_id: int) -> object | None:
        ...

    def get_by_key(self, key: str) -> object | None:
        ...

    def update(
        self,
        event_type_id: int,
        event_type: EventTypeUpdate,
    ) -> object | None:
        ...

    def deactivate(self, event_type_id: int) -> object | None:
        ...


class SnapshotReaderWriter(Protocol):
    def create(self, snapshot: object) -> object:
        ...

    def list_by_event(
        self,
        event_id: int,
        page: int = 1,
        limit: int = 100,
    ) -> dict[str, object]:
        ...

    def get_by_id(self, snapshot_id: int) -> object | None:
        ...


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a simple service health response."""
    return {"status": "ok"}


@router.get("/health/db", tags=["health"], dependencies=[Depends(require_api_key)])
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


def get_camera_repository() -> CameraReaderWriter:
    from app.repositories.camera_repository import CameraRepository

    return CameraRepository()


def get_event_type_repository() -> EventTypeReaderWriter:
    from app.repositories.event_type_repository import EventTypeRepository

    return EventTypeRepository()


def get_snapshot_repository() -> SnapshotReaderWriter:
    from app.repositories.snapshot_repository import SnapshotRepository

    return SnapshotRepository()


@router.get(
    "/event-types",
    response_model=EventTypeListResponse,
    tags=["event-types"],
    dependencies=[Depends(require_api_key)],
)
async def list_event_types(
    repository: Annotated[EventTypeReaderWriter, Depends(get_event_type_repository)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    is_active: bool | None = None,
) -> dict[str, object]:
    """Return paginated managed AI vision event types."""
    result = repository.list_event_types(
        page=page,
        limit=limit,
        is_active=is_active,
    )
    total = int(result["total"])
    return {
        "items": result["items"],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


@router.post(
    "/event-types",
    response_model=EventTypeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["event-types"],
    dependencies=[Depends(require_api_key)],
)
async def create_event_type(
    event_type: EventTypeCreate,
    repository: Annotated[EventTypeReaderWriter, Depends(get_event_type_repository)],
) -> object:
    """Create managed AI vision event type metadata."""
    if repository.get_by_key(event_type.key) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event type key already exists",
        )
    return repository.create(event_type)


@router.get(
    "/event-types/{event_type_id}",
    response_model=EventTypeResponse,
    tags=["event-types"],
    dependencies=[Depends(require_api_key)],
)
async def get_event_type(
    event_type_id: int,
    repository: Annotated[EventTypeReaderWriter, Depends(get_event_type_repository)],
) -> object:
    """Return one managed AI vision event type by id."""
    event_type = repository.get_by_id(event_type_id)
    if event_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event type not found",
        )
    return event_type


@router.patch(
    "/event-types/{event_type_id}",
    response_model=EventTypeResponse,
    tags=["event-types"],
    dependencies=[Depends(require_api_key)],
)
async def update_event_type(
    event_type_id: int,
    event_type: EventTypeUpdate,
    repository: Annotated[EventTypeReaderWriter, Depends(get_event_type_repository)],
) -> object:
    """Update managed AI vision event type metadata."""
    if event_type.key is not None:
        existing = repository.get_by_key(event_type.key)
        if existing is not None and getattr(existing, "id", None) != event_type_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event type key already exists",
            )

    updated = repository.update(event_type_id, event_type)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event type not found",
        )
    return updated


@router.delete(
    "/event-types/{event_type_id}",
    response_model=EventTypeResponse,
    tags=["event-types"],
    dependencies=[Depends(require_api_key)],
)
async def deactivate_event_type(
    event_type_id: int,
    repository: Annotated[EventTypeReaderWriter, Depends(get_event_type_repository)],
) -> object:
    """Mark managed AI vision event type metadata inactive."""
    event_type = repository.deactivate(event_type_id)
    if event_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event type not found",
        )
    return event_type


@router.get(
    "/events/stats",
    response_model=EventStatsResponse,
    tags=["events"],
    dependencies=[Depends(require_api_key)],
)
async def event_stats(
    repository: Annotated[EventReader, Depends(get_event_repository)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    camera_id: str | None = None,
    event_type: str | None = None,
    rule_name: str | None = None,
    severity: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    """Return aggregate event statistics for dashboard views."""
    return repository.stats(
        start_at=date_from if date_from is not None else start_at,
        end_at=date_to if date_to is not None else end_at,
        camera_id=camera_id,
        event_type=event_type,
        rule_name=rule_name,
        severity=severity,
        status=status,
    )


@router.get(
    "/cameras/health",
    response_model=list[CameraHealthResponse],
    tags=["cameras"],
    dependencies=[Depends(require_api_key)],
)
async def camera_health() -> list[object]:
    """Return runtime-only per-camera health state."""
    return camera_health_registry.list_health()


@router.get(
    "/cameras",
    response_model=CameraListResponse,
    tags=["cameras"],
    dependencies=[Depends(require_api_key)],
)
async def list_cameras(
    repository: Annotated[CameraReaderWriter, Depends(get_camera_repository)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    status: str | None = None,
    source_type: str | None = None,
) -> dict[str, object]:
    """Return paginated managed cameras and media sources."""
    result = repository.list_cameras(
        page=page,
        limit=limit,
        status=status,
        source_type=source_type,
    )
    total = int(result["total"])
    return {
        "items": result["items"],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


@router.post(
    "/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["cameras"],
    dependencies=[Depends(require_api_key)],
)
async def create_camera(
    camera: CameraCreate,
    repository: Annotated[CameraReaderWriter, Depends(get_camera_repository)],
) -> object:
    """Create a managed camera or media source."""
    return repository.create(camera)


@router.get(
    "/cameras/{camera_id}",
    response_model=CameraResponse,
    tags=["cameras"],
    dependencies=[Depends(require_api_key)],
)
async def get_camera(
    camera_id: int,
    repository: Annotated[CameraReaderWriter, Depends(get_camera_repository)],
) -> object:
    """Return one managed camera or media source by id."""
    camera = repository.get_by_id(camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    return camera


@router.patch(
    "/cameras/{camera_id}",
    response_model=CameraResponse,
    tags=["cameras"],
    dependencies=[Depends(require_api_key)],
)
async def update_camera(
    camera_id: int,
    camera: CameraUpdate,
    repository: Annotated[CameraReaderWriter, Depends(get_camera_repository)],
) -> object:
    """Update one managed camera or media source."""
    updated = repository.update(camera_id, camera)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    return updated


@router.delete(
    "/cameras/{camera_id}",
    response_model=CameraResponse,
    tags=["cameras"],
    dependencies=[Depends(require_api_key)],
)
async def deactivate_camera(
    camera_id: int,
    repository: Annotated[CameraReaderWriter, Depends(get_camera_repository)],
) -> object:
    """Mark a managed camera or media source inactive."""
    camera = repository.deactivate(camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    return camera


@router.get(
    "/events",
    response_model=EventListResponse,
    response_model_exclude_none=True,
    tags=["events"],
    dependencies=[Depends(require_api_key)],
)
async def list_events(
    repository: Annotated[EventReader, Depends(get_event_repository)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    camera_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, object]:
    """Return paginated events ordered by creation time."""
    result = repository.list_events(
        page=page,
        limit=limit,
        camera_id=camera_id,
        event_type=event_type,
        severity=severity,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    total = int(result["total"])
    return {
        "items": result["items"],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }


@router.get(
    "/events/latest",
    response_model=list[EventResponse],
    response_model_exclude_none=True,
    tags=["events"],
    dependencies=[Depends(require_api_key)],
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
    dependencies=[Depends(require_api_key)],
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


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
    response_model_exclude_none=True,
    tags=["snapshots"],
    dependencies=[Depends(require_api_key)],
)
async def get_snapshot(
    snapshot_id: int,
    repository: Annotated[SnapshotReaderWriter, Depends(get_snapshot_repository)],
) -> object:
    """Return one event snapshot by id."""
    snapshot = repository.get_by_id(snapshot_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )
    return snapshot


@router.get(
    "/events/{event_id}/snapshots",
    response_model=SnapshotListResponse,
    response_model_exclude_none=True,
    tags=["snapshots"],
    dependencies=[Depends(require_api_key)],
)
async def list_event_snapshots(
    event_id: int,
    repository: Annotated[SnapshotReaderWriter, Depends(get_snapshot_repository)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, object]:
    """Return paginated snapshots for one event."""
    result = repository.list_by_event(
        event_id=event_id,
        page=page,
        limit=limit,
    )
    total = int(result["total"])
    return {
        "items": result["items"],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
    }
