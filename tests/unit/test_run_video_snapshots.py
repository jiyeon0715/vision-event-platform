from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from pathlib import Path


def test_save_event_snapshot_writes_unique_jpeg_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_imwrite(path: str, frame: object) -> bool:
        Path(path).write_bytes(b"jpeg bytes")
        return frame == "frame"

    monkeypatch.setitem(sys.modules, "cv2", SimpleNamespace(imwrite=fake_imwrite))
    run_video = importlib.import_module("scripts.run_video")

    first_snapshot = run_video.save_event_snapshot("frame", tmp_path, camera_id="gate_01")
    second_snapshot = run_video.save_event_snapshot("frame", tmp_path, camera_id="gate_02")

    assert first_snapshot.parent == tmp_path / "gate_01"
    assert second_snapshot.parent == tmp_path / "gate_02"
    assert first_snapshot.suffix == ".jpg"
    assert second_snapshot.suffix == ".jpg"
    assert first_snapshot != second_snapshot
    assert first_snapshot.is_file()
    assert second_snapshot.is_file()
    assert first_snapshot.read_bytes() == b"jpeg bytes"
