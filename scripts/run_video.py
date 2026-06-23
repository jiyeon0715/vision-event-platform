from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.vision_event_pipeline import VisionEventPipeline
from storage.event_repository import EventRepository


class _NoOpEventRepository:
    def save_many(self, events: list[Any]) -> None:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the vision event pipeline against a local video file.",
    )
    parser.add_argument(
        "video_path",
        type=Path,
        help="Path to the local video file to process.",
    )
    parser.add_argument(
        "--save-events",
        action="store_true",
        help="Save emitted events to SQLite in addition to printing them.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/events.db"),
        help="SQLite database path used with --save-events.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video_path = args.video_path.expanduser()
    if not video_path.is_file():
        print(f"Video file not found: {video_path}", file=sys.stderr)
        return 1

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        print(f"Unable to open video file: {video_path}", file=sys.stderr)
        return 1

    pipeline = VisionEventPipeline(event_repository=_NoOpEventRepository())
    event_repository = EventRepository(args.db_path) if args.save_events else None
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_index = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                print("Reached end of video.")
                break

            timestamp = _frame_timestamp(capture, frame_index, fps)
            events = pipeline.process_frame(frame, timestamp)
            for event in events:
                event_dict = _event_to_dict(event)
                print(json.dumps(event_dict, sort_keys=True))
                if event_repository is not None:
                    event_repository.save(event_dict)

            frame_index += 1
    finally:
        capture.release()

    return 0


def _frame_timestamp(capture: cv2.VideoCapture, frame_index: int, fps: float) -> float:
    timestamp_msec = capture.get(cv2.CAP_PROP_POS_MSEC)
    if timestamp_msec > 0:
        return timestamp_msec / 1000.0

    if fps > 0:
        return frame_index / fps

    return float(frame_index)


def _event_to_dict(event: Any) -> dict[str, Any]:
    if is_dataclass(event):
        return asdict(event)

    if isinstance(event, dict):
        return event

    return {
        "event_type": getattr(event, "event_type", None),
        "track_id": getattr(event, "track_id", None),
        "timestamp": getattr(event, "timestamp", None),
        "message": getattr(event, "message", None),
    }


if __name__ == "__main__":
    raise SystemExit(main())
