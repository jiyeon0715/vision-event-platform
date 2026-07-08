from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import Snapshot as SnapshotModel
from app.database.session import get_session_factory


class SnapshotRepository:
    """Persist and read image snapshots associated with events."""

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

    def create(self, snapshot: Mapping[str, object]) -> SnapshotModel:
        model = SnapshotModel(**dict(snapshot))

        if self._session is not None:
            self._session.add(model)
            self._session.commit()
            self._session.refresh(model)
            return model

        if self._session_factory is None:
            raise RuntimeError("SnapshotRepository requires a session or session factory")

        with self._session_factory() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def list_by_event(
        self,
        event_id: int,
        page: int = 1,
        limit: int = 100,
    ) -> dict[str, object]:
        base_statement = select(SnapshotModel).where(SnapshotModel.event_id == event_id)
        count_statement = (
            select(func.count())
            .select_from(SnapshotModel)
            .where(SnapshotModel.event_id == event_id)
        )
        offset = (page - 1) * limit
        page_statement = (
            base_statement.order_by(
                SnapshotModel.captured_at.desc(),
                SnapshotModel.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        if self._session is not None:
            total = int(self._session.scalar(count_statement) or 0)
            items = list(self._session.scalars(page_statement).all())
            return {"items": items, "total": total}

        if self._session_factory is None:
            raise RuntimeError("SnapshotRepository requires a session or session factory")

        with self._session_factory() as session:
            total = int(session.scalar(count_statement) or 0)
            items = list(session.scalars(page_statement).all())
            return {"items": items, "total": total}

    def get_by_id(self, snapshot_id: int) -> SnapshotModel | None:
        if self._session is not None:
            return self._session.get(SnapshotModel, snapshot_id)

        if self._session_factory is None:
            raise RuntimeError("SnapshotRepository requires a session or session factory")

        with self._session_factory() as session:
            return session.get(SnapshotModel, snapshot_id)
