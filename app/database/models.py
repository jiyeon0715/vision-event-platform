from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Event(Base):
    """Persisted event emitted by the vision pipeline."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    camera_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        default="default",
        server_default="default",
    )
    track_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Camera(Base):
    """Managed camera or media source shown in dashboard views."""

    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        default="active",
        server_default="active",
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
