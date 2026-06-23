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
        snapshot_path = event.get("snapshot_path")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_type,
                    camera_id,
                    track_id,
                    timestamp,
                    snapshot_path,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.get("event_type"),
                    event.get("camera_id"),
                    event.get("track_id"),
                    event.get("timestamp"),
                    snapshot_path,
                    payload_json,
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def save_many(self, events: list[dict]) -> list[int]:
        return [self.save(event) for event in events]

    def list_events(
        self,
        limit: int | None = None,
        offset: int = 0,
        event_type: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT
                id,
                event_type,
                camera_id,
                track_id,
                timestamp,
                snapshot_path,
                payload_json,
                created_at
            FROM events
        """
        params: list[int | str] = []

        if event_type is not None:
            query += " WHERE event_type = ?"
            params.append(event_type)

        query += " ORDER BY id ASC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)

        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()

        return [dict(row) for row in rows]

    def list_latest_events(self, limit: int = 10) -> list[dict]:
        query = """
            SELECT
                id,
                event_type,
                camera_id,
                track_id,
                timestamp,
                snapshot_path,
                payload_json,
                created_at
            FROM events
            ORDER BY id DESC
            LIMIT ?
        """

        with self._connect() as connection:
            rows = connection.execute(query, (limit,)).fetchall()

        return [dict(row) for row in rows]

    def count_events(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM events").fetchone()

        return int(row["count"])

    def count_events_by_type(self) -> dict[str, int]:
        query = """
            SELECT event_type, COUNT(*) AS count
            FROM events
            GROUP BY event_type
            ORDER BY event_type ASC
        """

        with self._connect() as connection:
            rows = connection.execute(query).fetchall()

        return {
            str(row["event_type"] or "unknown"): int(row["count"])
            for row in rows
        }

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
                    snapshot_path TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(events)").fetchall()
            }
            if "snapshot_path" not in columns:
                connection.execute("ALTER TABLE events ADD COLUMN snapshot_path TEXT")
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
