from __future__ import annotations

import pytest

from app.pipeline.vision_event_pipeline import VisionEventPipeline
from app.services.camera_health import CameraHealthRegistry
from tests.unit.test_vision_event_pipeline import (
    CallRecorder,
    MockDetector,
    MockEventRepository,
    MockRule,
    MockTracker,
    make_event,
)


class FailingDetector:
    def detect(self, frame: object) -> list[object]:
        raise RuntimeError("camera read failed")


def test_camera_health_registry_tracks_frames_and_events() -> None:
    registry = CameraHealthRegistry()
    recorder = CallRecorder(calls=[])
    pipeline = VisionEventPipeline(
        detector=MockDetector(detections=[], recorder=recorder),
        tracker=MockTracker(tracks=[], recorder=recorder),
        rules=[MockRule(events=[make_event(timestamp=1.0)], recorder=recorder)],
        event_repository=MockEventRepository(),
        camera_id="gate_01",
        camera_source="data/videos/gate_01.mp4",
        health_registry=registry,
    )

    pipeline.process_frame(frame=object(), timestamp=1.0)

    health = registry.list_health()[0]
    assert health.camera_id == "gate_01"
    assert health.source == "data/videos/gate_01.mp4"
    assert health.status == "online"
    assert health.last_frame_at is not None
    assert health.last_event_at is not None
    assert health.processed_frame_count == 1
    assert health.emitted_event_count == 1
    assert health.last_error is None


def test_camera_health_registry_marks_processing_errors_offline() -> None:
    registry = CameraHealthRegistry()
    pipeline = VisionEventPipeline(
        detector=FailingDetector(),
        tracker=MockTracker(tracks=[], recorder=CallRecorder(calls=[])),
        rules=[],
        event_repository=MockEventRepository(),
        camera_id="gate_02",
        camera_source="rtsp://camera/gate_02",
        health_registry=registry,
    )

    with pytest.raises(RuntimeError, match="camera read failed"):
        pipeline.process_frame(frame=object(), timestamp=1.0)

    health = registry.list_health()[0]
    assert health.camera_id == "gate_02"
    assert health.source == "rtsp://camera/gate_02"
    assert health.status == "offline"
    assert health.last_frame_at is not None
    assert health.processed_frame_count == 1
    assert health.emitted_event_count == 0
    assert health.last_error == "camera read failed"
