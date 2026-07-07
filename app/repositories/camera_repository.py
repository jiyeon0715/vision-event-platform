from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import Camera as CameraModel
from app.database.session import get_session_factory
from app.schemas.cameras import CameraCreate, CameraUpdate


class CameraRepository:
    """Persist managed cameras and media sources."""

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

    def create(self, camera: CameraCreate | Mapping[str, object]) -> CameraModel:
        values = _schema_values(camera, exclude_unset=False)
        model = CameraModel(**values)

        if self._session is not None:
            self._session.add(model)
            self._session.commit()
            self._session.refresh(model)
            return model

        if self._session_factory is None:
            raise RuntimeError("CameraRepository requires a session or session factory")

        with self._session_factory() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def list_cameras(
        self,
        page: int = 1,
        limit: int = 100,
        status: str | None = None,
        source_type: str | None = None,
    ) -> dict[str, object]:
        base_statement = _apply_camera_filters(
            select(CameraModel),
            status=status,
            source_type=source_type,
        )
        count_statement = _apply_camera_filters(
            select(func.count()).select_from(CameraModel),
            status=status,
            source_type=source_type,
        )
        offset = (page - 1) * limit
        page_statement = (
            base_statement.order_by(CameraModel.created_at.desc(), CameraModel.id.desc())
            .offset(offset)
            .limit(limit)
        )

        if self._session is not None:
            total = int(self._session.scalar(count_statement) or 0)
            items = list(self._session.scalars(page_statement).all())
            return {"items": items, "total": total}

        if self._session_factory is None:
            raise RuntimeError("CameraRepository requires a session or session factory")

        with self._session_factory() as session:
            total = int(session.scalar(count_statement) or 0)
            items = list(session.scalars(page_statement).all())
            return {"items": items, "total": total}

    def get_by_id(self, camera_id: int) -> CameraModel | None:
        if self._session is not None:
            return self._session.get(CameraModel, camera_id)

        if self._session_factory is None:
            raise RuntimeError("CameraRepository requires a session or session factory")

        with self._session_factory() as session:
            return session.get(CameraModel, camera_id)

    def update(
        self,
        camera_id: int,
        camera: CameraUpdate | Mapping[str, object],
    ) -> CameraModel | None:
        values = _schema_values(camera, exclude_unset=True)

        if self._session is not None:
            model = self._session.get(CameraModel, camera_id)
            if model is None:
                return None
            _apply_values(model, values)
            self._session.commit()
            self._session.refresh(model)
            return model

        if self._session_factory is None:
            raise RuntimeError("CameraRepository requires a session or session factory")

        with self._session_factory() as session:
            model = session.get(CameraModel, camera_id)
            if model is None:
                return None
            _apply_values(model, values)
            session.commit()
            session.refresh(model)
            return model

    def deactivate(self, camera_id: int) -> CameraModel | None:
        return self.update(camera_id, {"status": "inactive"})

    def delete(self, camera_id: int) -> CameraModel | None:
        return self.deactivate(camera_id)


def _schema_values(
    schema: CameraCreate | CameraUpdate | Mapping[str, object],
    exclude_unset: bool,
) -> dict[str, object]:
    if isinstance(schema, Mapping):
        return dict(schema)

    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_unset=exclude_unset)

    return schema.dict(exclude_unset=exclude_unset)


def _apply_values(model: CameraModel, values: Mapping[str, object]) -> None:
    for field_name, value in values.items():
        setattr(model, field_name, value)


def _apply_camera_filters(
    statement: object,
    status: str | None = None,
    source_type: str | None = None,
) -> object:
    if status is not None:
        statement = statement.where(CameraModel.status == status)
    if source_type is not None:
        statement = statement.where(CameraModel.source_type == source_type)
    return statement
