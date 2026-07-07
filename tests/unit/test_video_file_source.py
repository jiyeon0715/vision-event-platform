from __future__ import annotations

from pathlib import Path

import pytest

from vision.inputs import FramePacket, VideoFileSource


class FakeCapture:
    def __init__(
        self,
        frames: list[object],
        fps: float = 0.0,
        pos_msecs: list[float] | None = None,
        opened: bool = True,
    ) -> None:
        self.frames = frames
        self.fps = fps
        self.pos_msecs = pos_msecs or []
        self.opened = opened
        self.released = False
        self._next_index = 0
        self._current_index = -1

    def isOpened(self) -> bool:
        return self.opened

    def read(self) -> tuple[bool, object | None]:
        if self._next_index >= len(self.frames):
            return False, None

        self._current_index = self._next_index
        self._next_index += 1
        return True, self.frames[self._current_index]

    def get(self, prop: int) -> float:
        if prop == FakeCv2.CAP_PROP_FPS:
            return self.fps

        if prop == FakeCv2.CAP_PROP_POS_MSEC and self._current_index >= 0:
            if self._current_index < len(self.pos_msecs):
                return self.pos_msecs[self._current_index]

        return 0.0

    def release(self) -> None:
        self.released = True


class FakeCv2:
    CAP_PROP_FPS = 5
    CAP_PROP_POS_MSEC = 0

    def __init__(self, capture: FakeCapture) -> None:
        self.capture = capture
        self.opened_paths: list[str] = []

    def VideoCapture(self, path: str) -> FakeCapture:
        self.opened_paths.append(path)
        return self.capture


def test_video_file_source_returns_frame_packets_with_metadata(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video")
    capture = FakeCapture(
        frames=["frame-1", "frame-2"],
        fps=30.0,
        pos_msecs=[0.0, 50.0],
    )
    cv2 = FakeCv2(capture)

    source = VideoFileSource(video_path, source_id="line_01", cv2_module=cv2)
    packets = list(source)
    source.close()

    assert packets == [
        FramePacket(
            source_id="line_01",
            source_type="video_file",
            timestamp=0.0,
            frame_index=0,
            frame="frame-1",
        ),
        FramePacket(
            source_id="line_01",
            source_type="video_file",
            timestamp=0.05,
            frame_index=1,
            frame="frame-2",
        ),
    ]
    assert cv2.opened_paths == [str(video_path)]
    assert capture.released is True


def test_video_file_source_falls_back_to_fps_timestamp(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video")
    capture = FakeCapture(frames=["frame-1", "frame-2"], fps=10.0)

    source = VideoFileSource(
        video_path,
        source_id="line_01",
        cv2_module=FakeCv2(capture),
    )
    packets = list(source)
    source.close()

    assert [packet.timestamp for packet in packets] == [0.0, 0.1]
    assert [packet.frame_index for packet in packets] == [0, 1]


def test_video_file_source_falls_back_to_frame_index_timestamp(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video")
    capture = FakeCapture(frames=["frame-1", "frame-2"], fps=0.0)

    source = VideoFileSource(
        video_path,
        source_id="line_01",
        cv2_module=FakeCv2(capture),
    )
    packets = list(source)
    source.close()

    assert [packet.timestamp for packet in packets] == [0.0, 1.0]


def test_video_file_source_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        VideoFileSource(
            tmp_path / "missing.mp4",
            source_id="line_01",
            cv2_module=FakeCv2(FakeCapture(frames=[])),
        )


def test_video_file_source_raises_when_file_cannot_be_opened(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"video")
    capture = FakeCapture(frames=[], opened=False)

    with pytest.raises(RuntimeError):
        VideoFileSource(video_path, source_id="line_01", cv2_module=FakeCv2(capture))

    assert capture.released is True
