from __future__ import annotations

import json
import sqlite3
from collections import Counter
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
        camera_id: str | None = None,
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
        clauses = []
        params: list[int | str] = []

        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        if camera_id is not None:
            clauses.append("camera_id = ?")
            params.append(camera_id)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

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

    def list_latest_events(
        self,
        limit: int = 10,
        camera_id: str | None = None,
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
        if camera_id is not None:
            query += " WHERE camera_id = ?"
            params.append(camera_id)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()

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

    def stats(
        self,
        start_at: str | None = None,
        end_at: str | None = None,
        camera_id: str | None = None,
        rule_name: str | None = None,
    ) -> dict:
        query = """
            SELECT event_type, camera_id, created_at
            FROM events
        """
        clauses = []
        params: list[str] = []

        if start_at is not None:
            clauses.append("created_at >= ?")
            params.append(start_at)
        if end_at is not None:
            clauses.append("created_at <= ?")
            params.append(end_at)
        if camera_id is not None:
            clauses.append("camera_id = ?")
            params.append(camera_id)
        if rule_name is not None:
            clauses.append("event_type = ?")
            params.append(rule_name)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()

        rule_counts = Counter(str(row["event_type"] or "unknown") for row in rows)
        camera_counts = Counter(str(row["camera_id"] or "unknown") for row in rows)
        hourly_counts = Counter(_hour_bucket(str(row["created_at"])) for row in rows)
        latest_event_timestamp = max(
            (str(row["created_at"]) for row in rows),
            default=None,
        )

        return {
            "total_event_count": len(rows),
            "event_count_by_rule_name": dict(sorted(rule_counts.items())),
            "event_count_by_camera_id": dict(sorted(camera_counts.items())),
            "hourly_event_counts": dict(sorted(hourly_counts.items())),
            "latest_event_timestamp": latest_event_timestamp,
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
            if "camera_id" not in columns:
                connection.execute("ALTER TABLE events ADD COLUMN camera_id TEXT")
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _hour_bucket(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value[:13]

    return parsed.replace(minute=0, second=0, microsecond=0).isoformat()
