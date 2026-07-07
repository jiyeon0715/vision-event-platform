from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.vision_event_pipeline import VisionEventPipeline
from scripts.run_video import (
    DEFAULT_CAMERA_ID,
    DEFAULT_SNAPSHOT_DIR,
    _NoOpEventRepository,
    _build_event_repository,
    _event_to_dict,
    _load_cv2,
    save_event_snapshot,
)
from vision.inputs.image_source import ImageSource


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the vision event pipeline against a local image file.",
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the local image file to process.",
    )
    source_id = parser.add_mutually_exclusive_group()
    source_id.add_argument(
        "--camera-id",
        dest="source_id",
        default=DEFAULT_CAMERA_ID,
        help="Camera id to attach to generated events.",
    )
    source_id.add_argument(
        "--source-id",
        dest="source_id",
        help="Source id to attach to generated events.",
    )
    parser.add_argument(
        "--save-events",
        action="store_true",
        help="Save emitted events in addition to printing them.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help=(
            "SQLAlchemy database URL used with --save-events. Defaults to "
            "DATABASE_URL when set; otherwise --db-path SQLite is used."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/events.db"),
        help="SQLite database path used with --save-events when no database URL is set.",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=DEFAULT_SNAPSHOT_DIR,
        help="Directory where event frame snapshots are stored.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cv2 = _load_cv2()
    event_repository = _build_event_repository(args) if args.save_events else None
    return _process_image(args, cv2, event_repository)


def _process_image(
    args: argparse.Namespace,
    cv2: Any,
    event_repository: Any | None,
) -> int:
    image_path = args.image_path.expanduser()
    source_id = args.source_id

    try:
        frame_source = ImageSource(
            image_path,
            source_id=source_id,
            cv2_module=cv2,
        )
    except FileNotFoundError:
        print(
            f"Image file not found for source {source_id}: {image_path}",
            file=sys.stderr,
        )
        return 1
    except RuntimeError:
        print(
            f"Unable to read image file for source {source_id}: {image_path}",
            file=sys.stderr,
        )
        return 1

    pipeline = VisionEventPipeline(
        event_repository=_NoOpEventRepository(),
        camera_id=source_id,
        camera_source=str(image_path),
    )

    try:
        for packet in frame_source:
            events = pipeline.process_frame(packet.frame, packet.timestamp)
            for event in events:
                event_dict = _event_to_dict(event)
                snapshot_path = save_event_snapshot(
                    packet.frame,
                    args.snapshot_dir,
                    camera_id=source_id,
                )
                event_dict["snapshot_path"] = str(snapshot_path)
                print(json.dumps(event_dict, sort_keys=True))
                if event_repository is not None:
                    event_repository.save(event_dict)
    finally:
        frame_source.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
