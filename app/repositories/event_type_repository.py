from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import EventType as EventTypeModel
from app.database.session import get_session_factory
from app.schemas.event_types import EventTypeCreate, EventTypeUpdate


class EventTypeRepository:
    """Persist managed AI vision event type metadata."""

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

    def create(
        self,
        event_type: EventTypeCreate | Mapping[str, object],
    ) -> EventTypeModel:
        values = _schema_values(event_type, exclude_unset=False)
        model = EventTypeModel(**values)

        if self._session is not None:
            self._session.add(model)
            self._session.commit()
            self._session.refresh(model)
            return model

        if self._session_factory is None:
            raise RuntimeError("EventTypeRepository requires a session or session factory")

        with self._session_factory() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def list_event_types(
        self,
        page: int = 1,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> dict[str, object]:
        base_statement = _apply_event_type_filters(
            select(EventTypeModel),
            is_active=is_active,
        )
        count_statement = _apply_event_type_filters(
            select(func.count()).select_from(EventTypeModel),
            is_active=is_active,
        )
        offset = (page - 1) * limit
        page_statement = (
            base_statement.order_by(EventTypeModel.key.asc())
            .offset(offset)
            .limit(limit)
        )

        if self._session is not None:
            total = int(self._session.scalar(count_statement) or 0)
            items = list(self._session.scalars(page_statement).all())
            return {"items": items, "total": total}

        if self._session_factory is None:
            raise RuntimeError("EventTypeRepository requires a session or session factory")

        with self._session_factory() as session:
            total = int(session.scalar(count_statement) or 0)
            items = list(session.scalars(page_statement).all())
            return {"items": items, "total": total}

    def get_by_id(self, event_type_id: int) -> EventTypeModel | None:
        if self._session is not None:
            return self._session.get(EventTypeModel, event_type_id)

        if self._session_factory is None:
            raise RuntimeError("EventTypeRepository requires a session or session factory")

        with self._session_factory() as session:
            return session.get(EventTypeModel, event_type_id)

    def get_by_key(self, key: str) -> EventTypeModel | None:
        statement = select(EventTypeModel).where(EventTypeModel.key == key)

        if self._session is not None:
            return self._session.scalars(statement).first()

        if self._session_factory is None:
            raise RuntimeError("EventTypeRepository requires a session or session factory")

        with self._session_factory() as session:
            return session.scalars(statement).first()

    def update(
        self,
        event_type_id: int,
        event_type: EventTypeUpdate | Mapping[str, object],
    ) -> EventTypeModel | None:
        values = _schema_values(event_type, exclude_unset=True)

        if self._session is not None:
            model = self._session.get(EventTypeModel, event_type_id)
            if model is None:
                return None
            _apply_values(model, values)
            self._session.commit()
            self._session.refresh(model)
            return model

        if self._session_factory is None:
            raise RuntimeError("EventTypeRepository requires a session or session factory")

        with self._session_factory() as session:
            model = session.get(EventTypeModel, event_type_id)
            if model is None:
                return None
            _apply_values(model, values)
            session.commit()
            session.refresh(model)
            return model

    def deactivate(self, event_type_id: int) -> EventTypeModel | None:
        return self.update(event_type_id, {"is_active": False})


def _schema_values(
    schema: EventTypeCreate | EventTypeUpdate | Mapping[str, object],
    exclude_unset: bool,
) -> dict[str, object]:
    if isinstance(schema, Mapping):
        return dict(schema)

    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_unset=exclude_unset)

    return schema.dict(exclude_unset=exclude_unset)


def _apply_values(model: EventTypeModel, values: Mapping[str, object]) -> None:
    for field_name, value in values.items():
        setattr(model, field_name, value)


def _apply_event_type_filters(
    statement: object,
    is_active: bool | None = None,
) -> object:
    if is_active is not None:
        statement = statement.where(EventTypeModel.is_active == is_active)
    return statement
