from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.core.config import (
    AppSettings,
    DatabaseSettings,
    EventSettings,
    Settings,
    TrackerSettings,
    YoloSettings,
)
from app.detector.yolo_detector import Detection, YoloDetector


@dataclass
class FakeBoxes:
    xyxy: object
    conf: object
    cls: object


@dataclass
class FakeResult:
    boxes: FakeBoxes | None


class FakeTensor:
    def __init__(self, value: object) -> None:
        self._value = value

    def cpu(self) -> "FakeTensor":
        return self

    def tolist(self) -> object:
        return self._value


class FakeModel:
    def __init__(self, results: list[FakeResult]) -> None:
        self.results = results
        self.predict_kwargs: dict[str, object] | None = None

    def predict(self, source: object, **kwargs: object) -> list[FakeResult]:
        self.predict_kwargs = {"source": source, **kwargs}
        return self.results


def make_settings() -> Settings:
    return Settings(
        app=AppSettings(name="test-platform", environment="test"),
        database=DatabaseSettings(url="postgresql://test/test"),
        yolo=YoloSettings(
            model_path="models/test-yolo.pt",
            confidence_threshold=0.7,
            device="cpu",
        ),
        tracker=TrackerSettings(type="bytetrack", max_age=30, min_hits=3),
        event=EventSettings(danger_zone_threshold=0.8, cooldown_seconds=60),
    )


def test_detector_loads_model_from_settings_and_detects_people() -> None:
    settings = make_settings()
    frame = object()
    model = FakeModel(
        results=[
            FakeResult(
                boxes=FakeBoxes(
                    xyxy=FakeTensor([[10, 20, 30, 40], [1, 2, 3, 4]]),
                    conf=FakeTensor([0.91, 0.88]),
                    cls=FakeTensor([0, 2]),
                )
            )
        ]
    )
    loaded_model_paths: list[str] = []

    def model_factory(model_path: str) -> FakeModel:
        loaded_model_paths.append(model_path)
        return model

    detector = YoloDetector(settings=settings, model_factory=model_factory)

    detections = detector.detect(frame)

    assert loaded_model_paths == ["models/test-yolo.pt"]
    assert model.predict_kwargs == {
        "source": frame,
        "conf": 0.7,
        "device": "cpu",
        "classes": [0],
        "verbose": False,
    }
    assert detections == [
        Detection(
            class_id=0,
            label="person",
            confidence=0.91,
            bbox=(10.0, 20.0, 30.0, 40.0),
        )
    ]


def test_detect_returns_empty_list_when_model_returns_no_boxes() -> None:
    model = FakeModel(results=[FakeResult(boxes=None)])
    detector = YoloDetector(settings=make_settings(), model_factory=lambda _: model)

    assert detector.detect(frame=object()) == []


def test_detect_rejects_malformed_bounding_boxes() -> None:
    model = FakeModel(
        results=[
            FakeResult(
                boxes=FakeBoxes(
                    xyxy=[[10, 20, 30]],
                    conf=[0.91],
                    cls=[0],
                )
            )
        ]
    )
    detector = YoloDetector(settings=make_settings(), model_factory=lambda _: model)

    with pytest.raises(ValueError, match="exactly four coordinates"):
        detector.detect(frame=object())

