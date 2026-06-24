from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol

from sqlalchemy import select
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

    def get(self, event_id: int) -> EventModel | None:
        if self._session is not None:
            return self._session.get(EventModel, event_id)

        if self._session_factory is None:
            raise RuntimeError("EventRepository requires a session or session factory")

        with self._session_factory() as session:
            return session.get(EventModel, event_id)

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


def _event_field(event: EventRecord, field_name: str, default: object = None) -> object:
    if isinstance(event, Mapping):
        return event.get(field_name, default)
    return getattr(event, field_name, default)
