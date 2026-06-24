from __future__ import annotations

from typing import Protocol, Sequence

from app.detector.yolo_detector import Detection, YoloDetector
from app.pipeline.alert_policy import AlertPolicy
from app.rules.base import Event
from app.rules.loader import load_rules
from app.tracker.bytetrack_tracker import ByteTrackTracker, Track


class Detector(Protocol):
    def detect(self, frame: object) -> Sequence[Detection]:
        ...


class Tracker(Protocol):
    def update(self, detections: Sequence[Detection]) -> Sequence[Track]:
        ...


class RuleEvaluator(Protocol):
    def evaluate(self, tracks: Sequence[Track], timestamp: float) -> Sequence[Event]:
        ...


DangerZoneRuleEvaluator = RuleEvaluator


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
        rules: Sequence[RuleEvaluator] | None = None,
        event_repository: EventWriter | None = None,
        alert_policy: AlertPolicy | None = None,
    ) -> None:
        self._detector = detector or YoloDetector()
        self._tracker = tracker or ByteTrackTracker()
        self._rules = (
            list(rules) if rules is not None else _resolve_rules(danger_zone_rule)
        )
        self._danger_zone_rule = self._rules[0] if self._rules else None
        self._event_repository = event_repository or _default_event_repository()
        self._alert_policy = alert_policy or _default_alert_policy()

    def process_frame(self, frame: object, timestamp: float) -> list[Event]:
        detections = self._detector.detect(frame)
        tracks = self._tracker.update(detections)
        events = [
            event
            for rule in self._rules
            for event in rule.evaluate(tracks, timestamp)
        ]
        approved_events = self._alert_policy.filter_events(events)
        self._event_repository.save_many(approved_events)
        return approved_events


def _resolve_rules(
    danger_zone_rule: DangerZoneRuleEvaluator | None = None,
) -> list[RuleEvaluator]:
    if danger_zone_rule is not None:
        return [danger_zone_rule]

    return load_rules()


def _default_event_repository() -> EventWriter:
    from app.repositories.event_repository import EventRepository

    return EventRepository()


def _default_alert_policy() -> AlertPolicy:
    from app.core.config import get_settings

    return AlertPolicy.from_settings(get_settings().alert_policy)
