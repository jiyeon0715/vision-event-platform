from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from app.detector.yolo_detector import Detection
from app.pipeline.vision_event_pipeline import VisionEventPipeline
from app.rules.danger_zone_rule import Event
from app.tracker.bytetrack_tracker import Track


@dataclass
class CallRecorder:
    calls: list[str]


def make_detection() -> Detection:
    return Detection(
        class_id=0,
        label="person",
        confidence=0.91,
        bbox=(10.0, 20.0, 30.0, 40.0),
    )


def make_track() -> Track:
    return Track(
        track_id=42,
        class_id=0,
        label="person",
        confidence=0.91,
        bbox=(10.0, 20.0, 30.0, 40.0),
    )


def make_event(timestamp: float = 123.45) -> Event:
    return Event(
        event_type="danger_zone",
        track_id=42,
        timestamp=timestamp,
        message="Track 42 stayed inside the danger zone.",
    )


class MockDetector:
    def __init__(self, detections: list[Detection], recorder: CallRecorder) -> None:
        self.detections = detections
        self.recorder = recorder
        self.detect_calls: list[object] = []

    def detect(self, frame: object) -> list[Detection]:
        self.recorder.calls.append("detect")
        self.detect_calls.append(frame)
        return self.detections


class MockTracker:
    def __init__(self, tracks: list[Track], recorder: CallRecorder) -> None:
        self.tracks = tracks
        self.recorder = recorder
        self.update_calls: list[list[Detection]] = []

    def update(self, detections: list[Detection]) -> list[Track]:
        self.recorder.calls.append("update")
        self.update_calls.append(detections)
        return self.tracks


class MockDangerZoneRule:
    def __init__(self, events: list[Event], recorder: CallRecorder) -> None:
        self.events = events
        self.recorder = recorder
        self.evaluate_calls: list[tuple[list[Track], float]] = []

    def evaluate(self, tracks: list[Track], timestamp: float) -> list[Event]:
        self.recorder.calls.append("evaluate")
        self.evaluate_calls.append((tracks, timestamp))
        return self.events


def test_process_frame_runs_detector_tracker_and_rule_in_order() -> None:
    recorder = CallRecorder(calls=[])
    frame = object()
    timestamp = 123.45
    detections = [make_detection()]
    tracks = [make_track()]
    events = [make_event(timestamp)]
    detector = MockDetector(detections=detections, recorder=recorder)
    tracker = MockTracker(tracks=tracks, recorder=recorder)
    danger_zone_rule = MockDangerZoneRule(events=events, recorder=recorder)
    pipeline = VisionEventPipeline(
        detector=detector,
        tracker=tracker,
        danger_zone_rule=danger_zone_rule,
    )

    result = pipeline.process_frame(frame, timestamp)

    assert result == events
    assert recorder.calls == ["detect", "update", "evaluate"]
    assert detector.detect_calls == [frame]
    assert tracker.update_calls == [detections]
    assert danger_zone_rule.evaluate_calls == [(tracks, timestamp)]


def test_process_frame_returns_empty_events_when_rule_emits_none() -> None:
    recorder = CallRecorder(calls=[])
    detector = MockDetector(detections=[], recorder=recorder)
    tracker = MockTracker(tracks=[], recorder=recorder)
    danger_zone_rule = MockDangerZoneRule(events=[], recorder=recorder)
    pipeline = VisionEventPipeline(
        detector=detector,
        tracker=tracker,
        danger_zone_rule=danger_zone_rule,
    )

    assert pipeline.process_frame(frame=object(), timestamp=1.0) == []
    assert recorder.calls == ["detect", "update", "evaluate"]


def test_pipeline_constructs_default_components() -> None:
    detector = MagicMock()
    tracker = MagicMock()
    danger_zone_rule = MagicMock()

    with (
        patch(
            "app.pipeline.vision_event_pipeline.YoloDetector",
            return_value=detector,
        ) as detector_cls,
        patch(
            "app.pipeline.vision_event_pipeline.ByteTrackTracker",
            return_value=tracker,
        ) as tracker_cls,
        patch(
            "app.pipeline.vision_event_pipeline.DangerZoneRule",
            return_value=danger_zone_rule,
        ) as rule_cls,
    ):
        pipeline = VisionEventPipeline()

    assert pipeline._detector is detector
    assert pipeline._tracker is tracker
    assert pipeline._danger_zone_rule is danger_zone_rule
    detector_cls.assert_called_once_with()
    tracker_cls.assert_called_once_with()
    rule_cls.assert_called_once_with()
