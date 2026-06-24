from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.database.urls import normalize_database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        normalize_database_url(get_settings().database.url),
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def create_session_factory(settings: Settings) -> sessionmaker[Session]:
    engine = create_engine(
        normalize_database_url(settings.database.url),
        pool_pre_ping=True,
    )
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Generator[Session, None, None]:
    with get_session_factory() as session:
        yield session
