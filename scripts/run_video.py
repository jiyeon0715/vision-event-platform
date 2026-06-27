from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, is_dataclass, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.vision_event_pipeline import VisionEventPipeline
from app.core.config import load_settings
from app.database.urls import database_backend, redact_database_url
from app.services.camera_health import camera_health_registry
from storage.event_repository import EventRepository as SqliteEventRepository

DEFAULT_SNAPSHOT_DIR = Path("data/snapshots")
DEFAULT_CAMERA_ID = "default"


@dataclass(frozen=True)
class CameraDefinition:
    id: str
    source: Path


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
        nargs="?",
        help="Path to the local video file to process.",
    )
    parser.add_argument(
        "--camera-id",
        default=DEFAULT_CAMERA_ID,
        help="Camera id to use with the legacy positional video_path argument.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "config.yaml",
        help="Configuration file containing camera definitions.",
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
    cameras = _resolve_cameras(args)
    if not cameras:
        print(
            "No camera sources configured. Provide video_path or configure cameras.",
            file=sys.stderr,
        )
        return 1

    cv2 = _load_cv2()
    event_repository = _build_event_repository(args) if args.save_events else None
    for camera in cameras:
        result = _process_camera(camera, args, cv2, event_repository)
        if result != 0:
            return result

    return 0


def _resolve_cameras(args: argparse.Namespace) -> list[CameraDefinition]:
    if args.video_path is not None:
        return [
            CameraDefinition(
                id=args.camera_id,
                source=args.video_path.expanduser(),
            )
        ]

    settings = load_settings(config_path=args.config)
    return [
        CameraDefinition(id=camera.id, source=Path(camera.source).expanduser())
        for camera in settings.cameras
    ]


def _process_camera(
    camera: CameraDefinition,
    args: argparse.Namespace,
    cv2: Any,
    event_repository: Any | None,
) -> int:
    video_path = camera.source
    if not video_path.is_file():
        camera_health_registry.mark_error(
            camera.id,
            f"Video file not found: {video_path}",
            str(video_path),
        )
        print(
            f"Video file not found for camera {camera.id}: {video_path}",
            file=sys.stderr,
        )
        return 1

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        camera_health_registry.mark_error(
            camera.id,
            f"Unable to open video file: {video_path}",
            str(video_path),
        )
        print(
            f"Unable to open video file for camera {camera.id}: {video_path}",
            file=sys.stderr,
        )
        return 1

    pipeline = VisionEventPipeline(
        event_repository=_NoOpEventRepository(),
        camera_id=camera.id,
        camera_source=str(camera.source),
    )
    snapshot_dir = args.snapshot_dir
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
                snapshot_path = save_event_snapshot(
                    frame,
                    snapshot_dir,
                    camera_id=camera.id,
                )
                event_dict["snapshot_path"] = str(snapshot_path)
                print(json.dumps(event_dict, sort_keys=True))
                if event_repository is not None:
                    event_repository.save(event_dict)

            frame_index += 1
    finally:
        capture.release()

    return 0


def _build_event_repository(args: argparse.Namespace) -> Any:
    if args.database_url:
        from app.core.config import get_settings
        from app.database.health import initialize_database
        from app.database.session import create_session_factory
        from app.repositories.event_repository import EventRepository

        settings = get_settings()
        database_settings = replace(settings.database, url=args.database_url)
        session_factory = create_session_factory(
            replace(settings, database=database_settings)
        )
        initialize_database(bind_from_session_factory(session_factory))
        print(
            "Saving events to "
            f"{database_backend(args.database_url)} ({redact_database_url(args.database_url)})",
            file=sys.stderr,
        )
        return EventRepository(session_factory=session_factory)

    print(f"Saving events to SQLite ({args.db_path})", file=sys.stderr)
    return SqliteEventRepository(args.db_path)


def bind_from_session_factory(session_factory: Any) -> Any:
    bind = session_factory.kw["bind"]
    if bind is None:
        raise RuntimeError("Session factory is missing a database bind")
    return bind


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
        "camera_id": getattr(event, "camera_id", DEFAULT_CAMERA_ID),
        "track_id": getattr(event, "track_id", None),
        "timestamp": getattr(event, "timestamp", None),
        "message": getattr(event, "message", None),
    }


def save_event_snapshot(
    frame: Any,
    snapshot_dir: Path,
    camera_id: str = DEFAULT_CAMERA_ID,
) -> Path:
    cv2 = _load_cv2()
    camera_snapshot_dir = snapshot_dir / _safe_path_component(camera_id)
    camera_snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = camera_snapshot_dir / f"{uuid4().hex}.jpg"
    if not cv2.imwrite(str(snapshot_path), frame):
        raise RuntimeError(f"Failed to write snapshot: {snapshot_path}")
    return snapshot_path


def _safe_path_component(value: str) -> str:
    safe_value = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in value
    ).strip("_")
    return safe_value or DEFAULT_CAMERA_ID


def _load_cv2() -> Any:
    import cv2

    return cv2


if __name__ == "__main__":
    raise SystemExit(main())
