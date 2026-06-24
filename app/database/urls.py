from __future__ import annotations

from sqlalchemy.engine import make_url


def normalize_database_url(url: str) -> str:
    """Select the psycopg SQLAlchemy driver for PostgreSQL URLs."""

    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def database_backend(url: str) -> str:
    """Return the database backend name without driver details."""

    return make_url(normalize_database_url(url)).get_backend_name()


def redact_database_url(url: str) -> str:
    """Return a database URL suitable for logs."""

    parsed_url = make_url(normalize_database_url(url))
    return parsed_url.render_as_string(hide_password=True)
