from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable, Protocol, Sequence

from app.core.config import Settings, TrackerSettings, get_settings
from app.detector.yolo_detector import Detection


@dataclass(frozen=True)
class Track:
    track_id: int
    class_id: int
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]


class TrackerBackend(Protocol):
    def update(self, detections: Sequence[dict[str, object]]) -> Sequence[object]:
        ...


TrackerFactory = Callable[[TrackerSettings], TrackerBackend]


class ByteTrackTracker:
    """ByteTrack wrapper that converts detector output into app-level tracks."""

    def __init__(
        self,
        settings: Settings | None = None,
        tracker_factory: TrackerFactory | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._tracker_settings = self._settings.tracker
        if self._tracker_settings.type != "bytetrack":
            raise ValueError(
                f"Unsupported tracker type: {self._tracker_settings.type}"
            )

        self._tracker = self._load_tracker(tracker_factory)

    def update(self, detections: Sequence[Detection]) -> list[Track]:
        tracker_detections = [_detection_to_tracker_input(d) for d in detections]
        raw_tracks = self._tracker.update(tracker_detections)

        tracks: list[Track] = []
        for index, raw_track in enumerate(raw_tracks):
            source_detection = detections[index] if index < len(detections) else None
            tracks.append(_normalize_track(raw_track, source_detection))

        return tracks

    def _load_tracker(self, tracker_factory: TrackerFactory | None) -> TrackerBackend:
        if tracker_factory is not None:
            return tracker_factory(self._tracker_settings)

        try:
            tracker_module = import_module("bytetracker")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "bytetracker is required to load the ByteTrack tracker"
            ) from exc

        tracker_class = (
            getattr(tracker_module, "BYTETracker", None)
            or getattr(tracker_module, "ByteTracker", None)
            or getattr(tracker_module, "Tracker", None)
        )
        if tracker_class is None:
            raise RuntimeError("bytetracker does not expose a supported tracker class")

        return tracker_class(
            max_age=self._tracker_settings.max_age,
            min_hits=self._tracker_settings.min_hits,
        )


def _detection_to_tracker_input(detection: Detection) -> dict[str, object]:
    return {
        "bbox": detection.bbox,
        "confidence": detection.confidence,
        "class_id": detection.class_id,
        "label": detection.label,
    }


def _normalize_track(raw_track: object, detection: Detection | None) -> Track:
    track_id = _required_int(raw_track, "track_id", "id")
    bbox = _normalize_bbox(_required_value(raw_track, "bbox", "tlbr", "xyxy"))

    return Track(
        track_id=track_id,
        class_id=_optional_int(raw_track, detection.class_id if detection else 0, "class_id"),
        label=str(_optional_value(raw_track, detection.label if detection else "", "label")),
        confidence=_optional_float(
            raw_track,
            detection.confidence if detection else 0.0,
            "confidence",
            "score",
        ),
        bbox=bbox,
    )


def _required_value(source: object, *names: str) -> object:
    for name in names:
        value = _get_value(source, name)
        if value is not None:
            return value

    raise ValueError(f"Track is missing required field: {'/'.join(names)}")


def _optional_value(source: object, default: object, *names: str) -> object:
    for name in names:
        value = _get_value(source, name)
        if value is not None:
            return value

    return default


def _required_int(source: object, *names: str) -> int:
    return int(_required_value(source, *names))


def _optional_int(source: object, default: int, *names: str) -> int:
    return int(_optional_value(source, default, *names))


def _optional_float(source: object, default: float, *names: str) -> float:
    return float(_optional_value(source, default, *names))


def _get_value(source: object, name: str) -> object:
    if isinstance(source, dict):
        return source.get(name)

    return getattr(source, name, None)


def _normalize_bbox(value: object) -> tuple[float, float, float, float]:
    coordinates = list(value)  # type: ignore[arg-type]
    if len(coordinates) != 4:
        raise ValueError("Track bbox must contain exactly four coordinates")

    return tuple(float(coordinate) for coordinate in coordinates)  # type: ignore[return-value]
