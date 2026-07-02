from __future__ import annotations

import argparse
import base64
import json
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_DB_PATH = Path("data/events.db")
DEFAULT_SNAPSHOT_DIR = Path("data/snapshots")
DEFAULT_EVENT_COUNT = 36
MIN_EVENT_COUNT = 20
MAX_EVENT_COUNT = 50

CAMERAS = [
    {
        "camera_id": "gate_01",
        "camera_name": "Front Gate",
        "location": "North entrance",
        "source": "sample://front-gate",
    },
    {
        "camera_id": "lobby_02",
        "camera_name": "Main Lobby",
        "location": "Building A lobby",
        "source": "sample://main-lobby",
    },
    {
        "camera_id": "dock_03",
        "camera_name": "Loading Dock",
        "location": "Warehouse dock",
        "source": "sample://loading-dock",
    },
    {
        "camera_id": "parking_04",
        "camera_name": "Visitor Parking",
        "location": "West parking lot",
        "source": "sample://visitor-parking",
    },
]

RULES = [
    {
        "event_type": "danger_zone",
        "rule_name": "Danger Zone Entry",
        "severity": "critical",
        "duration_range": (2.0, 9.5),
    },
    {
        "event_type": "loitering",
        "rule_name": "Loitering",
        "severity": "warning",
        "duration_range": (30.0, 180.0),
    },
    {
        "event_type": "person_count",
        "rule_name": "Person Count Threshold",
        "severity": "info",
        "duration_range": (5.0, 45.0),
    },
    {
        "event_type": "line_crossing",
        "rule_name": "Restricted Line Crossing",
        "severity": "warning",
        "duration_range": (1.0, 5.0),
    },
]

JPEG_1X1 = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QA"
    "FQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAH/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oA"
    "CAEBAAEFAqf/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/ASP/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/ASP/xAAU"
    "EAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAY/Ar//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/IV//2gAMAwEAAgADAAAAEP/E"
    "FBQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQMBAT8QH//EFBQRAQAAAAAAAAAAAAAAAAAAABD/2gAIAQIBAT8QH//EFBABAQAAAAAAAAAA"
    "AAAAAAAAABD/2gAIAQEAAT8QH//Z"
)


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    db_path = args.db_path
    snapshot_dir = args.snapshot_dir

    db_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    create_schema(db_path)

    if args.reset:
        delete_events(db_path)

    rows = build_events(
        count=args.count,
        snapshot_dir=snapshot_dir,
        rng=rng,
    )
    write_snapshots(rows)
    insert_events(db_path, rows)

    print(f"Seeded {len(rows)} dashboard events into {db_path}")
    print(f"Wrote sample snapshots under {snapshot_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed api.main dashboard data into the local SQLite events DB.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite DB path. Defaults to {DEFAULT_DB_PATH}.",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=DEFAULT_SNAPSHOT_DIR,
        help=f"Snapshot directory. Defaults to {DEFAULT_SNAPSHOT_DIR}.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_EVENT_COUNT,
        help=f"Number of events to insert ({MIN_EVENT_COUNT}-{MAX_EVENT_COUNT}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed for deterministic sample data.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing rows from the events table before inserting samples.",
    )
    args = parser.parse_args()
    if not MIN_EVENT_COUNT <= args.count <= MAX_EVENT_COUNT:
        parser.error(f"--count must be between {MIN_EVENT_COUNT} and {MAX_EVENT_COUNT}")
    return args


def create_schema(db_path: Path) -> None:
    with connect(db_path) as connection:
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


def delete_events(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.execute("DELETE FROM events")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'events'")
        connection.commit()


def build_events(
    *,
    count: int,
    snapshot_dir: Path,
    rng: random.Random,
) -> list[dict[str, object]]:
    base_time = datetime.now(timezone.utc).replace(microsecond=0)
    rows: list[dict[str, object]] = []

    for index in range(count):
        camera = CAMERAS[index % len(CAMERAS)]
        rule = RULES[(index + rng.randrange(len(RULES))) % len(RULES)]
        created_at = base_time - timedelta(minutes=index * rng.randint(4, 18))
        track_id = 1000 + index
        duration_min, duration_max = rule["duration_range"]
        snapshot_path = (
            snapshot_dir
            / str(camera["camera_id"])
            / f"{created_at.strftime('%Y%m%dT%H%M%SZ')}_{track_id}.jpg"
        )
        bbox = make_bbox(rng)
        confidence = round(rng.uniform(0.72, 0.98), 3)
        duration_sec = round(rng.uniform(duration_min, duration_max), 1)

        payload = {
            "event_type": rule["event_type"],
            "rule_name": rule["rule_name"],
            "severity": rule["severity"],
            "confidence": confidence,
            "bbox": bbox,
            "duration_sec": duration_sec,
            "camera_id": camera["camera_id"],
            "camera_name": camera["camera_name"],
            "location": camera["location"],
            "track_id": track_id,
            "timestamp": created_at.timestamp(),
            "snapshot_path": str(snapshot_path),
            "message": (
                f"{rule['rule_name']} detected on {camera['camera_name']} "
                f"with {confidence:.0%} confidence."
            ),
            "metadata": {
                "source": camera["source"],
                "zone": camera["location"],
                "sample": True,
            },
        }
        rows.append(
            {
                "event_type": rule["event_type"],
                "camera_id": camera["camera_id"],
                "track_id": track_id,
                "timestamp": created_at.timestamp(),
                "snapshot_path": str(snapshot_path),
                "payload_json": json.dumps(payload, sort_keys=True),
                "created_at": created_at.isoformat(),
            }
        )

    return rows


def make_bbox(rng: random.Random) -> dict[str, int]:
    x = rng.randint(60, 1120)
    y = rng.randint(40, 620)
    width = rng.randint(80, 260)
    height = rng.randint(120, 360)
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def write_snapshots(rows: list[dict[str, object]]) -> None:
    for row in rows:
        snapshot_path = Path(str(row["snapshot_path"]))
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot_path.exists():
            snapshot_path.write_bytes(JPEG_1X1)


def insert_events(db_path: Path, rows: list[dict[str, object]]) -> None:
    with connect(db_path) as connection:
        connection.executemany(
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
            VALUES (
                :event_type,
                :camera_id,
                :track_id,
                :timestamp,
                :snapshot_path,
                :payload_json,
                :created_at
            )
            """,
            rows,
        )
        connection.commit()


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


if __name__ == "__main__":
    main()
