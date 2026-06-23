from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class EventRepository:
    """Persist vision events to a local SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_table()

    def save(self, event: dict) -> int:
        payload_json = json.dumps(event, sort_keys=True)
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_type,
                    camera_id,
                    track_id,
                    timestamp,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("event_type"),
                    event.get("camera_id"),
                    event.get("track_id"),
                    event.get("timestamp"),
                    payload_json,
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def save_many(self, events: list[dict]) -> list[int]:
        return [self.save(event) for event in events]

    def list_events(self, limit: int | None = None) -> list[dict]:
        query = """
            SELECT
                id,
                event_type,
                camera_id,
                track_id,
                timestamp,
                payload_json,
                created_at
            FROM events
            ORDER BY id ASC
        """
        params: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def _create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    camera_id TEXT,
                    track_id INTEGER,
                    timestamp REAL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
