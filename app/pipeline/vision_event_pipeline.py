from __future__ import annotations

from typing import Protocol, Sequence

from app.detector.yolo_detector import Detection, YoloDetector
from app.rules.danger_zone_rule import DangerZoneRule, Event
from app.tracker.bytetrack_tracker import ByteTrackTracker, Track


class Detector(Protocol):
    def detect(self, frame: object) -> Sequence[Detection]:
        ...


class Tracker(Protocol):
    def update(self, detections: Sequence[Detection]) -> Sequence[Track]:
        ...


class DangerZoneRuleEvaluator(Protocol):
    def evaluate(self, tracks: Sequence[Track], timestamp: float) -> Sequence[Event]:
        ...


class EventWriter(Protocol):
    def save_many(self, events: Sequence[Event]) -> object:
        ...


class VisionEventPipeline:
    """Coordinates frame detection, tracking, and rule evaluation."""

    def __init__(
        self,
        detector: Detector | None = None,
        tracker: Tracker | None = None,
        danger_zone_rule: DangerZoneRuleEvaluator | None = None,
        event_repository: EventWriter | None = None,
    ) -> None:
        self._detector = detector or YoloDetector()
        self._tracker = tracker or ByteTrackTracker()
        self._danger_zone_rule = danger_zone_rule or DangerZoneRule()
        self._event_repository = event_repository or _default_event_repository()

    def process_frame(self, frame: object, timestamp: float) -> list[Event]:
        detections = self._detector.detect(frame)
        tracks = self._tracker.update(detections)
        events = list(self._danger_zone_rule.evaluate(tracks, timestamp))
        self._event_repository.save_many(events)
        return events


def _default_event_repository() -> EventWriter:
    from app.repositories.event_repository import EventRepository

    return EventRepository()
