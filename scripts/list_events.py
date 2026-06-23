from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage.event_repository import EventRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print saved SQLite vision events as JSON lines.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/events.db"),
        help="SQLite database path to read from.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of events to print.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = EventRepository(args.db_path)

    for event in repository.list_events(limit=args.limit):
        print(json.dumps(event, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
