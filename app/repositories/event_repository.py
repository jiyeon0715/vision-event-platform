from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import Event as EventModel
from app.database.session import get_session_factory


class EventRecord(Protocol):
    event_type: str
    camera_id: str
    track_id: int
    timestamp: float
    message: str


class EventRepository:
    """Persist generated pipeline events."""

    def __init__(
        self,
        session: Session | None = None,
        session_factory: sessionmaker[Session] | None = None,
    ) -> None:
        self._session = session
        self._session_factory = (
            session_factory
            if session_factory is not None
            else None
            if session is not None
            else get_session_factory()
        )

    def save(self, event: EventRecord) -> EventModel:
        return self.save_many([event])[0]

    def list_recent(
        self,
        limit: int = 100,
        camera_id: str | None = None,
    ) -> list[EventModel]:
        statement = select(EventModel).order_by(EventModel.created_at.desc()).limit(limit)
        if camera_id is not None:
            statement = statement.where(EventModel.camera_id == camera_id)

        if self._session is not None:
            return list(self._session.scalars(statement).all())

        if self._session_factory is None:
            raise RuntimeError("EventRepository requires a session or session factory")

        with self._session_factory() as session:
            return list(session.scalars(statement).all())

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
        base_statement = _apply_event_filters(
            select(EventModel),
            camera_id=camera_id,
            event_type=event_type,
            severity=severity,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        count_statement = _apply_event_filters(
            select(func.count()).select_from(EventModel),
            camera_id=camera_id,
            event_type=event_type,
            severity=severity,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        offset = (page - 1) * limit
        page_statement = (
            base_statement.order_by(EventModel.created_at.desc(), EventModel.id.desc())
            .offset(offset)
            .limit(limit)
        )

        if self._session is not None:
            total = int(self._session.scalar(count_statement) or 0)
            items = list(self._session.scalars(page_statement).all())
            return {"items": items, "total": total}

        if self._session_factory is None:
            raise RuntimeError("EventRepository requires a session or session factory")

        with self._session_factory() as session:
            total = int(session.scalar(count_statement) or 0)
            items = list(session.scalars(page_statement).all())
            return {"items": items, "total": total}

    def get(self, event_id: int) -> EventModel | None:
        if self._session is not None:
            return self._session.get(EventModel, event_id)

        if self._session_factory is None:
            raise RuntimeError("EventRepository requires a session or session factory")

        with self._session_factory() as session:
            return session.get(EventModel, event_id)

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
        event_type_filter = event_type if event_type is not None else rule_name
        statement = _apply_event_filters(
            select(EventModel),
            camera_id=camera_id,
            event_type=event_type_filter,
            severity=severity,
            status=status,
            date_from=start_at,
            date_to=end_at,
        )

        events = self._list_for_statement(statement)
        type_counts = Counter(event.event_type or "unknown" for event in events)
        camera_counts = Counter(event.camera_id or "unknown" for event in events)
        status_counts = Counter(event.status or "unknown" for event in events)
        hourly_counts = Counter(_hour_bucket(event.created_at) for event in events)
        latest_event_timestamp = max(
            (event.created_at for event in events),
            default=None,
        )

        return {
            "total_event_count": len(events),
            "event_count_by_type": dict(sorted(type_counts.items())),
            "event_count_by_rule_name": dict(sorted(type_counts.items())),
            "event_count_by_camera_id": dict(sorted(camera_counts.items())),
            "event_count_by_status": dict(sorted(status_counts.items())),
            "hourly_event_counts": dict(sorted(hourly_counts.items())),
            "latest_event_timestamp": latest_event_timestamp,
        }

    def save_many(self, events: Iterable[EventRecord]) -> list[EventModel]:
        event_list = list(events)
        if not event_list:
            return []

        models = [
            EventModel(
                event_type=_event_field(event, "event_type"),
                camera_id=_event_field(event, "camera_id", "default"),
                track_id=_event_field(event, "track_id"),
                timestamp=_event_field(event, "timestamp"),
                message=_event_field(event, "message"),
                severity=_event_field(event, "severity", None),
                status=_event_field(event, "status", None),
                snapshot_path=_event_field(event, "snapshot_path", None),
            )
            for event in event_list
        ]

        if self._session is not None:
            self._session.add_all(models)
            self._session.commit()
            return models

        if self._session_factory is None:
            raise RuntimeError("EventRepository requires a session or session factory")

        with self._session_factory() as session:
            session.add_all(models)
            session.commit()
            for model in models:
                session.refresh(model)
            return models

    def _list_for_statement(self, statement: object) -> list[EventModel]:
        if self._session is not None:
            return list(self._session.scalars(statement).all())

        if self._session_factory is None:
            raise RuntimeError("EventRepository requires a session or session factory")

        with self._session_factory() as session:
            return list(session.scalars(statement).all())


def _event_field(event: EventRecord, field_name: str, default: object = None) -> object:
    if isinstance(event, Mapping):
        return event.get(field_name, default)
    return getattr(event, field_name, default)


def _apply_event_filters(
    statement: object,
    camera_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> object:
    if camera_id is not None:
        statement = statement.where(EventModel.camera_id == camera_id)
    if event_type is not None:
        statement = statement.where(EventModel.event_type == event_type)
    if severity is not None:
        statement = statement.where(EventModel.severity == severity)
    if status is not None:
        statement = statement.where(EventModel.status == status)
    if date_from is not None:
        statement = statement.where(EventModel.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(EventModel.created_at <= date_to)
    return statement


def _hour_bucket(value: datetime) -> str:
    return value.replace(minute=0, second=0, microsecond=0).isoformat()
