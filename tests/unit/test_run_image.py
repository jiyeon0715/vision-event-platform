from __future__ import annotations

import importlib
import json
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FakeEvent:
    event_type: str
    camera_id: str
    track_id: int
    timestamp: float
    message: str


class FakeCv2:
    def __init__(self, frame: object | None) -> None:
        self.frame = frame
        self.read_paths: list[str] = []

    def imread(self, path: str) -> object | None:
        self.read_paths.append(path)
        return self.frame


class FakePipeline:
    instances: list["FakePipeline"] = []

    def __init__(
        self,
        event_repository: object,
        camera_id: str,
        camera_source: str,
    ) -> None:
        self.event_repository = event_repository
        self.camera_id = camera_id
        self.camera_source = camera_source
        self.process_frame_calls: list[tuple[object, float]] = []
        FakePipeline.instances.append(self)

    def process_frame(self, frame: object, timestamp: float) -> list[FakeEvent]:
        self.process_frame_calls.append((frame, timestamp))
        return [
            FakeEvent(
                event_type="danger_zone",
                camera_id=self.camera_id,
                track_id=7,
                timestamp=timestamp,
                message="detected",
            )
        ]


class FakeEventRepository:
    def __init__(self) -> None:
        self.saved_events: list[dict[str, object]] = []

    def save(self, event: dict[str, object]) -> None:
        self.saved_events.append(event)


def test_run_image_passes_image_source_frame_to_pipeline(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    image_path = tmp_path / "frame.jpg"
    image_path.write_bytes(b"image")
    cv2 = FakeCv2(frame="decoded-frame")
    run_image = importlib.import_module("scripts.run_image")
    FakePipeline.instances = []

    monkeypatch.setattr(run_image, "VisionEventPipeline", FakePipeline)
    monkeypatch.setattr(
        run_image,
        "save_event_snapshot",
        lambda frame, snapshot_dir, camera_id: snapshot_dir / camera_id / "event.jpg",
    )
    args = Namespace(
        image_path=image_path,
        source_id="gate_01",
        snapshot_dir=tmp_path / "snapshots",
    )

    result = run_image._process_image(args, cv2, event_repository=None)

    captured = capsys.readouterr()
    printed_event = json.loads(captured.out)
    assert result == 0
    assert cv2.read_paths == [str(image_path)]
    assert len(FakePipeline.instances) == 1
    pipeline = FakePipeline.instances[0]
    assert pipeline.camera_id == "gate_01"
    assert pipeline.camera_source == str(image_path)
    assert pipeline.process_frame_calls == [("decoded-frame", 0.0)]
    assert printed_event == {
        "camera_id": "gate_01",
        "event_type": "danger_zone",
        "message": "detected",
        "snapshot_path": str(tmp_path / "snapshots" / "gate_01" / "event.jpg"),
        "timestamp": 0.0,
        "track_id": 7,
    }


def test_run_image_saves_printed_events_when_requested(
    tmp_path: Path,
    monkeypatch,
) -> None:
    image_path = tmp_path / "frame.jpg"
    image_path.write_bytes(b"image")
    repository = FakeEventRepository()
    run_image = importlib.import_module("scripts.run_image")
    FakePipeline.instances = []

    monkeypatch.setattr(run_image, "VisionEventPipeline", FakePipeline)
    monkeypatch.setattr(
        run_image,
        "save_event_snapshot",
        lambda frame, snapshot_dir, camera_id: snapshot_dir / camera_id / "event.jpg",
    )
    args = Namespace(
        image_path=image_path,
        source_id="upload_01",
        snapshot_dir=tmp_path / "snapshots",
    )

    result = run_image._process_image(
        args,
        FakeCv2(frame="decoded-frame"),
        event_repository=repository,
    )

    assert result == 0
    assert repository.saved_events == [
        {
            "camera_id": "upload_01",
            "event_type": "danger_zone",
            "message": "detected",
            "snapshot_path": str(tmp_path / "snapshots" / "upload_01" / "event.jpg"),
            "timestamp": 0.0,
            "track_id": 7,
        }
    ]


def test_run_image_returns_error_for_unreadable_image(tmp_path: Path, capsys) -> None:
    image_path = tmp_path / "not-an-image.txt"
    image_path.write_text("not an image")
    run_image = importlib.import_module("scripts.run_image")
    args = Namespace(
        image_path=image_path,
        source_id="upload_01",
        snapshot_dir=tmp_path / "snapshots",
    )

    result = run_image._process_image(
        args,
        FakeCv2(frame=None),
        event_repository=None,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Unable to read image file for source upload_01" in captured.err
