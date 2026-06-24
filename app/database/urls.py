from __future__ import annotations


def normalize_database_url(url: str) -> str:
    """Select the psycopg SQLAlchemy driver for PostgreSQL URLs."""

    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url
