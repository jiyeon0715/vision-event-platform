from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.config import (
    AppSettings,
    DatabaseSettings,
    EventSettings,
    Settings,
    TrackerSettings,
    YoloSettings,
)
from app.detector.yolo_detector import Detection
from app.tracker.bytetrack_tracker import ByteTrackTracker, Track


@dataclass
class RawTrack:
    track_id: int
    tlbr: tuple[int, int, int, int]
    score: float


class FakeTracker:
    def __init__(self, tracks: list[object]) -> None:
        self.tracks = tracks
        self.update_calls: list[list[dict[str, object]]] = []

    def update(self, detections: list[dict[str, object]]) -> list[object]:
        self.update_calls.append(detections)
        return self.tracks


def make_settings(tracker_type: str = "bytetrack") -> Settings:
    return Settings(
        app=AppSettings(name="test-platform", environment="test"),
        database=DatabaseSettings(url="postgresql://test/test"),
        yolo=YoloSettings(
            model_path="models/test-yolo.pt",
            confidence_threshold=0.7,
            device="cpu",
        ),
        tracker=TrackerSettings(type=tracker_type, max_age=30, min_hits=3),
        event=EventSettings(danger_zone_threshold=0.8, cooldown_seconds=60),
    )


def test_tracker_loads_settings_and_returns_standardized_tracks() -> None:
    settings = make_settings()
    fake_tracker = FakeTracker(
        tracks=[
            {
                "track_id": 42,
                "bbox": (10, 20, 30, 40),
                "confidence": 0.91,
                "class_id": 0,
                "label": "person",
            }
        ]
    )
    loaded_settings: list[TrackerSettings] = []

    def tracker_factory(tracker_settings: TrackerSettings) -> FakeTracker:
        loaded_settings.append(tracker_settings)
        return fake_tracker

    tracker = ByteTrackTracker(
        settings=settings,
        tracker_factory=tracker_factory,
    )
    detections = [
        Detection(
            class_id=0,
            label="person",
            confidence=0.91,
            bbox=(10.0, 20.0, 30.0, 40.0),
        )
    ]

    tracks = tracker.update(detections)

    assert loaded_settings == [settings.tracker]
    assert fake_tracker.update_calls == [
        [
            {
                "bbox": (10.0, 20.0, 30.0, 40.0),
                "confidence": 0.91,
                "class_id": 0,
                "label": "person",
            }
        ]
    ]
    assert tracks == [
        Track(
            track_id=42,
            class_id=0,
            label="person",
            confidence=0.91,
            bbox=(10.0, 20.0, 30.0, 40.0),
        )
    ]


def test_tracker_uses_detection_metadata_when_raw_track_omits_it() -> None:
    fake_tracker = FakeTracker(
        tracks=[RawTrack(track_id=7, tlbr=(1, 2, 3, 4), score=0.82)]
    )
    tracker = ByteTrackTracker(
        settings=make_settings(),
        tracker_factory=lambda _: fake_tracker,
    )

    tracks = tracker.update(
        [
            Detection(
                class_id=0,
                label="person",
                confidence=0.73,
                bbox=(1.0, 2.0, 3.0, 4.0),
            )
        ]
    )

    assert tracks == [
        Track(
            track_id=7,
            class_id=0,
            label="person",
            confidence=0.82,
            bbox=(1.0, 2.0, 3.0, 4.0),
        )
    ]


def test_tracker_rejects_unsupported_tracker_type() -> None:
    with pytest.raises(ValueError, match="Unsupported tracker type"):
        ByteTrackTracker(
            settings=make_settings(tracker_type="sort"),
            tracker_factory=lambda _: FakeTracker(tracks=[]),
        )
