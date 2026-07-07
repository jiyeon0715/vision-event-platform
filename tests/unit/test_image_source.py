from __future__ import annotations

from pathlib import Path

import pytest

from vision.inputs import FramePacket, ImageSource


class FakeCv2:
    def __init__(self, frame: object | None) -> None:
        self.frame = frame
        self.read_paths: list[str] = []

    def imread(self, path: str) -> object | None:
        self.read_paths.append(path)
        return self.frame


def test_image_source_returns_single_frame_packet_with_metadata(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"image")
    cv2 = FakeCv2(frame="frame-1")

    source = ImageSource(image_path, source_id="upload_01", cv2_module=cv2)
    packets = list(source)
    source.close()

    assert packets == [
        FramePacket(
            source_id="upload_01",
            source_type="image",
            timestamp=0.0,
            frame_index=0,
            frame="frame-1",
        )
    ]
    assert cv2.read_paths == [str(image_path)]


def test_image_source_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ImageSource(
            tmp_path / "missing.jpg",
            source_id="upload_01",
            cv2_module=FakeCv2(frame="frame-1"),
        )


def test_image_source_raises_when_file_cannot_be_read(tmp_path: Path) -> None:
    image_path = tmp_path / "not-an-image.txt"
    image_path.write_text("not an image")

    with pytest.raises(RuntimeError):
        ImageSource(image_path, source_id="upload_01", cv2_module=FakeCv2(frame=None))
